import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
from datetime import datetime
import plotly.express as px

# --- CONFIGURAÇÃO VISUAL E REMOÇÃO DE ELEMENTOS DA PLATAFORMA ---
st.set_page_config(page_title="Qerqueijo Frota", page_icon="🚛", layout="wide")

# CSS Mágico para esconder: Header, Footer e Botão Manage App
st.markdown("""
    <style>
    /* Esconder o Header (ícones do canto superior) */
    header {visibility: hidden;}
    
    /* Esconder o Footer (Made with Streamlit) */
    footer {visibility: hidden;}

    /* Esconder o botão 'Manage App' e outros elementos de ancoragem */
    .stAppDeployButton {display:none;}
    #MainMenu {visibility: hidden;}
    
    /* Ajustes de Design Profissional */
    .stApp { background-color: white; }
    [data-testid="stSidebar"] { background-color: #F0F2F6; }
    h1, h2, h3 { color: #002060; }
    .stButton>button { background-color: #002060; color: white; border: none; }
    .stButton>button:hover { background-color: #001540; color: white; }
    div.stImage > img { display: block; margin-left: auto; margin-right: auto; }
    </style>
    """, unsafe_allow_html=True)

NOME_FOLHA_GOOGLE = "dados_frota"

def conectar_gsheets():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    try:
        if "service_account" in st.secrets:
            creds_dict = st.secrets["service_account"]
            if "gcp_json" in creds_dict:
                try:
                    creds_json = json.loads(creds_dict["gcp_json"], strict=False)
                except:
                    creds_json = json.loads(creds_dict["gcp_json"])
            else:
                creds_json = creds_dict
        else:
            return None
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
        client = gspread.authorize(creds)
        # Tenta abrir a folha. Se mudaste o nome para Folha1, ajusta aqui se der erro.
        # Por defeito, tenta abrir a primeira aba disponível.
        return client.open(NOME_FOLHA_GOOGLE).sheet1
