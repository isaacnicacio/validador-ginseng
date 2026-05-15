import streamlit as st
from lxml import etree
import re
import zipfile

st.set_page_config(page_title="Portal Fiscal Ginseng", layout="wide")

if 'banco_notas' not in st.session_state:
    st.session_state['banco_notas'] = {}

st.title("🛡️ Sistema Integrado Grupo Ginseng")

st.sidebar.metric("📊 Notas na Base", len(st.session_state['banco_notas']))
if st.sidebar.button("🗑️ Limpar Base"):
    st.session_state['banco_notas'] = {}
    st.rerun()

aba1, aba2 = st.tabs(["🔍 Consultar Nota", "📦 Upload de Lote"])

with aba2:
    st.header("Upload de Lote")
    arquivos_up = st.file_uploader("Arraste o ZIP ou XMLs aqui", type=['xml', 'zip'], accept_multiple_files=True)
    
    if st.button("🚀 Processar Tudo"):
        if arquivos_up:
            lidos = 0
            for item in arquivos_up:
                if item.name.lower().endswith('.zip'):
                    with zipfile.ZipFile(item) as z:
                        for info in z.infolist():
                            if not info.is_dir() and info.filename.lower().endswith('.xml'):
                                conteudo = z.read(info.filename).decode('utf-8', errors='ignore')
                                st.session_state['banco_notas'][info.filename] = conteudo
                                lidos += 1
                else:
                    conteudo = item.read().decode('utf-8', errors='ignore')
                    st.session_state['banco_notas'][item.name] = conteudo
                    lidos += 1
            st.success(f"✅ {lidos} notas indexadas!")
            st.rerun()

with aba1:
    st.header("Busca")
    termo = st.text_input("Digite o número da nota, código ou parte do conteúdo:")
    
    if termo:
        termo = termo.strip().upper()
        # Busca dentro do texto bruto de cada nota
        resultados = [v for k, v in st.session_state['banco_notas'].items() if termo in v.upper()]

        if resultados:
            st.success(f"Encontrei {len(resultados)} nota(s)!")
            for xml_str in resultados:
                try:
                    # REMOVE NAMESPACES: Isso faz o código ler notas de qualquer prefeitura/formato
                    parser = etree.XMLParser(recover=True, remove_blank_text=True)
                    root = etree.fromstring(xml_str.encode('utf-8'), parser=parser)
                    for elem in root.getiterator():
                        if not (isinstance(elem, etree._Comment) or isinstance(elem, etree._ProcessingInstruction)):
                            elem.tag = etree.QName(elem).localname
                    etree.cleanup_namespaces(root)

                    # Extração de Dados
                    emitente = root.xpath('//emit/xNome/text() | //RazaoSocialPrestador/text() | //xNome/text()')
                    numero = root.xpath('//nNFSe/text() | //nNF/text() | //NumeroNFe/text()')
                    valor = root.xpath('//vServ/text() | //vNF/text() | //ValorServicos/text()')

                    with st.expander(f"📄 Nota {numero[0] if numero else 'S/N'} - {emitente[0] if emitente else 'Fornecedor'}", expanded=True):
                        st.write(f"💰 **Valor Total:** R$ {valor[0] if valor else 'Não identificado'}")
                        
                        vencimentos = []
                        
                        # 1. Busca em Discriminacao/InfComp (Texto corrido)
                        texto_extra = root.xpath('//xDescServ/text() | //Discriminacao/text() | //xInfComp/text()')
                        if texto_extra:
                            datas = re.findall(r'VENC(?:\.:|:)?\s*(\d{2}/\d{2}/\d{4})', texto_extra[0].upper())
                            datas_bot = re.findall(r'R\$\s*[\d,.]+\s*venc\s*(\d{2}/\d{2}/\d{4})', texto_extra[0])
                            for d in (datas + datas_bot):
                                vencimentos.append(f"Vencimento: {d} (Encontrado no texto)")

                        # 2. Busca em Tags estruturadas
                        dups = root.xpath('//dup | //parcela')
                        for d in dups:
                            dv = d.xpath('.//dVenc/text() | .//venc/text()')
                            if dv: vencimentos.append(f"Vencimento: {dv[0]} (Tag estruturada)")

                        if vencimentos:
                            for v in set(vencimentos):
                                st.warning(f"📅 **{v}**")
                        else:
                            st.error("⚠️ Vencimento não encontrado no XML. Verifique a descrição abaixo:")
                            if texto_extra: st.text_area("Descrição:", texto_extra[0], height=100)
                            
                except Exception as e:
                    st.error(f"Erro técnico ao processar esta nota: {e}")
        else:
            st.error("Nenhuma nota encontrada.")
