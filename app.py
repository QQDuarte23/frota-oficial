import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
from datetime import datetime
import plotly.express as px

# --- 1. CONFIGURAÇÃO GERAL E VISUAL ---
st.set_page_config(page_title="Qerqueijo Frota", page_icon="🚛", layout="wide")

# Lista fixa das tuas 24 viaturas
LISTA_VIATURAS = [
    "06-QO-19", "59-RT-87", "19-TF-05", "28-UO-50", "17-UM-19", "83-ZL-79", 
    "83-ZL-83", "AD-66-VN", "AD-71-VN", "AL-36-FF", "AL-30-FF", "AT-79-QU", 
    "AT-87-QU", "BE-64-TJ", "BE-16-TL", "BE-35-TJ", "BL-33-LG", "BL-68-LF", 
    "BR-83-SQ", "BU-45-NF", "BX-53-AB", "BO-08-DB", "AU-56-NT", "74-LU-19"
]

# CSS "Tanque de Guerra": Limpo, sem rodapés, menu a funcionar
st.markdown("""
    <style>
    /* Esconde barra de ferramentas direita e rodapé */
    [data-testid="stToolbar"] {visibility: hidden !important;}
    footer {visibility: hidden;}
    .stAppDeployButton {display: none;}
    
    /* Cabeçalho transparente para o menu funcionar */
    header[data-testid="stHeader"] {background: transparent !important;}
    
    /* Estilo Azul Qerqueijo */
    h1, h2, h3 { color: #002060; }
    .stButton>button { background-color: #002060; color: white; border: none; width: 100%; }
    .stButton>button:hover { background-color: #001540; color: white; }
    
    /* Ajuste para o Logo */
    div.stImage > img { display: block; margin-left: auto; margin-right: auto; }
    </style>
    """, unsafe_allow_html=True)

NOME_FOLHA_GOOGLE = "dados_frota"

# --- 2. LIGAÇÃO AO GOOGLE SHEETS ---
def conectar_gsheets():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    try:
        if "service_account" in st.secrets:
            creds_dict = st.secrets["service_account"]
            if "gcp_json" in creds_dict:
                creds_json = json.loads(creds_dict["gcp_json"])
            else:
                creds_json = creds_dict
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
            client = gspread.authorize(creds)
            return client.open(NOME_FOLHA_GOOGLE)
    except: return None

# --- 3. FUNÇÕES DE DADOS ---

# Carregar Faturas (Aba 1 do Excel)
def carregar_faturas():
    wb = conectar_gsheets()
    if wb:
        try:
            df = pd.DataFrame(wb.sheet1.get_all_records())
            if df.empty: return pd.DataFrame(columns=["Data_Fatura", "Matricula", "Categoria", "Valor", "KM_Atuais", "Num_Fatura", "Descricao"])
            return df
        except: return pd.DataFrame()
    return pd.DataFrame()

# Carregar Validades (Aba 'Validades' do Excel)
def carregar_validades():
    wb = conectar_gsheets()
    if wb:
        try:
            sheet = wb.worksheet("Validades")
            df_ex = pd.DataFrame(sheet.get_all_records())
            
            # Garante que as 24 matrículas aparecem, mesmo que o Excel esteja vazio
            df_base = pd.DataFrame({"Matricula": LISTA_VIATURAS})
            
            if not df_ex.empty:
                # Junta o que está no Excel com a lista fixa
                df_final = pd.merge(df_base, df_ex, on="Matricula", how="left").fillna("")
            else:
                # Se vazio, cria colunas em branco
                for c in ["Data_Seguro", "Data_Inspecao", "Data_IUC", "Observacoes"]:
                    df_base[c] = ""
                df_final = df_base
            return df_final
        except: return pd.DataFrame() # Retorna vazio se der erro
    return pd.DataFrame()

