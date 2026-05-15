import streamlit as st
from lxml import etree
import re
import zipfile
from supabase import create_client

# --- COLOQUE SEUS DADOS AQUI ---
SUPABASE_URL = "SUA_URL_AQUI"
SUPABASE_KEY = "SUA_KEY_AQUI"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="Ginseng Fiscal", layout="wide")

st.title("🛡️ Sistema Permanente Grupo Ginseng")

aba1, aba2 = st.tabs(["🔍 Consultar Nota", "📦 Upload de Lote"])

with aba2:
    st.header("Upload para o Banco de Dados")
    arquivos_up = st.file_uploader("Suba o ZIP aqui", type=['xml', 'zip'], accept_multiple_files=True)
    if st.button("🚀 Salvar na Nuvem"):
        if arquivos_up:
            total = 0
            for item in arquivos_up:
                if item.name.lower().endswith('.zip'):
                    with zipfile.ZipFile(item) as z:
                        for info in z.infolist():
                            if not info.is_dir() and info.filename.lower().endswith('.xml'):
                                conteudo = z.read(info.filename).decode('utf-8', errors='ignore')
                                supabase.table("notas_fiscais").insert({"nome_arquivo": info.filename, "conteudo_xml": conteudo}).execute()
                                total += 1
                else:
                    conteudo = item.read().decode('utf-8', errors='ignore')
                    supabase.table("notas_fiscais").insert({"nome_arquivo": item.name, "conteudo_xml": conteudo}).execute()
                    total += 1
            st.success(f"✅ {total} notas salvas permanentemente!")

with aba1:
    st.header("Busca de Vencimentos")
    busca = st.text_input("Digite o número, chave ou código (Ex: LM9BUVRG):")
    if busca:
        res = supabase.table("notas_fiscais").select("*").ilike("conteudo_xml", f"%{busca}%").execute()
        if res.data:
            for nota in res.data:
                xml_str = nota['conteudo_xml']
                parser = etree.XMLParser(recover=True, remove_blank_text=True)
                root = etree.fromstring(xml_str.encode('utf-8'), parser=parser)
                
                # Limpa namespaces para ler Maceió/TOTVS
                for elem in root.getiterator():
                    if not (isinstance(elem, etree._Comment) or isinstance(elem, etree._ProcessingInstruction)):
                        elem.tag = etree.QName(elem).localname
                etree.cleanup_namespaces(root)

                emitente = root.xpath('//xNome/text() | //RazaoSocialPrestador/text()')
                with st.expander(f"📄 Nota: {nota['nome_arquivo']}"):
                    st.info(f"🏢 Fornecedor: {emitente[0] if emitente else 'Não identificado'}")
                    # Procura vencimento no texto (Padrão TOTVS/Boticário)
                    texto = root.xpath('//Discriminacao/text() | //xInfComp/text() | //xDescServ/text()')
                    if texto:
                        datas = re.findall(r'VENC(?:\.:|:)?\s*(\d{2}/\d{2}/\d{4})|R\$\s*[\d,.]+\s*VENC\s*(\d{2}/\d{2}/\d{4})', texto[0].upper())
                        for d in datas:
                            st.warning(f"📅 Vencimento: {d[0] or d[1]}")
        else:
            st.error("Nota não encontrada no banco de dados.")
