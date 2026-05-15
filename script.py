with aba1:
    st.header("🔍 Consulta de Vencimentos")
    if not st.session_state['banco_notas']:
        st.warning("⚠️ A base está vazia. Processe o ZIP na aba ao lado primeiro.")
    else:
        busca = st.text_input("Digite o número da nota ou a chave de acesso:")
        
        if busca:
            # Procura todas as notas que contêm o termo buscado
            encontrados = [k for k in st.session_state['banco_notas'].keys() if busca in k]
            
            if encontrados:
                for k in encontrados:
                    conteudo = st.session_state['banco_notas'][k]
                    try:
                        root = etree.fromstring(conteudo)
                        
                        with st.expander(f"📄 Detalhes da Nota: {k}", expanded=True):
                            # 1. Identificação do Fornecedor
                            fornecedor = root.xpath('//*[local-name()="xNome"]/text()')
                            if fornecedor:
                                st.info(f"🏢 **Fornecedor:** {fornecedor[0]}")

                            # 2. Captura de Vencimentos (Lógica para Notas de Serviço/Boticário)
                            # Procura no campo de informações complementares
                            inf_comp = root.xpath('//*[local-name()="xInfComp"]/text()')
                            
                            st.subheader("📅 Prazos de Pagamento")
                            achou_vencimento = False

                            if inf_comp:
                                # Procura o padrão "R$ X,XX venc DD/MM/AAAA" no texto
                                prazos = re.findall(r'R\$\s*[\d,.]+\s*venc\s*\d{2}/\d{2}/\d{4}', inf_comp[0])
                                for p in prazos:
                                    st.warning(f"💡 Encontrado no texto: **{p}**")
                                    achou_vencimento = True

                            # 3. Captura de Vencimentos (Lógica para NF-e padrão - duplicatas)
                            dups = root.xpath('//*[local-name()="dup"]')
                            for d in dups:
                                venc = d.xpath('.//*[local-name()="dVenc"]/text()')
                                valor = d.xpath('.//*[local-name()="vDup"]/text()')
                                if venc:
                                    valor_formatado = f"R$ {valor[0]}" if valor else ""
                                    st.success(f"📅 Parcelamento: **{venc[0]}** | {valor_formatado}")
                                    achou_vencimento = True

                            if not achou_vencimento:
                                st.error("❌ Nenhum vencimento formatado foi encontrado dentro deste XML.")
                                
                    except Exception as e:
                        st.error(f"Erro ao ler o ficheiro {k}: {e}")
            else:
                st.error("❓ Nota não encontrada na base de 2.000 arquivos.")
