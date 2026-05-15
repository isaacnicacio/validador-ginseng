import streamlit as st
from lxml import etree
import re
import zipfile
from supabase import create_client

# --- DADOS DE CONEXÃO ---
SUPABASE_URL = "https://tcvfvnzsmgtjsnsphgom.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRjdmZ2bnpzbWd0c2puc3BoZ29tIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzg4MTg0NDMsImV4cCI6MjA5NDM5NDQ0M30.Sk55DOfrbMuthd2eIF68mK0w7h7PIJ4UGMT_wqagbLg"

try:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    st.error("Erro de conexão com o banco de dados.")

st.set_page_config(page_title="Ginseng Fiscal", layout="wide")
st.title("🛡️ Sistema Permanente Grupo Ginseng")

aba1, aba2 = st.tabs(["🔍 Consultar Nota", "📦 Upload de Lote"])

with aba2:
    st.header("Upload para o Banco de Dados")
    arquivos_up = st.file_uploader("Suba o ZIP aqui", type=['xml', 'zip'], accept_multiple_files=True)
    
    if st.button("🚀 Salvar na Nuvem"):
        if arquivos_up:
            total = 0
            status_placeholder = st.empty()
            
            for item in arquivos_up:
                # SE FOR ZIP: Abre e lê cada XML lá dentro
                if item.name.lower().endswith('.zip'):
                    with zipfile.ZipFile(item) as z:
                        for filename in z.namelist():
                            if filename.lower().endswith('.xml'):
                                with z.open(filename) as f:
                                    conteudo = f.read().decode('utf-8', errors='ignore')
                                    try:
                                        supabase.table("notas_fiscais").insert({
                                            "nome_arquivo": filename, 
                                            "conteudo_xml": conteudo
                                        }).execute()
                                        total += 1
                                        status_placeholder.text(f"Enviando nota nº {total}...")
                                    except:
                                        continue
                # SE FOR XML SOLTO: Lê direto
                elif item.name.lower().endswith('.xml'):
                    conteudo = item.read().decode('utf-8', errors='ignore')
                    try:
                        supabase.table("notas_fiscais").insert({
                            "nome_arquivo": item.name, 
                            "conteudo_xml": conteudo
                        }).execute()
                        total += 1
                        status_placeholder.text(f"Enviando nota nº {total}...")
                    except:
                        continue
            
            st.success(f"✅ Sucesso! {total} notas foram guardadas na nuvem!")

with aba1:
    st.header("Busca de Vencimentos")
    busca = st.text_input("Digite o número, chave ou código (Ex: LM9BUVRG):")
    if busca:
        try:
            res = supabase.table("notas_fiscais").select("*").ilike("conteudo_xml", f"%{busca}%").execute()
            if res.data:
                st.success(f"Encontrei {len(res.data)} nota(s)!")
                for nota in res.data:
                    xml_str = nota['conteudo_xml']
                    parser = etree.XMLParser(recover=True, remove_blank_text=True)
                    root = etree.fromstring(xml_str.encode('utf-8'), parser=parser)
                    
                    # Limpa namespaces
                    for elem in root.getiterator():
                        if not (isinstance(elem, etree._Comment) or isinstance(elem, etree._ProcessingInstruction)):
                            elem.tag = etree.QName(elem).localname
                    etree.cleanup_namespaces(root)

                    emitente = root.xpath('//xNome/text() | //RazaoSocialPrestador/text()')
                    with st.expander(f"📄 Nota: {nota['nome_arquivo']}"):
                        st.info(f"🏢 Fornecedor: {emitente[0] if emitente else 'Não identificado'}")
                        
                        vencimentos = []
                        texto_campos = root.xpath('//Discriminacao/text() | //xInfComp/text() | //xDescServ/text()')
                        if texto_campos:
                            t_upper = texto_campos[0].upper()
                            datas = re.findall(r'VENC(?:\.:|:)?\s*(\d{2}/\d{2}/\d{4})', t_upper)
                            datas_bot = re.findall(r'R\$\s*[\d,.]+\s*VENC\s*(\d{2}/\d{2}/\d{4})', t_upper)
                            for d in (datas + datas_bot):
                                vencimentos.append(d)

                        dups = root.xpath('//dup | //parcela')
                        for d in dups:
                            dv = d.xpath('.//dVenc/text() | .//venc/text()')
                            if dv:
                                vencimentos.append(dv[0])

                        if vencimentos:
                            for v in sorted(list(set(vencimentos))):
                                st.warning(f"📅 Vencimento: {v}")
                        else:
                            st.error("⚠️ Vencimento não detectado automaticamente.")
        except Exception as e:
            st.error(f"Erro na busca: {e}")
