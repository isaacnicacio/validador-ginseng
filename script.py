import streamlit as st
import os
from lxml import etree
import re
import zipfile
import io

# Pasta onde o site guardará as notas
PASTA_BASE = "base_notas_ginseng"
if not os.path.exists(PASTA_BASE):
    os.makedirs(PASTA_BASE)

st.set_page_config(page_title="Portal Fiscal Ginseng", layout="wide")

def extrair_chave_xml(conteudo_xml):
    try:
        root = etree.fromstring(conteudo_xml)
        
        # 1. Tenta o padrão clássico (Atributo Id ou ID)
        chaves = root.xpath('//@Id | //@id | //@ID')
        if chaves:
            # Remove apenas o prefixo 'NFe' ou 'NFS' e mantém o resto, mesmo que não tenha 44 dígitos
            return re.sub(r'^(NFe|NFS|NFSe)', '', chaves[0])
        
        # 2. Se não achou, tenta procurar pela tag de número da nota + CNPJ (para criar um nome único)
        numero = root.xpath('//*[local-name()="nNFSe"] | //*[local-name()="nNF"]')
        cnpj = root.xpath('//*[local-name()="CNPJ"]')
        if numero and cnpj:
            return f"{cnpj[0].text}_{numero[0].text}"
            
        # 3. Última tentativa: pega qualquer número grande no corpo do XML
        todos_numeros = re.findall(r'\d{15,50}', str(conteudo_xml))
        if todos_numeros:
            return todos_numeros[0]
            
    except:
        return None
    return None

st.title("🛡️ Sistema Integrado Grupo Ginseng")
aba1, aba2 = st.tabs(["🔍 Consultar Nota", "📦 Upload de Lote (ZIP/XML)"])

# --- ABA 2: UPLOAD E ORGANIZAÇÃO ---
with aba2:
    st.header("Upload e Organização Automática")
    st.write("Esta versão aceita NF-e, NFS-e (Boticário) e chaves não convencionais.")
    
    arquivos_up = st.file_uploader("Arraste aqui o ZIP ou XMLs", accept_multiple_files=True, type=['xml', 'zip'])
    
    if st.button("Processar e Organizar Base"):
        contador = 0
        erros = 0
        for item in arquivos_up:
            if item.name.endswith('.zip'):
                with zipfile.ZipFile(item) as z:
                    for nome_arq in z.namelist():
                        if nome_arq.endswith('.xml'):
                            conteudo = z.read(nome_arq)
                            id_nota = extrair_chave_xml(conteudo)
                            if id_nota:
                                with open(os.path.join(PASTA_BASE, f"{id_nota}.xml"), "wb") as f:
                                    f.write(conteudo)
                                contador += 1
                            else: erros += 1
            elif item.name.endswith('.xml'):
                conteudo = item.read()
                id_nota = extrair_chave_xml(conteudo)
                if id_nota:
                    with open(os.path.join(PASTA_BASE, f"{id_nota}.xml"), "wb") as f:
                        f.write(conteudo)
                    contador += 1
                else: erros += 1
        
        st.success(f"🔥 Sucesso! {contador} notas processadas!")
        if erros > 0:
            st.warning(f"⚠️ {erros} arquivos foram ignorados por não parecerem notas fiscais válidas.")

# --- ABA 1: CONSULTA ---
with aba1:
    st.header("Busca de Vencimentos")
    chave_busca = st.text_input("Digite a Chave, CNPJ ou Número da Nota:")
    
    if st.button("Verificar"):
        arquivo_encontrado = None
        # Busca parcial: se o que você digitar estiver em qualquer parte do nome do arquivo
        for f in os.listdir(PASTA_BASE):
            if chave_busca.strip() in f:
                arquivo_encontrado = os.path.join(PASTA_BASE, f)
                break
        
        if arquivo_encontrado:
            try:
                tree = etree.parse(arquivo_encontrado)
                root = tree.getroot()
                
                # Identifica Fornecedor
                nomes = root.xpath('//*[local-name()="xNome"]')
                fornecedor = nomes[0].text if nomes else "Não identificado"
                st.info(f"🏢 Fornecedor: {fornecedor}")
                
                # Busca Vencimentos em texto (Padrão Boticário)
                infos = root.xpath('//*[local-name()="xInfComp"]')
                venc_encontrado = False
                if infos and infos[0].text:
                    texto = infos[0].text
                    vencs = re.findall(r'R\$ [\d,.]+ venc \d{2}/\d{2}/\d{4}', texto)
                    for v in vencs:
                        st.warning(f"📅 {v}")
                        venc_encontrado = True
                
                # Busca Vencimentos em tags (Padrão NF-e)
                dups = root.xpath('//*[local-name()="dup"]')
                for d in dups:
                    dt = d.xpath('.//*[local-name()="dVenc"]')[0].text
                    vl = d.xpath('.//*[local-name()="vDup"]')[0].text
                    st.warning(f"📅 Vencimento: {dt} | Valor: R$ {vl}")
                    venc_encontrado = True
                
                if not venc_encontrado:
                    st.error("Nenhum vencimento encontrado no arquivo.")
            except Exception as e:
                st.error(f"Erro ao ler arquivo: {e}")
        else:
            st.error("Nota não encontrada na base.")
            
