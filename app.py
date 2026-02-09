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
    
    tab1, tab2 = st.tabs(["➕ Adicionar", "📊 Resumo"])
    
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
                    if sucesso: 
                        st.success("✅ Fatura registada com sucesso!")
                else:
                    st.warning("Preenche Valor e Nº Fatura")

    # ABA 2: RESUMO
    with tab2:
        df = carregar_dados()
        if not df.empty:
            if 'Valor' in df.columns:
                df['Valor'] = pd.to_numeric(df['Valor'].astype(str).str.replace('€','').str.replace(',','.'), errors='coerce').fillna(0)
            
            # --- MÉTRICAS GERAIS ---
            c1, c2 = st.columns(2)
            c1.metric("Total Gasto (Global)", f"{df['Valor'].sum():.2f} €")
            c2.metric("Nº Faturas (Global)", len(df))
            
            st.divider()

            # --- SECÇÃO DE ELIMINAR (Separada para segurança) ---
            with st.expander("🗑️ Eliminar Fatura (Menu de Gestão)"):
                col_del1, col_del2 = st.columns(2)
                
                # Lista de matrículas para o filtro de eliminação
                lista_mat_del = ["Todas"] + list(df["Matricula"].unique())
                filtro_mat_del = col_del1.selectbox("Filtrar Viatura (Eliminar):", lista_mat_del)
                filtro_doc_del = col_del2.text_input("Pesquisar Doc (Eliminar):")

                df_del = df.copy()
                df_del['Index_Original'] = df_del.index

                if filtro_mat_del != "Todas":
                    df_del = df_del[df_del["Matricula"] == filtro_mat_del]
                if filtro_doc_del:
                    df_del = df_del[df_del["Num_Fatura"].astype(str).str.contains(filtro_doc_del, case=False)]

                if not df_del.empty:
                    opcoes_del = []
                    for index, row in df_del.iterrows():
                        idx_real = row['Index_Original']
                        texto = f"Linha {idx_real} | {row.get('Data_Fatura','?')} | {row.get('Matricula','?')} | {row.get('Valor','0')}€ | Doc: {row.get('Num_Fatura','?')}"
                        opcoes_del.append(texto)
                    
                    escolha_del = st.selectbox("Selecione para APAGAR:", options=opcoes_del[::-1])
                    
                    if st.button("❌ Confirmar Eliminação"):
                        try:
                            index_to_delete = int(escolha_del.split(" |")[0].replace("Linha ", ""))
                            if eliminar_registo(index_to_delete):
                                st.success("Registo eliminado.")
                                st.rerun()
                        except:
                            st.error("Erro ao eliminar.")
                else:
                    st.info("Nada encontrado para eliminar.")
            
            st.divider()
            
            # --- GRÁFICOS GERAIS ---
            st.subheader("💰 Gastos por Viatura")
            st.bar_chart(df.groupby("Matricula")["Valor"].sum(), color="#002060")
            
            st.write("---")
            
            # --- FILTROS AVANÇADOS (PESQUISA NA TABELA) ---
            st.subheader("🔍 Filtros de Pesquisa Detalhada")
            
            with st.expander("Abrir Filtros de Pesquisa", expanded=True):
                col_f1, col_f2, col_f3 = st.columns(3)
                
                # 1. Filtro Multisseleção de Matrículas
                todas_matriculas = sorted(df["Matricula"].unique())
                filtro_matriculas = col_f1.multiselect("Filtrar Matrículas (várias):", todas_matriculas)
                
                # 2. Filtro Multisseleção de Categorias
                todas_categorias = sorted(df["Categoria"].unique())
                filtro_categorias = col_f2.multiselect("Filtrar Categorias (várias):", todas_categorias)
                
                # 3. Filtro Texto Fatura
                filtro_fatura = col_f3.text_input("Pesquisar Nº Fatura:")
            
            # --- LÓGICA DE FILTRAGEM ---
            df_filtrado = df.copy()
            
            if filtro_matriculas:
                df_filtrado = df_filtrado[df_filtrado["Matricula"].isin(filtro_matriculas)]
                
            if filtro_categorias:
                df_filtrado = df_filtrado[df_filtrado["Categoria"].isin(filtro_categorias)]
                
            if filtro_fatura:
                df_filtrado = df_filtrado[df_filtrado["Num_Fatura"].astype(str).str.contains(filtro_fatura, case=False)]
            
            # Mostrar totais da pesquisa
            if not df_filtrado.empty and (filtro_matriculas or filtro_categorias or filtro_fatura):
                st.info(f"🔎 Resultados da Pesquisa: **{len(df_filtrado)}** faturas encontradas | Total: **{df_filtrado['Valor'].sum():.2f} €**")

            # --- TABELA FINAL ---
            st.subheader("📋 Detalhe das Faturas")
            st.dataframe(df_filtrado, use_container_width=True)
