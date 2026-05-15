import streamlit as st
import os
from lxml import etree
import re
import zipfile
import io

# Pasta onde o site guardará as notas processadas
PASTA_BASE = "base_notas_ginseng"
if not os.path.exists(PASTA_BASE):
    os.makedirs(PASTA_BASE)

st.set_page_config(page_title="Portal Fiscal Ginseng", layout="wide")

def extrair_chave_xml(conteudo_xml):
    try:
        root = etree.fromstring(conteudo_xml)
        # Busca a ID da nota (Chave de 44 dígitos)
        chave = root.xpath('//@Id') or root.xpath('//@id')
        if chave:
            return "".join(filter(str.isdigit, chave[0]))
    except:
        return None
    return None

st.title("🛡️ Sistema Integrado Grupo Ginseng")
aba1, aba2 = st.tabs(["🔍 Consultar Nota", "📦 Upload de Lote (ZIP/XML)"])

# --- ABA 2: O ORGANIZADOR AUTOMÁTICO ---
with aba2:
    st.header("Upload e Organização Automática")
    st.write("Jogue aqui o arquivo .ZIP do Qive ou os XMLs soltos.")
    
    arquivos_up = st.file_uploader("Arraste aqui", accept_multiple_files=True, type=['xml', 'zip'])
    
    if st.button("Processar e Organizar Base"):
        contador = 0
        for item in arquivos_up:
            # Se for um arquivo ZIP, o robô entra nele
            if item.name.endswith('.zip'):
                with zipfile.ZipFile(item) as z:
                    for nome_arq in z.namelist():
                        if nome_arq.endswith('.xml'):
                            conteudo = z.read(nome_arq)
                            chave = extrair_chave_xml(conteudo)
                            if chave:
                                with open(os.path.join(PASTA_BASE, f"{chave}.xml"), "wb") as f:
                                    f.write(conteudo)
                                contador += 1
            # Se for XML solto
            elif item.name.endswith('.xml'):
                conteudo = item.read()
                chave = extrair_chave_xml(conteudo)
                if chave:
                    with open(os.path.join(PASTA_BASE, f"{chave}.xml"), "wb") as f:
                        f.write(conteudo)
                    contador += 1
        
        st.success(f"🔥 Sucesso! {contador} notas foram limpas, renomeadas e salvas na base!")

# --- ABA 1: A CONSULTA (O que os outros usuários usam) ---
with aba1:
    st.header("Busca de Vencimentos")
    chave_busca = st.text_input("Digite a Chave ou o Número da Nota:")
    
    if st.button("Verificar"):
        arquivo_encontrado = None
        for f in os.listdir(PASTA_BASE):
            if chave_busca in f:
                arquivo_encontrado = os.path.join(PASTA_BASE, f)
                break
        
        if arquivo_encontrado:
            # Aqui entra a sua lógica de leitura de Boticário e NF-e que já funciona
            tree = etree.parse(arquivo_encontrado)
            root = tree.getroot()
            xml_str = etree.tostring(root, encoding='unicode')
            
            # Identifica Fornecedor
            nomes = root.xpath('//*[local-name()="xNome"]')
            st.info(f"🏢 Fornecedor: {nomes[0].text if nomes else 'Não identificado'}")
            
            # Busca Vencimentos (Lógica Boticário + Padrão)
            infos = root.xpath('//*[local-name()="xInfComp"]')
            if infos and infos[0].text:
                texto = infos[0].text
                vencs = re.findall(r'R\$ [\d,.]+ venc \d{2}/\d{2}/\d{4}', texto)
                for v in vencs: st.warning(v)
            
            dups = root.xpath('//*[local-name()="dup"]')
            for d in dups:
                st.warning(f"📅 Data: {d.find('.//*[local-name()=\"dVenc\"]').text} | R$ {d.find('.//*[local-name()=\"vDup\"]').text}")
        else:
            st.error("Nota não encontrada. Peça ao administrador para subir o XML na aba ao lado.")
