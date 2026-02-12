import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
from datetime import datetime, timedelta
import plotly.express as px

# --- 1. CONFIGURAÇÃO GERAL ---
st.set_page_config(page_title="Qerqueijo Frota", page_icon="🚛", layout="wide")

# Lista fixa das viaturas
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
    header[data-testid="stHeader"] {background: transparent !important;}
    
    .stApp { background-color: white; }
    h1, h2, h3 { color: #002060; }
    .stButton>button { background-color: #002060; color: white; border: none; }
    .stButton>button:hover { background-color: #001540; color: white; }
    div.stImage > img { display: block; margin-left: auto; margin-right: auto; }
    
    [data-testid="stSidebar"] { background-color: #F0F2F6; }
    
    /* Menu Horizontal */
    div[role="radiogroup"] > label > div:first-of-type { display: none; }
    div[role="radiogroup"] { flex-direction: row; justify-content: center; gap: 20px; }
    div[data-testid="metric-container"] { background-color: #F0F2F6; padding: 10px; border-radius: 5px; }
    </style>
    """, unsafe_allow_html=True)

NOME_FOLHA_GOOGLE = "dados_frota"

# --- 2. LIGAÇÕES ---
def conectar_gsheets():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    try:
        if "service_account" in st.secrets:
            creds_dict = st.secrets["service_account"]
            if "gcp_json" in creds_dict:
                creds_json = json.loads(creds_dict["gcp_json"])
            else: creds_json = creds_dict
        else: return None
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
        return gspread.authorize(creds).open(NOME_FOLHA_GOOGLE)
    except: return None

# --- 3. DADOS ---
def carregar_dados():
    wb = conectar_gsheets()
    if wb:
        try:
            df = pd.DataFrame(wb.sheet1.get_all_records())
            # Se vier vazio ou sem colunas, retorna estrutura padrão
            if df.empty or len(df.columns) < 2: 
                return pd.DataFrame(columns=["Data_Fatura", "Matricula", "Categoria", "Valor", "KM_Atuais", "Num_Fatura", "Descricao"])
            return df
        except: return pd.DataFrame()
    return pd.DataFrame()

def guardar_registo(dados):
    wb = conectar_gsheets()
    if wb:
        try: wb.sheet1.append_row(dados); return True
        except: return False
    return False

def eliminar_registo(indice):
    wb = conectar_gsheets()
    if wb:
        try: wb.sheet1.delete_rows(indice + 2); return True
        except: return False
    return False

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
            else:
                sheet.append_row(dados)
            return True
        except: return False
    return False

# --- LOGO & ALERTAS ---
def mostrar_logo():
    caminhos = [".streamlit/logo.png", "logo.png", ".streamlit/Logo.png", "Logo.png"]
    encontrou = False
    for c in caminhos:
        try: st.image(c, use_container_width=True); encontrou = True; break
        except: continue
    if not encontrou: st.header("QERQUEIJO 🧀")

def verificar_alertas(df_val):
    if df_val.empty: return
    hoje = datetime.now().date()
    for _, row in df_val.iterrows():
        mat = row['Matricula']
        for tipo, col in [("Seguro", "Data_Seguro"), ("Inspeção", "Data_Inspecao"), ("IUC", "Data_IUC")]:
            d_str = str(row.get(col)).strip()
            if d_str and d_str not in ["", "None", "nan"]:
                try:
                    d_val = datetime.strptime(str(d_str), "%Y-%m-%d").date()
                    dias = (d_val - hoje).days
                    if dias < 0: st.error(f"🚨 **URGENTE ({mat}):** {tipo} expirou dia {d_val.strftime('%d/%m')}!")
                    elif dias <= 7: st.error(f"⏰ **CRÍTICO ({mat}):** {tipo} vence em {dias} dias")
                    elif dias <= 30: st.warning(f"⚠️ **Atenção ({mat}):** {tipo} vence em {dias} dias")
                except: continue

# --- APP ---
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
        mostrar_logo(); st.write("---")
        if st.button("Sair"): st.session_state['logado'] = False; st.rerun()

    df_alertas = carregar_validades()
    if not df_alertas.empty: verificar_alertas(df_alertas)

    st.title("🚛 Gestão de Frota")

    # Menu Horizontal
    menu = st.radio("", ["➕ Adicionar Despesa", "📊 Resumo Financeiro", "📅 Validades & Alertas"], horizontal=True)
    st.divider()

    # --- ABA 1: ADICIONAR ---
    if menu == "➕ Adicionar Despesa":
        with st.form("nova_despesa", clear_on_submit=True):
            c1, c2 = st.columns(2)
            mat = c1.selectbox("Viatura", LISTA_VIATURAS)
            cat = c1.selectbox("Categoria", ["Combustível", "Pneus", "Oficina", "Frio", "Lavagem", "Portagens"])
            dt = c2.date_input("Data Fatura", datetime.now())
            nf = c2.text_input("Nº Fatura")
            k1, k2, k3 = st.columns(3)
            km = k1.number_input("KMs", step=1)
            val = k2.number_input("Valor (€)", min_value=0.0, step=0.01)
            desc = k3.text_input("Descrição")
            if st.form_submit_button("💾 Gravar", type="primary", use_container_width=True):
                if val > 0 and nf:
                    if guardar_registo([str(dt), mat, cat, val, km, nf, desc]):
                        st.success("✅ Fatura registada!")
                        st.rerun()
                else: st.warning("Preenche Valor e Nº Fatura")

    # --- ABA 2: RESUMO ---
    elif menu == "📊 Resumo Financeiro":
        df = carregar_dados()
        if not df.empty and len(df) > 0:
            # CORREÇÃO DE VALORES E DATAS
            def corrigir_valor(v):
                try:
                    v_str = str(v).replace('€', '').strip()
                    if ',' in v_str: v_str = v_str.replace('.', '').replace(',', '.')
                    valor = float(v_str)
                    if valor > 2000: return valor / 100 # Corrige erro de virgula
                    return valor
                except: return 0.0

            df['Valor'] = df['Valor'].apply(corrigir_valor)
            df['Valor_Visual'] = df['Valor'].apply(lambda x: f"{x:,.2f} €".replace(",", "X").replace(".", ",").replace("X", "."))
            
            # Converte data com tratamento de erro
            df['Data_Fatura'] = pd.to_datetime(df['Data_Fatura'], errors='coerce')
            df = df.dropna(subset=['Data_Fatura']) # Remove linhas com datas inválidas para não partir o gráfico

            # Filtros
            with st.expander("🗑️ Eliminar Fatura"):
                c1, c2 = st.columns(2)
                l_mat = ["Todas"] + list(df["Matricula"].unique())
                f_mat = c1.selectbox("Viatura", l_mat)
                f_doc = c2.text_input("Nº Fatura")
                df_del = df.copy(); df_del['Idx'] = df_del.index
                if f_mat != "Todas": df_del = df_del[df_del["Matricula"] == f_mat]
                if f_doc: df_del = df_del[df_del["Num_Fatura"].astype(str).str.contains(f_doc, case=False)]
                if not df_del.empty:
                    ops = [f"Linha {r.Idx} | {r.Data_Fatura.date()} | {r.Matricula} | {r.Valor_Visual}" for _, r in df_del.iterrows()]
                    escolha = st.selectbox("Selecionar:", ops[::-1])
                    if st.button("❌ Apagar"):
                        if eliminar_registo(int(escolha.split(" |")[0].replace("Linha ", ""))): st.rerun()

            st.divider()
            
            with st.expander("🔍 Configurar Filtros", expanded=True):
                c1, c2, c3 = st.columns(3)
                f_mats = c1.multiselect("Viaturas:", sorted(df["Matricula"].unique()))
                f_cats = c2.multiselect("Categorias:", sorted(df["Categoria"].unique()))
                f_nf = c3.text_input("Procurar Fatura:")

            df_f = df.copy()
            if f_mats: df_f = df_f[df_f["Matricula"].isin(f_mats)]
            if f_cats: df_f = df_f[df_f["Categoria"].isin(f_cats)]
            if f_nf: df_f = df_f[df_f["Num_Fatura"].astype(str).str.contains(f_nf, case=False)]

            if not df_f.empty:
                c_g1, c_g2 = st.columns(2)
                
                # Gráfico Linha (Evolução)
                try:
                    df_ev = df_f.groupby(df_f['Data_Fatura'].dt.to_period('M').astype(str))['Valor'].sum().reset_index()
                    df_ev.columns = ['Mês', 'Valor']
                    fig_line = px.line(df_ev, x='Mês', y='Valor', title="Evolução Mensal (€)", markers=True)
                    fig_line.update_traces(line_color='#002060')
                    c_g1.plotly_chart(fig_line, use_container_width=True)
                except: c_g1.error("Erro ao gerar gráfico de evolução.")
                
                # Gráfico Tarte
                try:
                    fig_pie = px.pie(df_f, values='Valor', names='Categoria', title="Custos por Categoria", hole=0.4)
                    c_g2.plotly_chart(fig_pie, use_container_width=True)
                except: c_g2.error("Erro ao gerar gráfico de categorias.")

                st.subheader("📋 Detalhe das Faturas")
                st.dataframe(df_f, use_container_width=True, hide_index=True,
                    column_order=["Data_Fatura", "Matricula", "Categoria", "Valor_Visual", "KM_Atuais", "Num_Fatura", "Descricao"],
                    column_config={
                        "Valor_Visual": st.column_config.TextColumn("Valor (€)"),
                        "Data_Fatura": st.column_config.DateColumn("Data", format="DD/MM/YYYY")
                    }
                )
            else: st.warning("Sem dados para os filtros selecionados.")
        else: st.info("Ainda não existem faturas registadas.")

    # --- ABA 3: VALIDADES ---
    elif menu == "📅 Validades & Alertas":
        st.subheader("Controlo de Prazos")
        st.info("ℹ️ Para apagar uma data, deixa o campo vazio e clica em Atualizar.")
        
        with st.expander("📝 Atualizar Validade", expanded=True):
            with st.form("form_validade"):
                c1, c2 = st.columns(2)
                v_mat = c1.selectbox("Viatura", LISTA_VIATURAS)
                v_obs = c2.text_input("Observações")
                
                c3, c4, c5 = st.columns(3)
                d_seg = c3.date_input("Seguro", value=None)
                d_insp = c4.date_input("Inspeção", value=None)
                d_iuc = c5.date_input("IUC", value=None)
                
                if st.form_submit_button("Atualizar Datas", type="primary", use_container_width=True):
                    dados_v = [v_mat, str(d_seg) if d_seg else "", str(d_insp) if d_insp else "", str(d_iuc) if d_iuc else "", v_obs]
                    if guardar_validade_nova(dados_v):
                        st.success(f"✅ {v_mat} atualizada!")
                        st.rerun()
                    else: st.error("Erro ao gravar.")
        
        st.divider()
        df_vals = carregar_validades()
        if not df_vals.empty:
            st.dataframe(df_vals, use_container_width=True, hide_index=True, column_config={"Data_Seguro": st.column_config.DateColumn("Seguro", format="DD/MM/YYYY"), "Data_Inspecao": st.column_config.DateColumn("Inspeção", format="DD/MM/YYYY"), "Data_IUC": st.column_config.DateColumn("IUC", format="DD/MM/YYYY")})
