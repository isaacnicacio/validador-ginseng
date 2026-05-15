import streamlit as st
import os
from lxml import etree
import re
import zipfile
import io

st.set_page_config(page_title="Portal Fiscal Ginseng", layout="wide")

# Inicializa o banco de dados na memória do navegador se não existir
if 'banco_notas' not in st.session_state:
    st.session_state['banco_notas'] = {}

def extrair_identificador_unico(conteudo_xml):
    """Tenta de todas as formas achar um nome único para a nota"""
    try:
        root = etree.fromstring(conteudo_xml)
        # 1. Padrão: Atributo ID (NFe..., NFS...)
        ids = root.xpath('//@Id | //@id | //@ID')
        if ids: return re.sub(r'\D', '', ids[0]) # Mantém só os números
        
        # 2. Padrão: Tag infNFSe ou infNFe
        inf = root.xpath('//*[local-name()="infNFSe"]/@Id | //*[local-name()="infNFe"]/@Id')
        if inf: return re.sub(r'\D', '', inf[0])

        # 3. Padrão: Número da Nota + CNPJ Emitente
        num = root.xpath('//*[local-name()="nNF"] | //*[local-name()="nNFSe"]')
        cnpj = root.xpath('//*[local-name()="CNPJ"]')
        if num and cnpj: return f"{cnpj[0].text}_{num[0].text}"

        # 4. Emergência: Qualquer número com mais de 10 dígitos no XML
        fallback = re.findall(r'\d{10,50}', str(conteudo_xml))
        if fallback: return fallback[0]
    except:
        return None
    return None

st.title("🛡️ Sistema Integrado Grupo Ginseng")
st.write(f"📊 Notas na base atual: **{len(st.session_state['banco_notas'])}**")

aba1, aba2 = st.tabs(["🔍 Consultar Nota", "📦 Upload de Lote"])

with aba2:
    st.header("Upload e Processamento")
    arquivos_up = st.file_uploader("Suba o ZIP do Qive aqui", type=['xml', 'zip'], accept_multiple_files=True)
    
    if st.button("Processar Lote Total"):
        processadas = 0
        for item in arquivos_up:
            if item.name.endswith('.zip'):
                with zipfile.ZipFile(item) as z:
                    for nome_arq in z.namelist():
                        if nome_arq.lower().endswith('.xml'):
                            conteudo = z.read(nome_arq)
                            chave = extrair_identificador_unico(conteudo)
                            if chave:
                                st.session_state['banco_notas'][chave] = conteudo
                                processadas += 1
            else:
                conteudo = item.read()
                chave = extrair_identificador_unico(conteudo)
                if chave:
                    st.session_state['banco_notas'][chave] = conteudo
                    processadas += 1
        st.success(f"✅ Processamento concluído! {processadas} arquivos lidos.")

with aba1:
    st.header("Busca de Vencimentos")
    busca = st.text_input("Digite o número da nota ou parte da chave:")
    
    if busca:
        # Busca no dicionário de memória
        resultados = [k for k in st.session_state['banco_notas'].keys() if busca in k]
        
        if resultados:
            for r in resultados:
                conteudo = st.session_state['banco_notas'][r]
                root = etree.fromstring(conteudo)
                
                st.subheader(f"📄 Nota: {r}")
                
                # Exibe Fornecedor
                fornecedor = root.xpath('//*[local-name()="xNome"]')
                if fornecedor: st.info(f"🏢 Fornecedor: {fornecedor[0].text}")
                
                # Busca Vencimentos (Texto e Tags)
                venc_texto = root.xpath('//*[local-name()="xInfComp"]')
                venc_tags = root.xpath('//*[local-name()="dup"]')
                
                achou_venc = False
                if venc_texto and venc_texto[0].text:
                    datas = re.findall(r'R\$ [\d,.]+ venc \d{2}/\d{2}/\d{4}', venc_texto[0].text)
                    for d in datas:
                        st.warning(f"📅 {d}")
                        achou_venc = True
                
                for d in venc_tags:
                    dt = d.xpath('.//*[local-name()="dVenc"]')
                    vl = d.xpath('.//*[local-name()="vDup"]')
                    if dt and vl:
                        st.warning(f"📅 Vencimento: {dt[0].text} | Valor: R$ {vl[0].text}")
                        achou_venc = True
                
                if not achou_venc:
                    st.error("⚠️ Vencimento não encontrado no XML.")
        else:
            st.error("❌ Nota não encontrada. Certifique-se de que fez o upload nesta sessão.")
            
