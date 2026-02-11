import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
from datetime import datetime
import plotly.express as px

# --- CONFIGURAÇÃO VISUAL ---
st.set_page_config(page_title="Qerqueijo Frota", page_icon="🚛", layout="wide")

# --- LISTA MESTRA ---
LISTA_VIATURAS = [
    "06-QO-19", "59-RT-87", "19-TF-05", "28-UO-50", "17-UM-19", "83-ZL-79", 
    "83-ZL-83", "AD-66-VN", "AD-71-VN", "AL-36-FF", "AL-30-FF", "AT-79-QU", 
    "AT-87-QU", "BE-64-TJ", "BE-16-TL", "BE-35-TJ", "BL-33-LG", "BL-68-LF", 
    "BR-83-SQ", "BU-45-NF", "BX-53-AB", "BO-08-DB", "AU-56-NT", "74-LU-19"
]

# --- CSS ---
st.markdown("""
    <style>
    footer {visibility: hidden;}
    .stAppDeployButton {display: none;}
    .stApp { background-color: white; }
    h1, h2, h3 { color: #002060; }
    .stButton>button { background-color: #002060; color: white; border: none; width: 100%; }
    </style>
    """, unsafe_allow_html=True)

NOME_FOLHA_GOOGLE = "dados_frota"

def conectar_gsheets():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    try:
        creds_dict = st.secrets["service_account"]
        creds_json = json.loads(creds_dict["gcp_json"]) if "gcp_json" in creds_dict else creds_dict
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
        return gspread.authorize(creds).open(NOME_FOLHA_GOOGLE)
    except: return None

def carregar_dados_faturas():
    wb = conectar_gsheets()
    if wb:
        try:
            df = pd.DataFrame(wb.sheet1.get_all_records())
            return df if not df.empty else pd.DataFrame(columns=["Data_Fatura", "Matricula", "Categoria", "Valor", "KM_Atuais", "Num_Fatura", "Descricao"])
        except: return pd.DataFrame()
    return pd.DataFrame()

def carregar_validades():
    wb = conectar_gsheets()
    if wb:
        try:
            sheet = wb.worksheet("Validades")
            df_existente = pd.DataFrame(sheet.get_all_records())
            
            # Garantir que todas as matrículas aparecem na lista
            df_base = pd.DataFrame({"Matricula": LISTA_VIATURAS})
            if not df_existente.empty:
                df_final = pd.merge(df_base, df_existente, on="Matricula", how="left").fillna("")
            else:
                for col in ["Data_Seguro", "Data_Inspecao", "Data_IUC", "Observacoes"]: df_base[col] = ""
                df_final = df_base
            return df_final
        except: return pd.DataFrame()
    return pd.DataFrame()

def guardar_tudo_validades(df_novo):
    wb = conectar_gsheets()
    if wb:
        try:
            sheet = wb.worksheet("Validades")
            sheet.clear()
            # Adicionar cabeçalho e dados
            sheet.update([df_novo.columns.values.tolist()] + df_novo.values.tolist())
            return True
        except: return False
    return False

# --- APP ---
if 'logado' not in st.session_state: st.session_state['logado'] = False

if not st.session_state['logado']:
    col1, col2, col3 = st.columns([2, 2, 2])
    with col2:
        st.write(""); st.write("")
        st.header("QERQUEIJO 🧀")
        senha = st.text_input("Senha", type="password")
        if st.button("Entrar"):
            if senha == "queijo123": st.session_state['logado'] = True; st.rerun()
            else: st.error("Senha errada!")
else:
    tab1, tab2, tab3 = st.tabs(["➕ Adicionar", "📊 Resumo", "📅 Validades"])

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
            if st.form_submit_button("💾 Gravar"):
                wb = conectar_gsheets()
                wb.sheet1.append_row([str(dt), mat, cat, val, km, nf, desc])
                st.success("Gravado!")

    with tab2:
        df = carregar_dados_faturas()
        if not df.empty:
            st.dataframe(df, use_container_width=True)

    with tab3:
        st.header("📅 Gestão de Validades")
        st.info("Podes editar as datas diretamente na tabela. Para apagar, seleciona a data e prime 'Delete' ou limpa o texto.")
        
        df_vals = carregar_validades()
        
        # O EDITOR DE TABELA (Aqui podes editar/apagar como no Excel)
        df_editado = st.data_editor(
            df_vals,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Matricula": st.column_config.TextColumn("Viatura", disabled=True),
                "Data_Seguro": st.column_config.DateColumn("Seguro", format="DD/MM/YYYY"),
                "Data_Inspecao": st.column_config.DateColumn("Inspeção", format="DD/MM/YYYY"),
                "Data_IUC": st.column_config.DateColumn("IUC", format="DD/MM/YYYY"),
                "Observacoes": st.column_config.TextColumn("Notas")
            }
        )
        
        if st.button("💾 Guardar Alterações na Tabela"):
            # Converte tudo para string antes de enviar para o Sheets
            df_para_gravar = df_editado.astype(str).replace("None", "").replace("nan", "")
            if guardar_tudo_validades(df_para_gravar):
                st.success("✅ Tabela atualizada com sucesso!")
                st.rerun()
            else:
                st.error("Erro ao guardar no Google Sheets.")
