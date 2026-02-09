import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
from datetime import datetime

# --- CONFIGURAÇÃO VISUAL ---
st.set_page_config(page_title="Qerqueijo Frota", page_icon="🚛", layout="wide")

# CSS (Visual Profissional)
st.markdown("""
    <style>
    .stApp { background-color: white; }
    [data-testid="stSidebar"] { background-color: #F0F2F6; }
    h1, h2, h3 { color: #002060; }
    .stButton>button { background-color: #002060; color: white; border: none; }
    .stButton>button:hover { background-color: #001540; color: white; }
    div.stImage > img { display: block; margin-left: auto; margin-right: auto; }
    </style>
    """, unsafe_allow_html=True)

NOME_FOLHA_GOOGLE = "dados_frota"

# --- LIGAÇÃO GOOGLE SHEETS ---
def conectar_gsheets():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    try:
        if "service_account" in st.secrets:
            creds_dict = st.secrets["service_account"]
            # Filtro para limpar chaves "sujas"
            if "gcp_json" in creds_dict:
                try:
                    creds_json = json.loads(creds_dict["gcp_json"], strict=False)
                except:
                    creds_json = json.loads(creds_dict["gcp_json"])
            else:
                creds_json = creds_dict
        else:
            st.error("❌ Erro: Falta a chave nos Segredos!")
            return None
        
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
        client = gspread.authorize(creds)
        return client.open(NOME_FOLHA_GOOGLE).sheet1
    except Exception as e:
        st.error(f"❌ Erro de Ligação: {e}")
        return None

def carregar_dados():
    sheet = conectar_gsheets()
    if sheet:
        try:
            df = pd.DataFrame(sheet.get_all_records())
            # Se a folha estiver vazia, cria colunas padrão
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
        except Exception as e:
            st.error(f"❌ Erro ao gravar: {e}")
            return False
    return False

# --- FUNÇÃO NOVA: ELIMINAR ---
def eliminar_registo(indice):
    sheet = conectar_gsheets()
    if sheet:
        try:
            # +2 porque: linha 1 é cabeçalho + gspread começa no 1
            sheet.delete_rows(indice + 2)
            return True
        except Exception as e:
            st.error(f"❌ Erro ao eliminar: {e}")
            return False
    return False

# --- FUNÇÃO LOGO ---
def mostrar_logo():
    try:
        st.image("logo.png", use_container_width=True)
    except:
        try:
            st.image(".streamlit/logo.png", use_container_width=True)
        except:
            st.header("QERQUEIJO 🧀")

# --- INTERFACE ---
if 'logado' not in st.session_state: st.session_state['logado'] = False

if not st.session_state['logado']:
    col1, col2, col3 = st.columns([2, 2, 2])
    with col2:
        st.write(""); st.write("")
        mostrar_logo()
        st.info("Gestão de Frota Cloud")
        senha = st.text_input("Senha", type="password")
        if st.button("Entrar", type="primary", use_container_width=True):
            if senha == "queijo123":
                st.session_state['logado'] = True
                st.rerun()
            else:
                st.error("Senha errada!")
else:
    with st.sidebar:
        mostrar_logo()
        st.write("---")
        if st.button("Sair"): 
            st.session_state['logado'] = False
            st.rerun()

    st.title("🚛 Gestão de Frota")
    
    tab1, tab2 = st.tabs(["➕ Adicionar", "📊 Resumo & Eliminar"])
    
    # ABA 1: ADICIONAR
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
                else:
                    st.warning("Preenche Valor e Nº Fatura")

    # ABA 2: RESUMO E ELIMINAR
    with tab2:
        df = carregar_dados()
        if not df.empty:
            # Tratamento de dados
            if 'Valor' in df.columns:
                df['Valor'] = pd.to_numeric(df['Valor'].astype(str).str.replace('€','').str.replace(',','.'), errors='coerce').fillna(0)
            
            # --- MÉTRICAS ---
            c1, c2 = st.columns(2)
            c1.metric("Total Gasto", f"{df['Valor'].sum():.2f} €")
            c2.metric("Nº Faturas", len(df))
            
            st.divider()
            
            # --- ÁREA DE ELIMINAR (NOVIDADE!) ---
            with st.expander("🗑️ Eliminar uma Fatura (Cuidado!)"):
                st.warning("Atenção: Ao clicar em eliminar, a linha desaparece para sempre do Google Sheets.")
                
                # Criar lista para escolher (Index | Viatura | Valor | Fatura)
                # Invertemos a lista [::-1] para as mais recentes aparecerem primeiro
                opcoes = []
                for i, row in df.iterrows():
                    opcoes.append(f"Linha {i} | {row.get('Data_Fatura','?')} | {row.get('Matricula','?')} | {row.get('Valor','0')}€ | Doc: {row.get('Num_Fatura','?')}")
                
                # Dropdown para selecionar (Mostra as mais recentes primeiro)
                escolha = st.selectbox("Escolhe a fatura a apagar:", options=opcoes[::-1])
                
                if st.button("❌ Eliminar Fatura Selecionada"):
                    # Extrair o número da linha (o primeiro número da string)
                    try:
                        index_to_delete = int(escolha.split(" |")[0].replace("Linha ", ""))
                        if eliminar_registo(index_to_delete):
                            st.success("Fatura eliminada com sucesso! Atualizando...")
                            st.rerun()
                    except:
                        st.error("Erro ao identificar a linha.")

            st.divider()
            
            # --- GRÁFICOS E TABELA ---
            st.subheader("💰 Gastos por Viatura")
            st.bar_chart(df.groupby("Matricula")["Valor"].sum(), color="#002060")
            
            st.subheader("📋 Detalhe das Faturas")
            st.dataframe(df, use_container_width=True)
