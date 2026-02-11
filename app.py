import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
from datetime import datetime, timedelta
import plotly.express as px

# --- CONFIGURAÇÃO VISUAL ---
st.set_page_config(page_title="Qerqueijo Frota", page_icon="🚛", layout="wide")

# --- LISTA MESTRA DE VIATURAS ---
LISTA_VIATURAS = [
    "06-QO-19", "59-RT-87", "19-TF-05", "28-UO-50", "17-UM-19", "83-ZL-79", 
    "83-ZL-83", "AD-66-VN", "AD-71-VN", "AL-36-FF", "AL-30-FF", "AT-79-QU", 
    "AT-87-QU", "BE-64-TJ", "BE-16-TL", "BE-35-TJ", "BL-33-LG", "BL-68-LF", 
    "BR-83-SQ", "BU-45-NF", "BX-53-AB", "BO-08-DB", "AU-56-NT", "74-LU-19"
]

# --- CSS LIMPO ---
st.markdown("""
    <style>
    footer {visibility: hidden;}
    .stAppDeployButton {display: none;}
    .stApp { background-color: white; }
    [data-testid="stSidebar"] { background-color: #F0F2F6; }
    h1, h2, h3 { color: #002060; }
    .stButton>button { background-color: #002060; color: white; border: none; }
    .stButton>button:hover { background-color: #001540; color: white; }
    </style>
    """, unsafe_allow_html=True)

NOME_FOLHA_GOOGLE = "dados_frota"

def conectar_gsheets():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    try:
        if "service_account" in st.secrets:
            creds_dict = st.secrets["service_account"]
            creds_json = json.loads(creds_dict["gcp_json"]) if "gcp_json" in creds_dict else creds_dict
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
            return gspread.authorize(creds).open(NOME_FOLHA_GOOGLE)
    except: return None

# --- FUNÇÕES DE DADOS ---
def carregar_faturas():
    wb = conectar_gsheets()
    if wb:
        df = pd.DataFrame(wb.sheet1.get_all_records())
        return df if not df.empty else pd.DataFrame(columns=["Data_Fatura", "Matricula", "Categoria", "Valor", "KM_Atuais", "Num_Fatura", "Descricao"])
    return pd.DataFrame()

def carregar_validades():
    wb = conectar_gsheets()
    if wb:
        try:
            sheet = wb.worksheet("Validades")
            df = pd.DataFrame(sheet.get_all_records())
            return df if not df.empty else pd.DataFrame(columns=["Matricula", "Data_Seguro", "Data_Inspecao", "Data_IUC", "Observacoes"])
        except: return pd.DataFrame()
    return pd.DataFrame()

def atualizar_toda_tabela_validades(df_novo):
    wb = conectar_gsheets()
    if wb:
        try:
            sheet = wb.worksheet("Validades")
            sheet.clear()
            # Converte tudo para string para evitar erros de JSON
            df_str = df_novo.astype(str).replace("None", "").replace("nan", "")
            sheet.update([df_str.columns.values.tolist()] + df_str.values.tolist())
            return True
        except: return False
    return False

# --- LÓGICA DE ALERTAS ---
def verificar_alertas(df_val):
    if df_val.empty: return
    hoje = datetime.now().date()
    for _, row in df_val.iterrows():
        mat = row['Matricula']
        for tipo, col in [("Seguro", "Data_Seguro"), ("Inspeção", "Data_Inspecao"), ("IUC", "Data_IUC")]:
            data_str = row.get(col)
            if data_str and str(data_str).strip() not in ["", "None", "nan"]:
                try:
                    data_val = pd.to_datetime(data_str).date()
                    dias = (data_val - hoje).days
                    if dias < 0: st.error(f"🚨 **EXPIRADO ({mat}):** {tipo} em {data_val.strftime('%d/%m')}")
                    elif dias <= 7: st.error(f"⏰ **CRÍTICO ({mat}):** {tipo} vence em {dias} dias")
                    elif dias <= 30: st.warning(f"⚠️ **AVISO ({mat}):** {tipo} vence em {dias} dias")
                except: continue

# --- LOGIN ---
if 'logado' not in st.session_state: st.session_state['logado'] = False

if not st.session_state['logado']:
    col1, col2, col3 = st.columns([2, 2, 2])
    with col2:
        st.header("QERQUEIJO 🧀")
        senha = st.text_input("Senha", type="password")
        if st.button("Entrar", use_container_width=True):
            if senha == "queijo123": st.session_state['logado'] = True; st.rerun()
            else: st.error("Senha errada!")
else:
    # Cabeçalho de Alertas
    df_val_raw = carregar_validades()
    verificar_alertas(df_val_raw)

    tab1, tab2, tab3 = st.tabs(["➕ Adicionar", "📊 Resumo", "📅 Validades & Alertas"])

    with tab1:
        with st.form("nova_despesa", clear_on_submit=True):
            c1, c2 = st.columns(2)
            mat = c1.selectbox("Viatura", LISTA_VIATURAS)
            cat = c1.selectbox("Categoria", ["Combustível", "Pneus", "Oficina", "Frio", "Lavagem", "Portagens"])
            dt = c2.date_input("Data", datetime.now())
            nf = c2.text_input("Nº Fatura")
            k1, k2, k3 = st.columns(3)
            km = k1.number_input("KMs", step=1)
            val = k2.number_input("Valor (€)", step=0.01)
            desc = k3.text_input("Descrição")
            if st.form_submit_button("💾 Gravar Fatura", use_container_width=True):
                wb = conectar_gsheets()
                wb.sheet1.append_row([str(dt), mat, cat, val, km, nf, desc])
                st.success("Fatura Gravada!"); st.rerun()

    with tab2:
        df_fat = carregar_faturas()
        if not df_fat.empty:
            st.subheader("📋 Detalhe Financeiro")
            st.dataframe(df_fat, use_container_width=True, hide_index=True)

    with tab3:
        st.subheader("📅 Gestão de Prazos")
        st.info("💡 **Como apagar:** Seleciona a data que queres remover e prime a tecla **'Delete'** ou **'Backspace'** no teu teclado. Depois clica no botão abaixo para gravar.")
        
        # Carrega os dados para o editor
        df_prazos = carregar_validades()
        
        # Se a folha estiver vazia, cria a estrutura base com as matrículas
        if df_prazos.empty:
            df_prazos = pd.DataFrame({"Matricula": LISTA_VIATURAS})
            for col in ["Data_Seguro", "Data_Inspecao", "Data_IUC", "Observacoes"]: df_prazos[col] = ""

        # O EDITOR DE TABELA
        df_editado = st.data_editor(
            df_prazos,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Matricula": st.column_config.TextColumn("Viatura", disabled=True),
                "Data_Seguro": st.column_config.DateColumn("Seguro", format="DD/MM/YYYY"),
                "Data_Inspecao": st.column_config.DateColumn("Inspeção", format="DD/MM/YYYY"),
                "Data_IUC": st.column_config.DateColumn("IUC", format="DD/MM/YYYY"),
                "Observacoes": st.column_config.TextColumn("Notas")
            },
            key="editor_validades"
        )

        if st.button("💾 Guardar Alterações na Tabela", use_container_width=True):
            if atualizar_toda_tabela_validades(df_editado):
                st.success("✅ Validades atualizadas com sucesso!")
                st.rerun()
            else:
                st.error("Erro ao comunicar com o Google Sheets.")
