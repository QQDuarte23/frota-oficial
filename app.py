import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
from datetime import datetime, timedelta
import plotly.express as px

# --- 1. CONFIGURAÇÃO GERAL ---
st.set_page_config(page_title="Qerqueijo Frota", page_icon="🚛", layout="wide")

LISTA_VIATURAS = [
    "06-QO-19", "59-RT-87", "19-TF-05", "28-UO-50", "17-UM-19", "83-ZL-79", 
    "83-ZL-83", "AD-66-VN", "AD-71-VN", "AL-36-FF", "AL-30-FF", "AT-79-QU", 
    "AT-87-QU", "BE-64-TJ", "BE-16-TL", "BE-35-TJ", "BL-33-LG", "BL-68-LF", 
    "BR-83-SQ", "BU-45-NF", "BX-53-AB", "BO-08-DB", "AU-56-NT", "74-LU-19"
]

# CSS
st.markdown("""
    <style>
    [data-testid="stToolbar"] {visibility: hidden !important;}
    footer {visibility: hidden;}
    .stAppDeployButton {display: none;}
    .stApp { background-color: white; }
    [data-testid="stSidebar"] { background-color: #F0F2F6; }
    h1, h2, h3 { color: #002060; }
    .stButton>button { background-color: #002060; color: white; border: none; }
    .stButton>button:hover { background-color: #001540; color: white; }
    div.stImage > img { display: block; margin-left: auto; margin-right: auto; }
    div[role="radiogroup"] > label > div:first-of-type { display: none; }
    div[role="radiogroup"] { flex-direction: row; justify-content: center; gap: 20px; }
    div[data-testid="metric-container"] { background-color: #F0F2F6; padding: 10px; border-radius: 5px; }
    </style>
    """, unsafe_allow_html=True)

NOME_FOLHA_GOOGLE = "dados_frota"

# --- 2. LIGAÇÕES GOOGLE SHEETS ---
def conectar_gsheets():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    try:
        if "service_account" in st.secrets:
            creds_dict = st.secrets["service_account"]
            if "gcp_json" in creds_dict:
                try: creds_json = json.loads(creds_dict["gcp_json"], strict=False)
                except: creds_json = json.loads(creds_dict["gcp_json"])
            else: creds_json = creds_dict
        else: return None
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
        client = gspread.authorize(creds)
        return client.open(NOME_FOLHA_GOOGLE)
    except: return None

# --- 3. FUNÇÕES DE DADOS (FATURAS) ---
def carregar_dados():
    wb = conectar_gsheets()
    if wb:
        try:
            sheet = wb.sheet1 
            data = sheet.get_all_values()
            if not data or len(data) <= 1: 
                return pd.DataFrame(columns=["Data_Fatura", "Matricula", "Categoria", "Valor", "KM_Atuais", "Num_Fatura", "Descricao"])
            df = pd.DataFrame(data[1:], columns=data[0])
            return df
        except: return pd.DataFrame()
    return pd.DataFrame()

def guardar_registo(dados):
    wb = conectar_gsheets()
    if wb:
        try: 
            wb.sheet1.append_row(dados, value_input_option='USER_ENTERED')
            return True
        except: return False
    return False

def eliminar_registo(indice):
    wb = conectar_gsheets()
    if wb:
        try: wb.sheet1.delete_rows(indice + 2); return True
        except: return False
    return False

# --- 4. FUNÇÕES DE DADOS (VALIDADES) ---
def carregar_validades():
    wb = conectar_gsheets()
    if wb:
        try:
            sheet = wb.worksheet("Validades")
            data = sheet.get_all_records()
            df_base = pd.DataFrame({"Matricula": LISTA_VIATURAS})
            if not data: 
                for c in ["Data_Seguro", "Data_Inspecao", "Data_IUC", "Observacoes"]: df_base[c] = ""
                return df_base
            return pd.merge(df_base, pd.DataFrame(data), on="Matricula", how="left").fillna("")
        except: return pd.DataFrame()
    return pd.DataFrame()

def guardar_validade_nova(dados):
    wb = conectar_gsheets()
    if wb:
        try:
            sheet = wb.worksheet("Validades")
            try: cell = sheet.find(dados[0])
            except: cell = None
            if cell:
                linha = cell.row
                sheet.update(f"B{linha}:E{linha}", [[dados[1], dados[2], dados[3], dados[4]]])
            else: sheet.append_row(dados)
            return True
        except: return False
    return False

# --- 5. LOGO ---
def mostrar_logo():
    caminhos = [".streamlit/logo.png", "logo.png", ".streamlit/Logo.png", "Logo.png"]
    encontrou = False
    for c in caminhos:
        try: st.image(c, use_container_width=True); encontrou = True; break
        except: continue
    if not encontrou: st.header("QERQUEIJO 🧀")

# --- 6. ALERTAS ---
def verificar_alertas(df_val):
    if df_val.empty: return
    hoje = datetime.now().date()
    for _, row in df_val.iterrows():
        mat = row['Matricula']
        verificacoes = {"Seguro": row.get('Data_Seguro'), "Inspeção": row.get('Data_Inspecao'), "IUC": row.get('Data_IUC')}
        for tipo, data_str in verificacoes.items():
            if data_str and str(data_str).strip() not in ["", "None", "nan"]:
                try:
                    data_val = datetime.strptime(str(data_str), "%Y-%m-%d").date()
                    dias_restantes = (data_val - hoje).days
                    if dias_restantes < 0: st.error(f"🚨 **URGENTE ({mat}):** {tipo} expirou dia {data_val.strftime('%d/%m')}!")
                    elif dias_restantes <= 7: st.error(f"⏰ **CRÍTICO ({mat}):** {tipo} vence em {dias_restantes} dias")
                    elif dias_restantes <= 30: st.warning(f"⚠️ **Atenção ({mat}):** {tipo} vence em {dias_restantes} dias")
                except: continue

