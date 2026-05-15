import streamlit as st
from lxml import etree
import re
import zipfile
import io

st.set_page_config(page_title="Portal Fiscal Ginseng", layout="wide")

if 'banco_notas' not in st.session_state:
    st.session_state['banco_notas'] = {}

def extrair_qualquer_id(conteudo, nome_arquivo):
    try:
        parser = etree.XMLParser(recover=True)
        root = etree.fromstring(conteudo, parser=parser)
        
        # 1. Tenta Chave de Acesso (longa)
        ids = root.xpath('//@Id | //@id | //@ID')
        if ids: return re.sub(r'^(NFe|NFS|NFSe)', '', ids[0])
        
        # 2. Tenta Número da Nota (nNF ou nNFSe)
        num = root.xpath('//*[local-name()="nNF"]/text() | //*[local-name()="nNFSe"]/text()')
        if num: return num[0]
        
        # 3. Tenta Código de Verificação (como os da sua imagem)
        cod = root.xpath('//*[local-name()="vCodigo"]/text() | //*[local-name()="cVerif"]/text()')
        if cod: return cod[0]
        
    except: pass
    # 4. Se falhar tudo, usa o nome do arquivo que está no ZIP (sem o .xml)
    return nome_arquivo.replace(".xml", "").replace(".XML", "")

st.title("🛡️ Sistema Integrado Grupo Ginseng")

col1, col2 = st.columns(2)
col1.metric("📊 Notas Prontas", len(st.session_state['banco_notas']))

aba1, aba2 = st.tabs(["🔍 Consultar", "📦 Upload"])

with aba2:
    st.header("Upload Total")
    # Aumentando o limite para arquivos pesados
    arquivos_up = st.file_uploader("Suba o ZIP aqui", type=['xml', 'zip'], accept_multiple_files=True)
    
    if st.button("🚀 Processar Sem Exceções"):
        if arquivos_up:
            total_lido = 0
            for item in arquivos_up:
                if item.name.lower().endswith('.zip'):
                    with zipfile.ZipFile(item) as z:
                        for info in z.infolist():
                            if not info.is_dir() and info.filename.lower().endswith('.xml'):
                                conteudo = z.read(info.filename)
                                # Pega o ID ou o nome do arquivo
                                chave = extrair_qualquer_id(conteudo, info.filename)
                                
                                # Garante que não vai ignorar se a chave for repetida
                                final_key = chave
                                count = 1
                                while final_key in st.session_state['banco_notas']:
                                    final_key = f"{chave}_{count}"
                                    count += 1
                                
                                st.session_state['banco_notas'][final_key] = conteudo
                                total_lido += 1
                else:
                    conteudo = item.read()
                    chave = extrair_qualquer_id(conteudo, item.name)
                    st.session_state['banco_notas'][chave] = conteudo
                    total_lido += 1
            
            st.success(f"✅ {total_lido} arquivos processados e salvos!")
            st.rerun()

with aba1:
    st.header("Busca")
    busca = st.text_input("Digite a Chave, Código (Ex: LM9BUVRG) ou Número:")
    if busca:
        # Busca parcial (ignora maiúsculas/minúsculas)
        encontrados = [k for k in st.session_state['banco_notas'].keys() if busca.upper() in k.upper()]
        
        if encontrados:
            for k in encontrados:
                with st.expander(f"📄 Nota: {k}", expanded=True):
                    conteudo = st.session_state['banco_notas'][k]
                    root = etree.fromstring(conteudo, parser=etree.XMLParser(recover=True))
                    
                    fornecedor = root.xpath('//*[local-name()="xNome"]/text()')
                    if fornecedor: st.info(f"🏢 **Fornecedor:** {fornecedor[0]}")
                    
                    # Lógica de Vencimentos
                    inf_comp = root.xpath('//*[local-name()="xInfComp"]/text()')
                    dups = root.xpath('//*[local-name()="dup"]')
                    achou = False
                    
                    if inf_comp:
                        # Regex flexível para pegar valores e datas
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
                    
                    if not achou: st.error("Vencimento não encontrado no XML.")
        else:
            st.error("Nenhuma nota encontrada com esse termo.")
