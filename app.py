import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
from datetime import datetime

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="Qerqueijo Frota", page_icon="🚛", layout="wide")
NOME_FOLHA_GOOGLE = "dados_frota"

# --- LIGAÇÃO GOOGLE SHEETS ---
def conectar_gsheets():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    try:
        if "service_account" in st.secrets:
            creds_dict = st.secrets["service_account"]
            # Ajuste para garantir compatibilidade com diferentes formatos de segredo
            if "gcp_json" in creds_dict:
                creds_json = json.loads(creds_dict["gcp_json"])
            else:
                creds_json = creds_dict
        else:
            st.error("❌ Falta a chave secreta [service_account]!")
            return None

        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
        client = gspread.authorize(creds)
        return client.open(NOME_FOLHA_GOOGLE).sheet1
    except Exception as e:
        st.sidebar.error(f"⚠️ Erro Google: {e}")
        return None

def carregar_dados():
    sheet = conectar_gsheets()
    if sheet:
        try:
            data = sheet.get_all_records()
            df = pd.DataFrame(data)
            if df.empty: return pd.DataFrame(columns=["Data_Registo", "Data_Fatura", "Matricula", "Categoria", "Valor", "KM_Atuais", "Num_Fatura", "Descricao"])
            return df
        except: return pd.DataFrame()
    return pd.DataFrame()

def guardar_registo(dados):
    sheet = conectar_gsheets()
    if sheet:
        try:
            sheet.append_row(dados)
            return True
        except: return False
    return False

# --- INTERFACE ---
if 'logado' not in st.session_state: st.session_state['logado'] = False

if not st.session_state['logado']:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.header("QERQUEIJO 🧀")
        st.info("Gestão de Frota Cloud")
        senha = st.text_input("Senha", type="password")
        if st.button("Entrar", type="primary", use_container_width=True):
            if senha == "queijo123": st.session_state['logado'] = True
            else: st.error("Senha errada!")
else:
    # BARRA LATERAL COM AJUDA
    with st.sidebar:
        st.header("QERQUEIJO")
        st.write("---")
        try:
            # Mostrar email para facilitar partilha
            if "service_account" in st.secrets:
                if "gcp_json" in st.secrets["service_account"]:
                    c = json.loads(st.secrets["service_account"]["gcp_json"])
                else:
                    c = st.secrets["service_account"]
                st.info("📧 **Copia este email para o Google Sheets:**")
                st.code(c.get("client_email", "Erro"), language="text")
        except: pass
        
        st.write("---")
        if st.button("Sair"): st.session_state['logado'] = False; st.rerun()

    st.title("🚛 Gestão de Frota")
    
    tab1, tab2 = st.tabs(["➕ Adicionar", "📊 Resumo"])
    
    with tab1:
        with st.form("nova_despesa", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                mat = st.selectbox("Viatura", ["06-QO-19", "59-RT-87", "19-TF-05", "28-UO-50", "17-UM-19", "83-ZL-79", "83-ZL-83", "AD-66-VN", "AD-71-VN", "AL-36-FF", "AL-30-FF", "AT-79-QU", "AT-87-QU", "BE-64-TJ", "BE-16-TL", "BE-35-TJ", "BL-33-LG", "BL-68-LF", "BR-83-SQ", "BU-45-NF", "BX-53-AB", "BO-08-DB", "AU-56-NT", "74-LU-19"])
                cat = st.selectbox("Categoria", ["Combustível", "Pneus", "Oficina", "Frio", "Lavagem", "Portagens"])
            with c2:
                dt = st.date_input("Data Fatura", datetime.now())
                nf = st.text_input("Nº Fatura")
            
            k1, k2, k3 = st.columns(3)
            km = k1.number_input("KMs", step=1)
            val = k2.number_input("Valor (€)", min_value=0.0, step=0.01)
            desc = k3.text_input("Descrição")
            
            if st.form_submit_button("💾 Gravar", type="primary", use_container_width=True):
                if val > 0 and nf:
                    sucesso = guardar_registo([str(datetime.now()), str(dt), mat, cat, val, km, nf, desc])
                    if sucesso: st.success("✅ Guardado!"); st.balloons()
                    else: st.error("Erro ao gravar. Verifica a ligação.")
                else:
                    st.warning("Preenche Valor e Nº Fatura")

    with tab2:
        df = carregar_dados()
        if not df.empty:
            if 'Valor' in df.columns:
                df['Valor'] = pd.to_numeric(df['Valor'].astype(str).str.replace('€','').str.replace(',','.'), errors='coerce').fillna(0)
            c1, c2 = st.columns(2)
            c1.metric("Total", f"{df['Valor'].sum():.2f} €")
            c2.metric("Faturas", len(df))
            st.dataframe(df, use_container_width=True)
