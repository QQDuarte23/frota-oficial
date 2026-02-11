import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
from datetime import datetime
import plotly.express as px

# --- CONFIGURAÇÃO VISUAL ---
st.set_page_config(page_title="Qerqueijo Frota", page_icon="🚛", layout="wide")

# CSS: Mantém o visual limpo, esconde rodapé e botão 'Manage app'
st.markdown("""
    <style>
    footer {visibility: hidden;}
    .stAppDeployButton {display:none;}
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
        return client.open(NOME_FOLHA_GOOGLE).sheet1
    except: return None

def carregar_dados():
    sheet = conectar_gsheets()
    if sheet:
        try:
            df = pd.DataFrame(sheet.get_all_records())
            if df.empty: return pd.DataFrame(columns=["Data_Fatura", "Matricula", "Categoria", "Valor", "KM_Atuais", "Num_Fatura", "Descricao"])
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

def eliminar_registo(indice):
    sheet = conectar_gsheets()
    if sheet:
        try:
            sheet.delete_rows(indice + 2)
            return True
        except: return False
    return False

# --- FUNÇÃO DO LOGO (AGORA PROCURA DENTRO DA PASTA .streamlit) ---
def mostrar_logo():
    # Lista alargada de locais onde o logo pode estar
    caminhos_possiveis = [
        ".streamlit/logo.png",      # O mais provável (baseado na tua imagem)
        "logo.png",                 # Na raiz
        ".streamlit/Logo.png",      # Pasta com maiúscula
        "Logo.png",                 # Raiz com maiúscula
        ".streamlit/logo.jpg",      # Pasta jpg
        "logo.jpg"                  # Raiz jpg
    ]
    
    encontrou = False
    for caminho in caminhos_possiveis:
        try:
            st.image(caminho, use_container_width=True)
            encontrou = True
            break 
        except:
            continue
            
    if not encontrou:
        st.header("QERQUEIJO 🧀")

# --- INTERFACE DE LOGIN ---
if 'logado' not in st.session_state: st.session_state['logado'] = False

if not st.session_state['logado']:
    col1, col2, col3 = st.columns([2, 2, 2])
    with col2:
        st.write(""); st.write("")
        mostrar_logo()
        senha = st.text_input("Senha", type="password")
        if st.button("Entrar", type="primary", use_container_width=True):
            if senha == "queijo123":
                st.session_state['logado'] = True
                st.rerun()
            else:
                st.error("Senha errada!")
else:
    # --- BARRA LATERAL (MENU) ---
    with st.sidebar:
        mostrar_logo()
        st.write("---")
        if st.button("Sair"): 
            st.session_state['logado'] = False
            st.rerun()

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
                    if guardar_registo([str(dt), mat, cat, val, km, nf, desc]):
                        st.success("✅ Fatura registada!")
                        st.rerun()
                else: st.warning("Preenche Valor e Nº Fatura")

    with tab2:
        df = carregar_dados()
        if not df.empty:
            
            # --- CORREÇÃO INTELIGENTE DE VALORES ---
            def corrigir_valor(v):
                try:
                    v_str = str(v).replace('€', '').replace(',', '.')
                    valor_float = float(v_str)
                    if valor_float > 2000:
                        return valor_float / 100
                    return valor_float
                except:
                    return 0.0

            df['Valor'] = df['Valor'].apply(corrigir_valor)
            df['Valor_Visual'] = df['Valor'].apply(lambda x: f"{x:,.2f} €".replace(",", "X").replace(".", ",").replace("X", "."))
            df['Data_Fatura'] = pd.to_datetime(df['Data_Fatura'])

            # --- ÁREA DE ELIMINAR ---
            with st.expander("🗑️ Eliminar Fatura"):
                col_d1, col_d2 = st.columns(2)
                l_mat_del = ["Todas"] + list(df["Matricula"].unique())
                f_mat_del = col_d1.selectbox("Viatura (Eliminar):", l_mat_del)
                f_doc_del = col_d2.text_input("Nº Fatura (Eliminar):")
                df_del = df.copy(); df_del['Idx'] = df_del.index
                if f_mat_del != "Todas": df_del = df_del[df_del["Matricula"] == f_mat_del]
                if f_doc_del: df_del = df_del[df_del["Num_Fatura"].astype(str).str.contains(f_doc_del, case=False)]
                if not df_del.empty:
                    ops = [f"Linha {r.Idx} | {r.Data_Fatura.date()} | {r.Matricula} | {r.Valor:.2f}€" for _, r in df_del.iterrows()]
                    escolha = st.selectbox("Selecionar:", ops[::-1])
                    if st.button("❌ Confirmar"):
                        idx = int(escolha.split(" |")[0].replace("Linha ", ""))
                        if eliminar_registo(idx): st.rerun()

            st.divider()
            
            # --- FILTROS ---
            st.subheader("🔍 Filtros de Análise")
            with st.expander("Configurar Filtros", expanded=True):
                c_f1, c_f2, c_f3 = st.columns(3)
                f_mats = c_f1.multiselect("Viaturas:", sorted(df["Matricula"].unique()))
                f_cats = c_f2.multiselect("Categorias:", sorted(df["Categoria"].unique()))
                f_doc = c_f3.text_input("Nº Fatura:")

            df_f = df.copy()
            if f_mats: df_f = df_f[df_f["Matricula"].isin(f_mats)]
            if f_cats: df_f = df_f[df_f["Categoria"].isin(f_cats)]
            if f_doc: df_f = df_f[df_f["Num_Fatura"].astype(str).str.contains(f_doc, case=False)]

            # --- GRÁFICOS ---
            if not df_f.empty:
                col_g1, col_g2 = st.columns(2)
                df_ev = df_f.groupby(df_f['Data_Fatura'].dt.to_period('M'))['Valor'].sum().reset_index()
                df_ev['Data_Fatura'] = df_ev['Data_Fatura'].astype(str)
                fig_line = px.line(df_ev, x='Data_Fatura', y='Valor', title="Evolução Mensal (€)", markers=True)
                fig_line.update_traces(line_color='#002060')
                col_g1.plotly_chart(fig_line, use_container_width=True)
                
                fig_pie = px.pie(df_f, values='Valor', names='Categoria', title="Distribuição por Categoria", hole=0.4)
                col_g2.plotly_chart(fig_pie, use_container_width=True)

                st.subheader("📋 Detalhe das Faturas")
                st.dataframe(
                    df_f,
                    use_container_width=True,
                    hide_index=True,
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
            else:
                st.warning("Sem dados para os filtros selecionados.")
