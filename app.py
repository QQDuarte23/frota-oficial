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
    /* Esconde barra de topo e rodapé */
    [data-testid="stToolbar"] {visibility: hidden !important;}
    footer {visibility: hidden;}
    .stAppDeployButton {display: none;}
    
    /* Cores da Marca */
    .stApp { background-color: white; }
    [data-testid="stSidebar"] { background-color: #F0F2F6; }
    h1, h2, h3 { color: #002060; }
    .stButton>button { background-color: #002060; color: white; border: none; }
    .stButton>button:hover { background-color: #001540; color: white; }
    div.stImage > img { display: block; margin-left: auto; margin-right: auto; }
    
    /* Métrica de Alertas */
    div[data-testid="metric-container"] {
        background-color: #F0F2F6;
        padding: 10px;
        border-radius: 5px;
    }
    </style>
    """, unsafe_allow_html=True)

NOME_FOLHA_GOOGLE = "dados_frota"

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

# --- FUNÇÕES DE DADOS (FATURAS) ---
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
        try:
            wb.sheet1.append_row(dados)
            return True
        except: return False
    return False

def eliminar_registo(indice):
    wb = conectar_gsheets()
    if wb:
        try:
            wb.sheet1.delete_rows(indice + 2)
            return True
        except: return False
    return False

# --- FUNÇÕES DE DADOS (VALIDADES) ---
def carregar_validades():
    wb = conectar_gsheets()
    if wb:
        try:
            sheet = wb.worksheet("Validades")
            data = sheet.get_all_records()
            # Se a folha estiver vazia, cria estrutura base
            df_base = pd.DataFrame({"Matricula": LISTA_VIATURAS})
            if not data: 
                for c in ["Data_Seguro", "Data_Inspecao", "Data_IUC", "Observacoes"]: df_base[c] = ""
                return df_base
            
            df_google = pd.DataFrame(data)
            # Junta com a lista mestra para garantir que aparecem as 24 viaturas
            return pd.merge(df_base, df_google, on="Matricula", how="left").fillna("")
        except: return pd.DataFrame()
    return pd.DataFrame()

def guardar_validade_nova(dados):
    # dados = [Matricula, Seg, Insp, IUC, Obs]
    wb = conectar_gsheets()
    if wb:
        try:
            sheet = wb.worksheet("Validades")
            matricula_alvo = dados[0]
            
            # 1. Procura a linha da matrícula
            try: cell = sheet.find(matricula_alvo)
            except: cell = None

            if cell:
                # 2. Atualiza a linha existente
                linha = cell.row
                sheet.update(f"B{linha}:E{linha}", [[dados[1], dados[2], dados[3], dados[4]]])
                return True
            else:
                # 3. Segurança: se não encontrar, adiciona ao fundo
                sheet.append_row(dados)
                return True
        except: return False
    return False

# --- FUNÇÃO DO LOGO ---
def mostrar_logo():
    caminhos = [".streamlit/logo.png", "logo.png", ".streamlit/Logo.png", "Logo.png", "logo.jpg"]
    encontrou = False
    for c in caminhos:
        try:
            st.image(c, use_container_width=True)
            encontrou = True
            break
        except: continue
    if not encontrou: st.header("QERQUEIJO 🧀")

# --- LÓGICA DE ALERTAS ---
def verificar_alertas(df_val):
    if df_val.empty: return
    hoje = datetime.now().date()
    
    for _, row in df_val.iterrows():
        mat = row['Matricula']
        verificacoes = {
            "Seguro": row.get('Data_Seguro'),
            "Inspeção": row.get('Data_Inspecao'),
            "IUC": row.get('Data_IUC')
        }
        
        for tipo, data_str in verificacoes.items():
            if data_str and str(data_str).strip() not in ["", "None", "nan"]:
                try:
                    data_val = datetime.strptime(str(data_str), "%Y-%m-%d").date()
                    dias_restantes = (data_val - hoje).days
