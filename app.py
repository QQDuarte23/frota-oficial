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
            df = pd.DataFrame(sheet.get_all_records())
            if df.empty: return pd.DataFrame(columns=["Data_Fatura", "Matricula", "Categoria", "Valor", "KM_Atuais", "Num_Fatura", "Descricao"])
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
        with k1: km = st.number_input("KMs", step=1)
        with k2:
            if cat == "Lavagem": val = st.number_input("Valor (€)", value=18.50, step=0.01)
            else: val = st.number_input("Valor (€)", min_value=0.0, step=0.01)
        with k3: desc = st.text_input("Descrição")
            
        st.write("") 
        
        if st.button("💾 Gravar", type="primary", use_container_width=True):
            # AQUI ESTÁ A PROTEÇÃO: Força a gravação como STRING (texto) com vírgula!
            # O Excel em Português lê isto perfeitamente como número.
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

    # --- CONTEÚDO 2: RESUMO FINANCEIRO E TABELA DO PATRÃO ---
    elif menu == "📊 Resumo Financeiro":
        df = carregar_dados()
        if not df.empty:
            
            # --- FUNÇÃO DETETIVE ULTIMATE (Lê os novos e corrige os velhos) ---
            def limpar_valor_seguro(row):
                v = row.get('Valor', 0)
                cat = row.get('Categoria', '')
                try:
                    if pd.isna(v) or v == "": return 0.0
                    
                    # 1. Se for o FORMATO NOVO (Blindado, gravado como texto com vírgula)
                    if isinstance(v, str):
                        v_str = v.replace('€', '').strip().replace(' ', '')
                        if '.' in v_str and ',' in v_str:
                            v_str = v_str.replace('.', '').replace(',', '.')
                        elif ',' in v_str:
                            v_str = v_str.replace(',', '.')
                        return float(v_str)
                        
                    # 2. Se for o FORMATO ANTIGO (Bug do Excel, gravado como número inteiro gigante)
                    valor = float(v)
                    
                    if cat == "Lavagem":
                        if valor > 50: return valor / 10 # Transforma 185 em 18.50
                        
                    elif cat in ["Combustível", "Frio", "Oficina", "Pneus", "Portagens", "Seguro", "Inspeção", "IUC"]:
                        if valor >= 2000:       # Ex: 8706 transforma-se em 87.06
                            return valor / 100
                        elif valor > 300:       # Ex: 1084 transforma-se em 108.40 / 731 passa a 73.10
                            return valor / 10
                            
                    return valor
                except: return 0.0

            # Aplica a limpeza linha a linha
            df['Valor'] = df.apply(limpar_valor_seguro, axis=1)
            df['Valor_Visual'] = df['Valor'].apply(lambda x: f"{x:,.2f} €".replace(",", "X").replace(".", ",").replace("X", "."))
            df['Data_Fatura'] = pd.to_datetime(df['Data_Fatura'], errors='coerce')
            df = df.dropna(subset=['Data_Fatura']) 

            # Filtros Globais (Ano e Mês para o Patrão)
            with st.expander("🔍 Configurar Filtros (Data, Viatura, etc)", expanded=True):
                df['Ano'] = df['Data_Fatura'].dt.year.astype(int)
                df['Mês'] = df['Data_Fatura'].dt.month.astype(int)
                
                c_ano, c_mes, c_mat = st.columns(3)
                lista_anos = ["Todos"] + sorted(list(df['Ano'].unique()), reverse=True)
                f_ano = c_ano.selectbox("Ano:", lista_anos)
                
                meses_dict = {1:"Jan", 2:"Fev", 3:"Mar", 4:"Abr", 5:"Mai", 6:"Jun", 7:"Jul", 8:"Ago", 9:"Set", 10:"Out", 11:"Nov", 12:"Dez"}
                df['Nome_Mês'] = df['Mês'].map(meses_dict)
                
                lista_meses = ["Todos"] + list(meses_dict.values())
                f_mes = c_mes.selectbox("Mês:", lista_meses)
                
                f_mats = c_mat.multiselect("Viaturas:", sorted(df["Matricula"].unique()))

            # Aplica os Filtros
            df_f = df.copy()
            if f_ano != "Todos": df_f = df_f[df_f['Ano'] == f_ano]
            if f_mes != "Todos": df_f = df_f[df_f['Nome_Mês'] == f_mes]
            if f_mats: df_f = df_f[df_f["Matricula"].isin(f_mats)]

            if not df_f.empty:
                st.divider()
                
                # --- TABELA DO PATRÃO (PIVOT TABLE) ---
                st.subheader("📊 Resumo por Viatura e Mês")
                pivot = pd.pivot_table(df_f, values='Valor', index='Matricula', columns='Nome_Mês', aggfunc='sum', fill_value=0)
                meses_ordem = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
                cols = [m for m in meses_ordem if m in pivot.columns]
                pivot = pivot[cols]
                
                pivot['Total Gasto'] = pivot.sum(axis=1)
                pivot = pivot.sort_values('Total Gasto', ascending=False)
                for col in pivot.columns:
                    pivot[col] = pivot[col].apply(lambda x: f"{x:,.2f} €".replace(",", "X").replace(".", ","
