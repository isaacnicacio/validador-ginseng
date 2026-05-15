import streamlit as st
from lxml import etree
import re
import zipfile

st.set_page_config(page_title="Portal Fiscal Ginseng", layout="wide")

# Inicializa o banco de dados na memória do site
if 'banco_notas' not in st.session_state:
    st.session_state['banco_notas'] = {}

st.title("🛡️ Sistema Integrado Grupo Ginseng")

# Painel de Controle Lateral
st.sidebar.metric("📊 Notas na Base", len(st.session_state['banco_notas']))
if st.sidebar.button("🗑️ Limpar Tudo para Novo Lote"):
    st.session_state['banco_notas'] = {}
    st.rerun()

aba1, aba2 = st.tabs(["🔍 Consultar Nota", "📦 Upload de Lote (ZIP)"])

with aba2:
    st.header("Upload de Lote")
    st.write("Dica: O sistema agora aceita Notas de Serviço (TOTVS) e busca vencimentos no texto.")
    arquivos_up = st.file_uploader("Arraste o ZIP de 2.000 notas aqui", type=['xml', 'zip'], accept_multiple_files=True)
    
    if st.button("🚀 Processar e Salvar"):
        if arquivos_up:
            total_adicionado = 0
            for item in arquivos_up:
                if item.name.lower().endswith('.zip'):
                    with zipfile.ZipFile(item) as z:
                        for info in z.infolist():
                            if not info.is_dir() and info.filename.lower().endswith('.xml'):
                                conteudo = z.read(info.filename).decode('utf-8', errors='ignore')
                                
                                # CRUCIAL: Criamos um índice com o conteúdo todo para a nota "subir" de qualquer jeito
                                # Usamos o nome do arquivo no ZIP como chave única inicial
                                id_temp = info.filename
                                st.session_state['banco_notas'][id_temp] = conteudo
                                total_adicionado += 1
                else:
                    conteudo = item.read().decode('utf-8', errors='ignore')
                    st.session_state['banco_notas'][item.name] = conteudo
                    total_adicionado += 1
            
            st.success(f"✅ {total_adicionado} notas subiram para o sistema!")
            st.rerun()

with aba1:
    st.header("Busca de Vencimentos")
    busca = st.text_input("Digite o Código (Ex: LM9BUVRG), Número da Nota ou CNPJ:")
    
    if busca:
        busca = busca.strip().upper()
        # Busca inteligente: olha dentro do texto de cada nota que "subiu"
        resultados = [v for k, v in st.session_state['banco_notas'].items() if busca in v.upper()]

        if resultados:
            st.success(f"Encontrada(s) {len(resultados)} nota(s) correspondente(s)!")
            for xml_str in resultados:
                try:
                    # O parser 'recover' ajuda a ler notas com caracteres especiais
                    parser = etree.XMLParser(recover=True)
                    root = etree.fromstring(xml_str.encode('utf-8'), parser=parser)
                    
                    # Extração de Dados do Emitente
                    prestador = root.xpath('//*[local-name()="RazaoSocialPrestador"]/text() | //*[local-name()="xNome"]/text()')
                    numero = root.xpath('//*[local-name()="NumeroNFe"]/text() | //*[local-name()="nNF"]/text() | //*[local-name()="nNFSe"]/text()')
                    
                    with st.expander(f"📄 Nota {numero[0] if numero else 'S/N'} - {prestador[0] if prestador else 'Fornecedor'}", expanded=True):
                        if prestador: st.info(f"🏢 **Fornecedor:** {prestador[0]}")
                        
                        # --- LÓGICA DE VENCIMENTOS ---
                        vencimentos = []

                        # 1. Notas TOTVS/Prefeituras (Campo Discriminacao)
                        discrim = root.xpath('//*[local-name()="Discriminacao"]/text()')
                        if discrim:
                            # Procura "VENC.: 24/05/2026", "VENC 24/05/2026", etc.
                            datas = re.findall(r'VENC(?:\.:|:)?\s*(\d{2}/\d{2}/\d{4})', discrim[0].upper())
                            for d in datas:
                                vencimentos.append(f"Vencimento: {d} (Extraído da Descrição)")

                        # 2. Notas Boticário (Campo xInfComp)
                        inf_comp = root.xpath('//*[local-name()="xInfComp"]/text()')
                        if inf_comp:
                            prazos_bot = re.findall(r'R\$\s*[\d,.]+\s*venc\s*(\d{2}/\d{2}/\d{4})', inf_comp[0])
                            for p in prazos_bot:
                                vencimentos.append(f"Vencimento: {p} (Padrão Boticário)")

                        # 3. Notas de Mercadoria (Tags dup/dVenc)
                        dups = root.xpath('//*[local-name()="dup"]')
                        for d in dups:
                            dv = d.xpath('.//*[local-name()="dVenc"]/text()')
                            if dv: vencimentos.append(f"Vencimento: {dv[0]} (Tag estruturada)")

                        # Exibir resultados
                        if vencimentos:
                            for v in set(vencimentos):
                                st.warning(f"📅 **{v}**")
                        else:
                            st.error("⚠️ Vencimento não detectado automaticamente no XML.")
                            if discrim: st.text_area("Texto da Nota:", discrim[0])
                except:
                    st.error("Erro ao ler os detalhes desta nota específica.")
        else:
            st.error("Nenhuma nota encontrada com este termo.")
