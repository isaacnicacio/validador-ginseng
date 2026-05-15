import streamlit as st
from lxml import etree
import re
import zipfile
import io

st.set_page_config(page_title="Portal Fiscal Ginseng", layout="wide")

# Garante que as notas fiquem guardadas enquanto o site estiver aberto
if 'banco_notas' not in st.session_state:
    st.session_state['banco_notas'] = {}

def extrair_id_unico(conteudo, nome_original):
    try:
        root = etree.fromstring(conteudo)
        ids = root.xpath('//@Id | //@id | //@ID')
        if ids: return re.sub(r'\D', '', ids[0])
        num = root.xpath('//*[local-name()="nNF"] | //*[local-name()="nNFSe"]')
        cnpj = root.xpath('//*[local-name()="CNPJ"]')
        if num and cnpj: return f"{cnpj[0].text}_{num[0].text}"
    except: pass
    return nome_original.replace(".xml", "")

st.title("🛡️ Sistema Integrado Grupo Ginseng")
st.metric("📊 Notas na Base Atual", len(st.session_state['banco_notas']))

aba1, aba2 = st.tabs(["🔍 Consultar Nota", "📦 Upload de Lote"])

# --- ABA DE CONSULTA ---
with aba1:
    st.header("Busca de Vencimentos")
    if not st.session_state['banco_notas']:
        st.warning("⚠️ Base vazia. Faça o upload na aba ao lado.")
    else:
        busca = st.text_input("Digite o número ou a chave da nota:")
        if busca:
            encontrados = [k for k in st.session_state['banco_notas'].keys() if busca in k]
            if encontrados:
                for k in encontrados:
                    with st.expander(f"📄 Nota: {k}", expanded=True):
                        conteudo = st.session_state['banco_notas'][k]
                        root = etree.fromstring(conteudo)
                        
                        # Nome Fornecedor
                        fornecedor = root.xpath('//*[local-name()="xNome"]/text()')
                        if fornecedor: st.info(f"🏢 **Fornecedor:** {fornecedor[0]}")
                        
                        # Lógica de Vencimentos
                        inf_comp = root.xpath('//*[local-name()="xInfComp"]/text()')
                        dups = root.xpath('//*[local-name()="dup"]')
                        achou = False
                        
                        if inf_comp:
                            prazos = re.findall(r'R\$\s*[\d,.]+\s*venc\s*\d{2}/\d{2}/\d{4}', inf_comp[0])
                            for p in prazos:
                                st.warning(f"📅 **{p}**")
                                achou = True
                        
                        for d in dups:
                            venc = d.xpath('.//*[local-name()="dVenc"]/text()')
                            valor = d.xpath('.//*[local-name()="vDup"]/text()')
                            if venc:
                                st.success(f"📅 Vencimento: **{venc[0]}** | R$ {valor[0] if valor else ''}")
                                achou = True
                        
                        if not achou: st.error("Vencimento não localizado no XML.")
            else:
                st.error("Nota não encontrada.")

# --- ABA DE UPLOAD ---
with aba2:
    st.header("Upload de Lote")
    arquivos_up = st.file_uploader("Arraste o ZIP de 2.000 notas aqui", type=['xml', 'zip'], accept_multiple_files=True)
    if st.button("🚀 Processar Tudo"):
        if arquivos_up:
            total = 0
            for item in arquivos_up:
                if item.name.endswith('.zip'):
                    with zipfile.ZipFile(item) as z:
                        for info in z.infolist():
                            if not info.is_dir() and info.filename.lower().endswith('.xml'):
                                conteudo = z.read(info.filename)
                                chave = extrair_id_unico(conteudo, info.filename)
                                # Adiciona um sufixo se a chave for igual para não perder arquivos
                                if chave in st.session_state['banco_notas']:
                                    chave = f"{chave}_{total}"
                                st.session_state['banco_notas'][chave] = conteudo
                                total += 1
                else:
                    conteudo = item.read()
                    chave = extrair_id_unico(conteudo, item.name)
                    st.session_state['banco_notas'][chave] = conteudo
                    total += 1
            st.success(f"✅ {total} arquivos adicionados à base!")
            st.rerun()   
                    
