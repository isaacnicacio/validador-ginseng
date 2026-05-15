import streamlit as st
from lxml import etree
import re
import zipfile
import io

st.set_page_config(page_title="Portal Fiscal Ginseng", layout="wide")

if 'banco_notas' not in st.session_state:
    st.session_state['banco_notas'] = {}

def extrair_id_unico(conteudo, nome_original):
    try:
        root = etree.fromstring(conteudo)
        # Tenta Chave de Acesso
        ids = root.xpath('//@Id | //@id | //@ID')
        if ids: return re.sub(r'\D', '', ids[0])
        # Tenta CNPJ + Número
        num = root.xpath('//*[local-name()="nNF"] | //*[local-name()="nNFSe"]')
        cnpj = root.xpath('//*[local-name()="CNPJ"]')
        if num and cnpj: return f"{cnpj[0].text}_{num[0].text}"
    except: pass
    # Se falhar tudo, usa o nome original do ficheiro para não perder a nota
    return nome_original.replace(".xml", "")

st.title("🛡️ Sistema Ginseng - Processamento Total")
st.metric("📊 Notas na Base", len(st.session_state['banco_notas']))

aba1, aba2 = st.tabs(["🔍 Consultar", "📦 Upload Total"])

with aba2:
    st.header("Upload de Lote")
    arquivos_up = st.file_uploader("Suba o ZIP aqui", type=['xml', 'zip'], accept_multiple_files=True)
    
    if st.button("🚀 Processar Tudo (Sem Descartes)"):
        if arquivos_up:
            cont_xml = 0
            for item in arquivos_up:
                if item.name.endswith('.zip'):
                    with zipfile.ZipFile(item) as z:
                        for info in z.infolist():
                            # Ignora pastas, foca apenas em ficheiros .xml
                            if not info.is_dir() and info.filename.lower().endswith('.xml'):
                                conteudo = z.read(info.filename)
                                chave = extrair_id_unico(conteudo, info.filename)
                                # Se a chave já existe, cria uma variante para não apagar a anterior
                                if chave in st.session_state['banco_notas']:
                                    chave = f"{chave}_{cont_xml}"
                                st.session_state['banco_notas'][chave] = conteudo
                                cont_xml += 1
                else:
                    conteudo = item.read()
                    chave = extrair_id_unico(conteudo, item.name)
                    st.session_state['banco_notas'][chave] = conteudo
                    cont_xml += 1
            
            st.success(f"✅ Processados {cont_xml} ficheiros XML do seu lote!")
            st.rerun()

with aba1:
    st.header("Busca")
    if not st.session_state['banco_notas']:
        st.warning("Base vazia.")
    else:
        busca = st.text_input("Digite a chave ou número:")
        if busca:
            encontrados = [k for k in st.session_state['banco_notas'].keys() if busca in k]
            if encontrados:
                for k in encontrados:
                    st.write(f"📄 Nota: {k}")
                    # Lógica de extração de vencimentos aqui...
            else:
                st.error("Não encontrado.")