# Gravar Nova Fatura
def guardar_fatura(dados):
    wb = conectar_gsheets()
    if wb:
        try:
            wb.sheet1.append_row(dados)
            return True
        except: return False
    return False

# Atualizar TODA a tabela de Validades (Para quando editas na tabela)
def salvar_tabela_validades(df_novo):
    wb = conectar_gsheets()
    if wb:
        try:
            sheet = wb.worksheet("Validades")
            sheet.clear() # Limpa tudo
            # Escreve de novo (Cabeçalhos + Dados)
            dados_lista = [df_novo.columns.values.tolist()] + df_novo.astype(str).values.tolist()
            sheet.update(dados_lista)
            return True
        except: return False
    return False

# Função Inteligente do Logo (Procura em todo o lado)
def mostrar_logo():
    caminhos = [".streamlit/logo.png", "logo.png", ".streamlit/Logo.png", "Logo.png"]
    encontrou = False
    for c in caminhos:
        try:
            st.image(c, use_container_width=True)
            encontrou = True
            break
        except: continue
    if not encontrou: st.header("QERQUEIJO 🧀")

# --- 4. LÓGICA DE ALERTAS (TOPO DA PÁGINA) ---
def mostrar_alertas(df):
    if df.empty: return
    hoje = datetime.now().date()
    
    for _, row in df.iterrows():
        mat = row['Matricula']
        # Verifica Seguro, Inspeção e IUC
        for tipo, col in [("Seguro", "Data_Seguro"), ("Inspeção", "Data_Inspecao"), ("IUC", "Data_IUC")]:
            data_str = str(row.get(col)).strip()
            
            # Se tiver data válida (ignora vazios ou "nan")
            if data_str and data_str not in ["", "nan", "None"]:
                try:
                    data_obj = datetime.strptime(data_str, "%Y-%m-%d").date()
                    dias = (data_obj - hoje).days
                    
                    if dias < 0:
                        st.error(f"🚨 **EXPIRADO:** {tipo} da **{mat}** venceu dia {data_obj.strftime('%d/%m')}!")
                    elif dias <= 15:
                        st.error(f"⏰ **URGENTE:** {tipo} da **{mat}** vence em {dias} dias ({data_obj.strftime('%d/%m')})")
                    elif dias <= 30:
                        st.warning(f"⚠️ **Atenção:** {tipo} da **{mat}** vence em {dias} dias.")
                except: continue

# --- 5. INTERFACE PRINCIPAL ---

# Login
if 'logado' not in st.session_state: st.session_state['logado'] = False

if not st.session_state['logado']:
    col1, col2, col3 = st.columns([2,2,2])
    with col2:
        st.write(""); st.write("")
        mostrar_logo()
        p = st.text_input("Senha", type="password")
        if st.button("Entrar"):
            if p == "queijo123": st.session_state['logado'] = True; st.rerun()
            else: st.error("Senha Errada")
