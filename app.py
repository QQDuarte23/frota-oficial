elif cat == "Seguro":
            with k2:
                val = st.number_input("Valor (€)", min_value=0.0, step=0.01)
            with k3:
                num_sinistros = st.number_input("Nº de Sinistros neste seguro", min_value=0, step=1, value=0)
                desc_input = st.text_input("Descrição (Opcional)")
                
                if num_sinistros > 0:
                    desc = f"Sinistros: {num_sinistros} | {desc_input}".strip(" |")
                else:
                    desc = desc_input.strip()
                
        else:
            with k2:
                if cat == "Lavagem": val = st.number_input("Valor (€)", value=18.50, step=0.01)
                else: val = st.number_input("Valor (€)", min_value=0.0, step=0.01)
            with k3: 
                desc = st.text_input("Descrição")
            
        st.write("") 
        
        if st.button("💾 Gravar", type="primary", use_container_width=True):
            # 1. O ESCUDO ANTI-DUPLICAÇÃO
            df_atual = carregar_dados()
            duplicada = False
            if nf and not df_atual.empty and nf in df_atual['Num_Fatura'].values:
                duplicada = True
                
            if duplicada:
                st.error(f"🛑 ERRO: A fatura nº **{nf}** já foi registada! Não foi guardada para evitar duplicados.")
            else:
                val_para_gravar = f"{val:.2f}".replace('.', ',')

                if cat == "Lavagem":
                    if not mat: st.warning("⚠️ Escolhe pelo menos uma viatura.")
                    elif val <= 0: st.warning("⚠️ O valor tem de ser maior que 0.")
                    else:
                        sucesso = True
                        for viatura in mat:
                            if not guardar_registo([str(dt), viatura, cat, val_para_gravar, km, nf, desc]): sucesso = False
                        if sucesso:
                            st.success(f"✅ {len(mat)} lavagens registadas com sucesso!")
                            st.rerun()
                        else: st.error("Erro a gravar.")
                else:
                    if val > 0 and nf:
                        if cat == "Combustível": st.session_state['preco_gasoleo_memoria'] = preco_litro
                        if guardar_registo([str(dt), mat, cat, val_para_gravar, km, nf, desc]):
                            st.success("✅ Fatura registada!")
                            st.rerun()
                    else: st.warning("⚠️ Preenche Valor e Nº Fatura")

    # --- CONTEÚDO 2: RESUMO FINANCEIRO ---
    elif menu == "📊 Resumo Financeiro":
        df = carregar_dados()
        if not df.empty:
            
            # 2. O RADAR (Deteta faturas duplicadas que já estavam no sistema)
            faturas_contagem = df[df['Num_Fatura'] != ""]['Num_Fatura'].value_counts()
            duplicados_lista = faturas_contagem[faturas_contagem > 1].index.tolist()
            
            if duplicados_lista:
                st.error("🚨 **ATENÇÃO: Foram detetadas faturas duplicadas no sistema!**")
                st.write(f"Nºs de Fatura em duplicado: **{', '.join(duplicados_lista)}** (Usa a ferramenta Editar/Apagar abaixo para corrigir)")
            
            def limpar_valor_definitivo(row):
                v = row.get('Valor', '0')
                try:
                    if pd.isna(v) or v == "": return 0.0
                    v_str = str(v).replace('€', '').strip().replace(' ', '')
                    if '.' in v_str and ',' in v_str:
                        v_str = v_str.replace('.', '').replace(',', '.')
                    elif ',' in v_str:
                        v_str = v_str.replace(',', '.')
                    return float(v_str)
                except: return 0.0

            df['Valor'] = df.apply(limpar_valor_definitivo, axis=1)
            df['Valor_Visual'] = df['Valor'].apply(lambda x: f"{x:,.2f} €".replace(",", "X").replace(".", ",").replace("X", "."))
            df['Data_Fatura'] = pd.to_datetime(df['Data_Fatura'], errors='coerce')
            df['KM_Atuais'] = pd.to_numeric(df['KM_Atuais'], errors='coerce').fillna(0).astype(int)
            df = df.dropna(subset=['Data_Fatura']) 
            
            def extrair_litros(desc):
                try:
                    if "Litros:" in str(desc):
                        return float(str(desc).split("Litros:")[1].split("|")[0].strip().replace(',', '.'))
                except: pass
                return 0.0
            
            df['Litros'] = df['Descricao'].apply(extrair_litros)

            with st.expander("🔍 Configurar Filtros", expanded=True):
                df['Ano'] = df['Data_Fatura'].dt.year.astype(int)
                df['Mês'] = df['Data_Fatura'].dt.month.astype(int)
                
                c_ano, c_mes, c_doc = st.columns(3)
                lista_anos = ["Todos"] + sorted(list(df['Ano'].unique()), reverse=True)
                f_ano = c_ano.selectbox("Ano:", lista_anos)
                
                meses_dict = {1:"Jan", 2:"Fev", 3:"Mar", 4:"Abr", 5:"Mai", 6:"Jun", 7:"Jul", 8:"Ago", 9:"Set", 10:"Out", 11:"Nov", 12:"Dez"}
                df['Nome_Mês'] = df['Mês'].map(meses_dict)
                
                lista_meses = ["Todos"] + list(meses_dict.values())
                f_mes = c_mes.selectbox("Mês:", lista_meses)
                f_doc = c_doc.text_input("Nº Fatura:")
                
                c_mat, c_cat = st.columns(2)
                f_mats = c_mat.multiselect("Viaturas:", sorted(df["Matricula"].unique()))
                f_cats = c_cat.multiselect("Categorias:", sorted(df["Categoria"].unique()))

            df_f = df.copy()
            if f_ano != "Todos": df_f = df_f[df_f['Ano'] == f_ano]
            if f_mes != "Todos": df_f = df_f[df_f['Nome_Mês'] == f_mes]
            if f_mats: df_f = df_f[df_f["Matricula"].isin(f_mats)]
            if f_cats: df_f = df_f[df_f["Categoria"].isin(f_cats)]
            if f_doc: df_f = df_f[df_f["Num_Fatura"].astype(str).str.contains(f_doc, case=False)]

            if not df_f.empty:
                st.divider()
                
                st.subheader("📊 Resumo por Viatura e Mês")
                pivot = pd.pivot_table(df_f, values='Valor', index='Matricula', columns='Nome_Mês', aggfunc='sum', fill_value=0)
                meses_ordem = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
                cols = [m for m in meses_ordem if m in pivot.columns]
                pivot = pivot[cols]
                
                pivot['Total Gasto'] = pivot.sum(axis=1)
                pivot = pivot.sort_values('Total Gasto', ascending=False)
                for col in pivot.columns:
                    pivot[col] = pivot[col].apply(lambda x: f"{x:,.2f} €".replace(",", "X").replace(".", ",").replace("X", "."))
                    
                st.dataframe(pivot, use_container_width=True)

                st.write("---")
                
                col_g1, col_g2 = st.columns(2)
                df_ev = df_f.groupby([df_f['Data_Fatura'].dt.to_period('M').astype(str), 'Categoria'])['Valor'].sum().reset_index()
                df_ev.columns = ['Mês', 'Categoria', 'Valor'] 
                
                fig_bar_stack = px.bar(df_ev, x='Mês', y='Valor', color='Categoria', title="Evolução Mensal (Por Categoria)", text_auto='.2s')
                col_g1.plotly_chart(fig_bar_stack, use_container_width=True)
                
                fig_pie = px.pie(df_f, values='Valor', names='Categoria', title="Distribuição de Custos", hole=0.4)
                col_g2.plotly_chart(fig_pie, use_container_width=True)

                st.divider()
                
                # 3. A FERRAMENTA DE PRECISÃO (EDITAR/APAGAR)
                with st.expander("🛠️ Editar ou Apagar Fatura"):
                    c_del1, c_del2 = st.columns(2)
                    l_mat_del = ["Todas"] + list(df["Matricula"].unique())
                    f_mat_del = c_del1.selectbox("Viatura (Procurar):", l_mat_del)
                    f_doc_del = c_del2.text_input("Nº Fatura (Procurar):")
                    
                    df_del = df.copy(); df_del['Idx'] = df_del.index
                    if f_mat_del != "Todas": df_del = df_del[df_del["Matricula"] == f_mat_del]
                    if f_doc_del: df_del = df_del[df_del["Num_Fatura"].astype(str).str.contains(f_doc_del, case=False)]
                    
                    if not df_del.empty:
                        ops = [f"Linha {r.Idx} | {r.Data_Fatura.date()} | {r.Matricula} | Fatura: {r.Num_Fatura} | {r.Valor_Visual}" for _, r in df_del.iterrows()]
                        escolha = st.selectbox("Selecionar Fatura:", ops[::-1])
                        
                        idx_escolhido = int(escolha.split(" |")[0].replace("Linha ", ""))
                        dados_linha = df_del[df_del['Idx'] == idx_escolhido].iloc[0]
                        
                        st.write("---")
                        st.markdown("##### ✏️ Editar Dados da Fatura")
                        e_c1, e_c2, e_c3 = st.columns(3)
                        n_data = e_c1.date_input("Nova Data", dados_linha['Data_Fatura'])
                        n_mat = e_c2.selectbox("Nova Viatura", LISTA_VIATURAS, index=LISTA_VIATURAS.index(dados_linha['Matricula']) if dados_linha['Matricula'] in LISTA_VIATURAS else 0)
                        n_cat = e_c3.selectbox("Nova Categoria", ["Combustível", "Pneus", "Oficina", "Frio", "Lavagem", "Portagens", "Seguro", "Inspeção", "IUC"], index=["Combustível", "Pneus", "Oficina", "Frio", "Lavagem", "Portagens", "Seguro", "Inspeção", "IUC"].index(dados_linha['Categoria']) if dados_linha['Categoria'] in ["Combustível", "Pneus", "Oficina", "Frio", "Lavagem", "Portagens", "Seguro", "Inspeção", "IUC"] else 0)
                        
                        e_k1, e_k2, e_k3 = st.columns(3)
                        n_val = e_k1.number_input("Novo Valor (€)", value=float(dados_linha['Valor']), step=0.01)
                        n_km = e_k2.number_input("Novos KMs", value=int(dados_linha['KM_Atuais']), step=1)
                        n_nf = e_k3.text_input("Novo Nº Fatura", value=str(dados_linha['Num_Fatura']))
                        
                        n_desc = st.text_input("Nova Descrição", value=str(dados_linha['Descricao']))
                        
                        col_btn1, col_btn2 = st.columns(2)
                        if col_btn1.button("💾 Guardar Alterações", type="primary", use_container_width=True):
                            n_val_str = f"{n_val:.2f}".replace('.', ',')
                            if editar_registo(idx_escolhido, [str(n_data), n_mat, n_cat, n_val_str, n_km, n_nf, n_desc]):
                                st.success("✅ Fatura atualizada com sucesso!")
                                st.rerun()
                            else:
                                st.error("Erro ao atualizar fatura.")
                                
                        if col_btn2.button("❌ Eliminar Fatura", use_container_width=True):
                            if eliminar_registo(idx_escolhido): 
                                st.success("✅ Fatura eliminada!")
                                st.rerun()

                st.subheader("📋 Detalhe das Faturas (Filtradas)")
                st.dataframe(df_f, use_container_width=True, hide_index=True,
                    column_order=["Data_Fatura", "Matricula", "Categoria", "Valor_Visual", "KM_Atuais", "Num_Fatura", "Descricao"],
                    column_config={
                        "Matricula": st.column_config.TextColumn("Viatura"),
                        "Categoria": st.column_config.TextColumn("Categoria"),
                        "Valor_Visual": st.column_config.TextColumn("Valor (€)"),
                        "KM_Atuais": st.column_config.NumberColumn("KMs", format="%d km"),
                        "Data_Fatura": st.column_config.DateColumn("Data", format="DD/MM/YYYY"),
                        "Num_Fatura": st.column_config.TextColumn("Nº Fatura"),
                        "Descricao": st.column_config.TextColumn("Descrição")
                    }
                )

                st.divider()
                st.subheader("📈 Custo Total por Viatura (Detalhado)")
                df_grafico_final = df_f.groupby(['Matricula', 'Categoria'])['Valor'].sum().reset_index()
                
                fig_final = px.bar(
                    df_grafico_final, 
                    y='Matricula', 
                    x='Valor', 
                    color='Categoria', 
                    orientation='h',
                    title="Despesas por Viatura divididas por Categoria",
                    text_auto='.2s'
                )
                
                fig_final.update_layout(
                    yaxis={'categoryorder':'total ascending'}, 
                    xaxis_title="Total Gasto (€)", 
                    yaxis_title="Viatura",
                    height=600 
                )
                
                st.plotly_chart(fig_final, use_container_width=True)
                
                st.divider()
                st.subheader("⛽ Análise de Consumos Médios (L/100km)")
                
                df_comb = df_f[df_f['Categoria'] == 'Combustível'].copy()
                dados_consumo = []
                
                for mat in df_comb['Matricula'].unique():
                    df_v = df_comb[(df_comb['Matricula'] == mat) & (df_comb['KM_Atuais'] > 0) & (df_comb['Litros'] > 0)].sort_values('KM_Atuais')
                    
                    if len(df_v) > 1:
                        dist = df_v['KM_Atuais'].max() - df_v['KM_Atuais'].min()
                        litros_gastos = df_v['Litros'].iloc[1:].sum() 
                        
                        if dist > 0 and litros_gastos > 0:
                            media = (litros_gastos / dist) * 100
                            if 0 < media < 100: 
                                dados_consumo.append({
                                    'Matricula': mat, 
                                    'Média (L/100km)': round(media, 2),
                                    'KMs Percorridos': dist,
                                    'Litros Consumidos': round(litros_gastos, 2)
                                })
                
                if dados_consumo:
                    df_cons = pd.DataFrame(dados_consumo).sort_values('Média (L/100km)', ascending=False)
                    
                    c_cons1, c_cons2 = st.columns([2, 1])
                    
                    fig_cons = px.bar(
                        df_cons, 
                        x='Média (L/100km)', 
                        y='Matricula', 
                        orientation='h',
                        title="Viaturas Mais Gulosas (Média de Litros por 100km)",
                        text_auto=True,
                        color='Média (L/100km)',
                        color_continuous_scale='Reds'
                    )
                    fig_cons.update_layout(yaxis={'categoryorder':'total ascending'})
                    c_cons1.plotly_chart(fig_cons, use_container_width=True)
                    
                    c_cons2.dataframe(
                        df_cons[['Matricula', 'Média (L/100km)', 'KMs Percorridos']], 
                        use_container_width=True, 
                        hide_index=True
                    )
                else:
                    st.info("💡 Não há registos de abastecimento suficientes no período selecionado para calcular médias reais.")

            else: st.warning("Sem dados para os filtros selecionados.")

    # --- CONTEÚDO 3: VALIDADES ---
    elif menu == "📅 Validades & Alertas":
        st.subheader("Controlo de Prazos")
        st.info("ℹ️ Para **APAGAR** uma data, limpa o campo (deixa vazio) e clica em Atualizar.")
        
        with st.expander("📝 Atualizar Validade", expanded=True):
            with st.form("form_validade"):
                c_v1, c_v2 = st.columns(2)
                v_mat = c_v1.selectbox("Qual a Viatura?", LISTA_VIATURAS)
                v_obs = c_v2.text_input("Observações (Opcional)")
                
                c_d1, c_d2, c_d3 = st.columns(3)
                d_seg = c_d1.date_input("Próximo Seguro", value=None)
                d_insp = c_d2.date_input("Próxima Inspeção", value=None)
                d_iuc = c_d3.date_input("Próximo IUC", value=None)
                
                if st.form_submit_button("Atualizar Datas", type="primary", use_container_width=True):
                    dados_v = [v_mat, str(d_seg) if d_seg else "", str(d_insp) if d_insp else "", str(d_iuc) if d_iuc else "", v_obs]
                    if guardar_validade_nova(dados_v):
                        st.success(f"✅ Dados da {v_mat} atualizados!")
                        st.rerun() 
                    else: st.error("Erro.")

        st.divider()
        st.subheader("📋 Estado Geral da Frota")
        df_vals = carregar_validades()
        if not df_vals.empty:
            st.dataframe(df_vals, use_container_width=True, hide_index=True,
                column_config={
                    "Matricula": st.column_config.TextColumn("Viatura", width="small"),
                    "Data_Seguro": st.column_config.DateColumn("Seguro", format="DD/MM/YYYY"),
                    "Data_Inspecao": st.column_config.DateColumn("Inspeção", format="DD/MM/YYYY"),
                    "Data_IUC": st.column_config.DateColumn("IUC", format="DD/MM/YYYY"),
                    "Observacoes": st.column_config.TextColumn("Notas")
                }
            )