# --- 7. APP PRINCIPAL ---
if 'logado' not in st.session_state: st.session_state['logado'] = False

if not st.session_state['logado']:
    col1, col2, col3 = st.columns([2, 2, 2])
    with col2:
        st.write(""); st.write("")
        mostrar_logo()
        senha = st.text_input("Senha", type="password")
        if st.button("Entrar", type="primary", use_container_width=True):
            if senha == "queijo123": st.session_state['logado'] = True; st.rerun()
            else: st.error("Senha errada!")
else:
    with st.sidebar:
        mostrar_logo()
        st.write("---")
        if st.button("Sair"): st.session_state['logado'] = False; st.rerun()

    df_alertas = carregar_validades()
    if not df_alertas.empty: verificar_alertas(df_alertas)

    st.title("🚛 Gestão de Frota")
    menu = st.radio("", ["➕ Adicionar Despesa", "📊 Resumo Financeiro", "📅 Validades & Alertas"], horizontal=True)
    st.divider()

    # --- CONTEÚDO 1: ADICIONAR ---
    if menu == "➕ Adicionar Despesa":
        cat = st.selectbox("Categoria", ["Combustível", "Pneus", "Oficina", "Frio", "Lavagem", "Portagens", "Seguro", "Inspeção", "IUC"])
        c1, c2 = st.columns(2)
        with c1:
            if cat == "Lavagem": mat = st.multiselect("Viaturas (Podes escolher várias)", LISTA_VIATURAS)
            else: mat = st.selectbox("Viatura", LISTA_VIATURAS)
        with c2:
            dt = st.date_input("Data Fatura", datetime.now())
            nf = st.text_input("Nº Fatura")
            
        k1, k2, k3 = st.columns(3)
        with k1: 
            km = st.number_input("KMs", step=1)
        
        # LÓGICA DE CAMPOS DINÂMICOS
        if cat == "Combustível":
            with k2:
                val_comb = st.number_input("Valor Gasóleo (€)", min_value=0.0, step=0.01)
            with k3:
                tem_adblue = st.checkbox("💧 Levou AdBlue?")
                if tem_adblue:
                    val_adblue = st.number_input("Valor AdBlue (€)", min_value=0.0, step=0.01)
                else:
                    val_adblue = 0.0
            
            val = val_comb + val_adblue
            desc_input = st.text_input("Descrição (Opcional)")
            
            if tem_adblue and val_adblue > 0:
                desc = f"AdBlue: {val_adblue:.2f}€ | {desc_input}".strip(" |")
                st.info(f"💶 **Valor Total da Fatura a Gravar:** {val:.2f} € (Gasóleo + AdBlue)")
            else:
                desc = desc_input
                
        elif cat == "Frio":
            with k2:
                val = st.number_input("Valor (€)", min_value=0.0, step=0.01)
            with k3:
                tipo_frio = st.selectbox("Tipo de Serviço:", ["Revisão", "Reparação"])
                desc_input = st.text_input("Descrição (Opcional)")
                desc = f"{tipo_frio} | {desc_input}".strip(" |")

        elif cat == "Oficina":
            with k2:
                val = st.number_input("Valor (€)", min_value=0.0, step=0.01)
            with k3:
                # AQUI ESTÁ A ALTERAÇÃO: Eletricista adicionado à lista!
                tipo_oficina = st.selectbox("Tipo de Serviço:", ["Revisão", "Discos", "Pastilhas", "Acidente", "Eletricista"])
                desc_input = st.text_input("Descrição (Opcional)")
                desc = f"{tipo_oficina} | {desc_input}".strip(" |")
                
        else:
            with k2:
                if cat == "Lavagem": val = st.number_input("Valor (€)", value=18.50, step=0.01)
                else: val = st.number_input("Valor (€)", min_value=0.0, step=0.01)
            with k3: 
                desc = st.text_input("Descrição")
            
        st.write("") 
        
        if st.button("💾 Gravar", type="primary", use_container_width=True):
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
                    if guardar_registo([str(dt), mat, cat, val_para_gravar, km, nf, desc]):
                        st.success("✅ Fatura registada!")
                        st.rerun()
                else: st.warning("⚠️ Preenche Valor e Nº Fatura")

    # --- CONTEÚDO 2: RESUMO FINANCEIRO ---
    elif menu == "📊 Resumo Financeiro":
        df = carregar_dados()
        if not df.empty:
            
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
                with st.expander("🗑️ Eliminar Fatura Específica"):
                    c_del1, c_del2 = st.columns(2)
                    l_mat_del = ["Todas"] + list(df["Matricula"].unique())
                    f_mat_del = c_del1.selectbox("Viatura (Eliminar):", l_mat_del)
                    f_doc_del = c_del2.text_input("Nº Fatura (Apagar):")
                    df_del = df.copy(); df_del['Idx'] = df_del.index
                    if f_mat_del != "Todas": df_del = df_del[df_del["Matricula"] == f_mat_del]
                    if f_doc_del: df_del = df_del[df_del["Num_Fatura"].astype(str).str.contains(f_doc_del, case=False)]
                    if not df_del.empty:
                        ops = [f"Linha {r.Idx} | {r.Data_Fatura.date()} | {r.Matricula} | {r.Valor_Visual}" for _, r in df_del.iterrows()]
                        escolha = st.selectbox("Selecionar para Apagar:", ops[::-1])
                        if st.button("❌ Confirmar Eliminação"):
                            idx = int(escolha.split(" |")[0].replace("Linha ", ""))
                            if eliminar_registo(idx): st.rerun()

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