else:
    # Menu Lateral
    with st.sidebar:
        mostrar_logo()
        st.write("---")
        if st.button("Sair"): st.session_state['logado'] = False; st.rerun()

    # 1. Carrega Validades para mostrar Alertas
    df_val = carregar_validades()
    mostrar_alertas(df_val)

    st.title("🚛 Gestão de Frota")
    
    tab1, tab2, tab3 = st.tabs(["➕ Adicionar", "📊 Resumo", "📅 Validades"])

    # --- ABA 1: ADICIONAR DESPESA ---
    with tab1:
        with st.form("form_fatura", clear_on_submit=True):
            c1, c2 = st.columns(2)
            mat = c1.selectbox("Viatura", LISTA_VIATURAS)
            cat = c1.selectbox("Categoria", ["Combustível", "Pneus", "Oficina", "Frio", "Lavagem", "Portagens"])
            dt = c2.date_input("Data", datetime.now())
            nf = c2.text_input("Nº Fatura")
            
            k1, k2, k3 = st.columns(3)
            km = k1.number_input("KMs", step=1)
            val = k2.number_input("Valor (€)", min_value=0.0, step=0.01)
            desc = k3.text_input("Descrição")
            
            if st.form_submit_button("💾 Gravar Fatura"):
                if val > 0 and nf:
                    # Grava no sheets
                    dados = [str(dt), mat, cat, val, km, nf, desc]
                    if guardar_fatura(dados):
                        st.success("✅ Fatura Gravada!")
                        st.rerun()
                else: st.warning("Preenche o Valor e Nº Fatura")

    # --- ABA 2: RESUMO E TABELA ---
    with tab2:
        df = carregar_faturas()
        if not df.empty:
            # Correção inteligente dos valores (Vírgulas e /100)
            def limpar_valor(v):
                try:
                    v = str(v).replace('€','').replace(',','.')
                    vf = float(v)
                    if vf > 2000: return vf / 100 # Corrige 8652 para 86.52
                    return vf
                except: return 0.0
            
            df['Valor'] = df['Valor'].apply(limpar_valor)
            # Coluna Visual (Texto com vírgula)
            df['Valor_Visual'] = df['Valor'].apply(lambda x: f"{x:,.2f} €".replace(",", "X").replace(".", ",").replace("X", "."))
            df['Data_Fatura'] = pd.to_datetime(df['Data_Fatura'])
            
            # Gráficos e Filtros
            with st.expander("🔍 Filtros"):
                filtro_mat = st.multiselect("Viatura", df['Matricula'].unique())
            
            df_show = df.copy()
            if filtro_mat: df_show = df_show[df_show['Matricula'].isin(filtro_mat)]
            
            if not df_show.empty:
                colg1, colg2 = st.columns(2)
                # Gráfico Evolução
                df_ev = df_show.groupby(df_show['Data_Fatura'].dt.to_period('M'))['Valor'].sum().reset_index()
                df_ev['Data_Fatura'] = df_ev['Data_Fatura'].astype(str)
                fig = px.line(df_ev, x='Data_Fatura', y='Valor', title="Evolução Mensal")
                colg1.plotly_chart(fig, use_container_width=True)
                # Tabela Bonita
                st.dataframe(df_show, use_container_width=True, hide_index=True,
                             column_order=["Data_Fatura", "Matricula", "Categoria", "Valor_Visual", "KM_Atuais", "Num_Fatura"],
                             column_config={"Valor_Visual": "Valor (€)", "Data_Fatura": st.column_config.DateColumn("Data", format="DD/MM/YYYY")})
            else: st.warning("Sem dados.")

    # --- ABA 3: VALIDADES (EDITÁVEL) ---
    with tab3:
        st.subheader("📅 Gestão de Prazos")
        st.info("Para apagar uma data: Seleciona a célula e carrega em **Delete** no teclado.")
        
        # Carrega dados
        df_edit = carregar_validades()
        
        # Tabela Editável
        df_alterado = st.data_editor(
            df_edit,
            use_container_width=True,
            hide_index=True,
            num_rows="fixed", # Impede adicionar linhas novas, só editamos as 24 viaturas
            column_config={
                "Matricula": st.column_config.TextColumn("Viatura", disabled=True), # Bloqueia matrícula
                "Data_Seguro": st.column_config.DateColumn("Seguro", format="DD/MM/YYYY"),
                "Data_Inspecao": st.column_config.DateColumn("Inspeção", format="DD/MM/YYYY"),
                "Data_IUC": st.column_config.DateColumn("IUC", format="DD/MM/YYYY"),
                "Observacoes": st.column_config.TextColumn("Notas")
            }
        )
        
        if st.button("💾 Guardar Alterações na Tabela"):
            if salvar_tabela_validades(df_alterado):
                st.success("✅ Tabela atualizada com sucesso!")
                st.rerun()
            else:
                st.error("Erro ao gravar. Verifica se a aba 'Validades' existe no Sheets.")
