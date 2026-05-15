import streamlit as st
from lxml import etree
import re
import zipfile
from supabase import create_client

# --- CONEXÃO SUPABASE (DADOS REAIS DO ISAAC) ---
SUPABASE_URL = "https://tcvfvnzsmgtjsnsphgom.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRjdmZ2bnpzbWd0c2puc3BoZ29tIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzg4MTg0NDMsImV4cCI6MjA5NDM5NDQ0M30.Sk55DOfrbMuthd2eIF68mK0w7h7PIJ4UGMT_wqagbLg"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="Portal Fiscal Ginseng", layout="wide")

st.title("🛡️ Sistema Permanente Grupo Ginseng")

# Funções de Banco de Dados
def salvar_nota(nome, conteudo):
    try:
        # Tenta inserir no banco de dados. Se já existir (pelo nome), ele pula.
        supabase.table("notas_fiscais").insert({"nome_arquivo": nome, "conteudo_xml": conteudo}).execute()
    except:
        pass

def buscar_notas_db(termo):
    # Busca inteligente: procura o termo dentro do conteúdo bruto do XML
    res = supabase.table("notas_fiscais").select("*").ilike("conteudo_xml", f"%{termo}%").execute()
    return res.data

aba1, aba2 = st.tabs(["🔍 Consultar Nota (Toda Equipe)", "📦 Upload de Lote (Permanente)"])

with aba2:
    st.header("Upload para Nuvem")
    st.info("As notas salvas aqui não somem e podem ser acessadas de qualquer máquina.")
    arquivos_up = st.file_uploader("Arraste o ZIP de 2.000 notas", type=['xml', 'zip'], accept_multiple_files=True)
    
    if st.button("🚀 Enviar para o Banco de Dados"):
        if arquivos_up:
            lidos = 0
            with st.spinner('Enviando dados... Isso pode demorar um pouco para lotes grandes.'):
                for item in arquivos_up:
                    if item.name.lower().endswith('.zip'):
                        with zipfile.ZipFile(item) as z:
                            for info in z.infolist():
                                if not info.is_dir() and info.filename.lower().endswith('.xml'):
                                    conteudo = z.read(info.filename).decode('utf-8', errors='ignore')
                                    salvar_nota(info.filename, conteudo)
                                    lidos += 1
                    else:
                        conteudo = item.read().decode('utf-8', errors='ignore')
                        salvar_nota(item.name, conteudo)
                        lidos += 1
            st.success(f"✅ {lidos} notas foram guardadas na nuvem!")

with aba1:
    st.header("Busca de Vencimentos")
    termo = st.text_input("Digite o Código (Ex: LM9BUVRG), Número ou Chave:")
    
    if termo:
        termo = termo.strip()
        notas_encontradas = buscar_notas_db(termo)

        if notas_encontradas:
            st.success(f"Encontrei {len(notas_encontradas)} nota(s) na base permanente!")
            for nota in notas_encontradas:
                try:
                    xml_str = nota['conteudo_xml']
                    # Parser que remove Namespaces para ler qualquer formato (Maceió, TOTVS, etc)
                    parser = etree.XMLParser(recover=True, remove_blank_text=True)
                    root = etree.fromstring(xml_str.encode('utf-8'), parser=parser)
                    for elem in root.getiterator():
                        if not (isinstance(elem, etree._Comment) or isinstance(elem, etree._ProcessingInstruction)):
                            elem.tag = etree.QName(elem).localname
                    etree.cleanup_namespaces(root)

                    emitente = root.xpath('//RazaoSocialPrestador/text() | //xNome/text() | //emit/xNome/text()')
                    numero = root.xpath('//nNFSe/text() | //nNF/text() | //NumeroNFe/text()')
                    
                    with st.expander(f"📄 Nota {numero[0] if numero else 'S/N'} - {emitente[0] if emitente else 'Fornecedor'}", expanded=True):
                        vencimentos = []
                        # Busca em campos de texto (TOTVS, Boticário, Maceió)
                        textos = root.xpath('//Discriminacao/text() | //xInfComp/text() | //xDescServ/text()')
                        if textos:
                            t = textos[0].upper()
                            # Captura datas próximas a palavra VENC
                            datas = re.findall(r'VENC(?:\.:|:)?\s*(\d{2}/\d{2}/\d{4})', t)
                            datas_bot = re.findall(r'R\$\s*[\d,.]+\s*VENC\s*(\d{2}/\d{2}/\d{4})', t)
                            for d in (datas + datas_bot):
                                vencimentos.append(f"Vencimento: {d}")

                        # Busca em tags de parcelas padrão
                        dups = root.xpath('//dup | //parcela')
                        for d in dups:
                            dv = d.xpath('.//dVenc/text() | .//venc/text()')
                            if dv: vencimentos.append(f"Vencimento: {dv
