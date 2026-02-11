import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
from datetime import datetime
import plotly.express as px

# --- 1. CONFIGURAÇÃO GERAL ---
st.set_page_config(page_title="Qerqueijo Frota", page_icon="🚛", layout="wide")

# Lista fixa das viaturas
LISTA_VIATURAS = [
    "06-QO-19", "59-RT-87", "19-TF-05", "28-UO-50", "17-UM-19", "83-ZL-79", 
    "83-ZL-83", "AD-66-VN", "AD-71-VN", "AL-36-FF", "AL-30-FF", "AT-79-QU", 
    "AT-87-QU", "BE-64-TJ", "BE-16-TL", "BE-35-TJ", "BL-33-LG", "BL-68-LF", 
    "BR-83-SQ", "BU-45-NF", "BX-53-AB", "BO-08-DB", "AU-56-NT", "74-LU-19"
]

# CSS Limpo e Profissional
st.markdown("""
    <style>
    /* Esconde barra de topo e rodapés */
    [data-testid="stToolbar"] {visibility: hidden !important;}
    footer {visibility: hidden;}
    .stAppDeployButton {display: none;}
    
    /* Cores da Marca */
    h1, h2, h3 { color: #002060; }
    .stButton>button { background-color: #002060; color: white; border: none; width: 100%; }
    .stButton>button:hover { background-color: #001540; color: white; }
    
    /* Centralizar Logo */
    div.stImage > img { display: block; margin-left: auto; margin-right: auto; }
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
                creds_json = json.loads(creds_dict["gcp_json"])
            else:
                creds_json = creds_dict
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
            return gspread.authorize(creds).open(NOME_FOLHA_GOOGLE)
    except: return None

# --- 3. FUNÇÕES DE DADOS (FATURAS) ---
def carregar_faturas():
    wb = conectar_gsheets()
    if wb:
        try:
            df = pd.DataFrame(wb.sheet1.get_all_records())
            if df.empty: return pd.DataFrame(columns=["Data_Fatura", "Matricula", "Categoria", "Valor", "KM_Atuais", "Num_Fatura", "Descricao"])
            return df
        except: return pd.DataFrame()
    return pd.DataFrame()

def guardar_fatura(dados):
    wb = conectar_gsheets()
    if wb:
        try:
            wb.sheet1.append_row(dados)
            return True
        except: return False
    return False

def eliminar_fatura(indice):
    wb = conectar_gsheets()
    if wb:
        try:
            wb.sheet1.delete_rows(indice + 2)
            return True
        except: return False
    return False

# --- 4. FUNÇÕES DE DADOS (VALIDADES) ---
def carregar_validades():
    wb = conectar_gsheets()
    if wb:
        try:
            sheet = wb.worksheet("Validades")
            df = pd.DataFrame(sheet.get_all_records())
            # Garante que mostra todas as matrículas
            df_base = pd.DataFrame({"Matricula": LISTA_VIATURAS})
            if not df.empty:
                return pd.merge(df_base, df, on="Matricula", how="left").fillna("")
            else:
                for col in ["Data_Seguro", "Data_Inspecao", "Data_IUC", "Observacoes"]:
                    df_base[col] = ""
                return df_base
        except: return pd.DataFrame()
    return pd.DataFrame()

# Função nova: Busca os dados atuais de uma matrícula para preencher o formulário
def obter_dados_atuais(matricula):
    df = carregar_validades()
    if df.empty: return None, None, None, ""
    
    linha = df[df["Matricula"] == matricula]
    if linha.empty: return None, None, None, ""
    
    r = linha.iloc[0]
    
    # Helper para converter texto em data
    def to_date(x):
        try: return datetime.strptime(str(x), "%Y-%m-%d").date()
        except: return None

    return to_date(r["Data_Seguro"]), to_date(r["Data_Inspecao"]), to_date(r["Data_IUC"]), r["Observacoes"]

def guardar_validade(dados):
    # dados = [Matricula, Seg, Insp, IUC, Obs]
    wb = conectar_gsheets()
    if wb:
        try:
            sheet = wb.worksheet("Validades")
            try: cell = sheet.find(dados[0]) # Procura a matrícula
            except: cell = None

            if cell:
                # Atualiza a linha existente
                linha = cell.row
                sheet.update(f"B{linha}:E{linha}", [[dados[1], dados[2], dados[3], dados[4]]])
            else:
                # Adiciona nova se não existir
                sheet.append_row(dados)
            return True
        except: return False
    return False

# --- 5. LOGO INTELIGENTE ---
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

# --- 6. ALERTAS ---
def verificar_alertas(df):
    if df.empty: return
    hoje = datetime.now().date()
    for _, row in df.iterrows():
        mat = row['Matricula']
        for tipo, col in [("Seguro", "Data_Seguro"), ("Inspeção", "Data_Inspecao"), ("IUC", "Data_IUC")]:
            d_str = str(row.get(col)).strip()
            if d_str and d_str not in ["", "nan", "None"]:
                try:
                    d_val = datetime.strptime(d_str, "%Y-%m-%d").date()
                    dias = (d_val - hoje).days
                    if dias < 0: st.error(f"🚨 **EXPIRADO ({mat}):** {tipo} em {d_val.strftime('%d/%m')}")
                    elif dias <= 15: st.error(f"⏰ **CRÍTICO ({mat}):** {tipo} vence em {dias} dias")
                    elif dias <= 30: st.warning(f"⚠️ **AVISO ({mat}):** {tipo} vence em {dias} dias")
                except: continue

# --- 7. APP PRINCIPAL ---
if 'logado' not in st.session_state: st.session_state['logado'] = False

if not st.session_state['logado']:
    col1, col2, col3 = st.columns([2, 2, 2])
    with col2:
        st.write(""); mostrar_logo()
        senha = st.text_input("Senha", type="password")
        if st.button("Entrar"):
            if senha == "queijo123": st.session_state['logado'] = True; st.rerun()
            else: st.error("Senha errada!")
else:
    with st.sidebar:
        mostrar_logo(); st.write("---")
        if st.button("Sair"): st.session_state['logado'] = False; st.rerun()

    # Mostra alertas no topo
    df_alertas = carregar_validades()
    verificar_alertas(df_alertas)

    st.title("🚛 Gestão de Frota")
    tab1, tab2, tab3 = st.tabs(["➕ Adicionar", "📊 Resumo", "📅 Validades"])

    # ABA 1: NOVA FATURA
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
                    if guardar_fatura([str(dt), mat, cat, val, km, nf, desc]):
                        st.success("✅ Fatura Gravada!"); st.rerun()
                else: st.warning("Preenche Valor e Nº Fatura")

    # ABA 2: RESUMO
    with tab2:
        df = carregar_faturas()
        if not df.empty:
            # Correção valores
            def limpar_val(v):
                try:
                    v = float(str(v).replace('€','').replace(',','.'))
                    return v/100 if v > 2000 else v
                except: return 0.0
            df['Valor'] = df['Valor'].apply(limpar_val)
            df['Valor_V'] = df['Valor'].apply(lambda x: f"{x:,.2f} €".replace(",", "X").replace(".", ",").replace("X", "."))
            df['Data_Fatura'] = pd.to_datetime(df['Data_Fatura'])

            # Eliminar
            with st.expander("🗑️ Eliminar Fatura"):
                c_del1, c_del2 = st.columns(2)
                mat_del = c_del1.selectbox("Viatura Eliminar", ["Todas"] + list(df["Matricula"].unique()))
                nf_del = c_del2.text_input("Nº Fatura Eliminar")
                df_del = df.copy(); df_del['Idx'] = df_del.index
                if mat_del != "Todas": df_del = df_del[df_del["Matricula"] == mat_del]
                if nf_del: df_del = df_del[df_del["Num_Fatura"].astype(str).str.contains(nf_del, case=False)]
                if not df_del.empty:
                    escolha = st.selectbox("Selecionar Fatura:", [f"Linha {r.Idx} | {r.Matricula} | {r.Valor_V}" for _, r in df_del.iterrows()])
                    if st.button("❌ Apagar"):
                        if eliminar_fatura(int(escolha.split(" |")[0].replace("Linha ", ""))): st.rerun()

            st.divider()
            
            # Filtros e Gráficos
            c_f1, c_f2 = st.columns(2)
            f_mat = c_f1.multiselect("Filtrar Viatura", df["Matricula"].unique())
            df_show = df[df["Matricula"].isin(f_mat)] if f_mat else df

            if not df_show.empty:
                colg1, colg2 = st.columns(2)
                df_ev = df_show.groupby(df_show['Data_Fatura'].dt.to_period('M'))['Valor'].sum().reset_index()
                df_ev['Data_Fatura'] = df_ev['Data_Fatura'].astype(str)
                colg1.plotly_chart(px.line(df_ev, x='Data_Fatura', y='Valor', title="Evolução Mensal"), use_container_width=True)
                colg2.plotly_chart(px.pie(df_show, values='Valor', names='Categoria', title="Por Categoria", hole=0.4), use_container_width=True)
                
                st.dataframe(df_show, use_container_width=True, hide_index=True,
                             column_order=["Data_Fatura", "Matricula", "Categoria", "Valor_V", "KM_Atuais", "Num_Fatura"],
                             column_config={"Valor_V": "Valor (€)", "Data_Fatura": st.column_config.DateColumn("Data", format="DD/MM/YYYY")})
            else: st.warning("Sem dados.")

    # ABA 3: VALIDADES (O teu favorito, com preenchimento automático)
    with tab3:
        st.header("📅 Controlo de Prazos")
        
        # Seleção da Viatura (Fora do form para atualizar os dados)
        v_selecionada = st.selectbox("🔎 Escolher Viatura para Editar:", LISTA_VIATURAS)
        
        # Vai buscar os dados atuais para não editares "às cegas"
        d_seg_at, d_insp_at, d_iuc_at, obs_at = obter_dados_atuais(v_selecionada)

        with st.form("form_validade"):
            st.write(f"**A editar: {v_selecionada}**")
            c_d1, c_d2, c_d3 = st.columns(3)
            
            # Preenche com o valor atual. Se quiseres apagar, limpa a caixa.
            d_seg = c_d1.date_input("Seguro", value=d_seg_at)
            d_insp = c_d2.date_input("Inspeção", value=d_insp_at)
            d_iuc = c_d3.date_input("IUC", value=d_iuc_at)
            obs = st.text_input("Observações", value=obs_at)
            
            if st.form_submit_button("💾 Atualizar Datas"):
                # Se a data vier vazia ou None, grava string vazia (apaga no Excel)
                dados_v = [v_selecionada, str(d_seg) if d_seg else "", str(d_insp) if d_insp else "", str(d_iuc) if d_iuc else "", obs]
                if guardar_validade(dados_v):
                    st.success(f"✅ {v_selecionada} atualizada!"); st.rerun()
                else: st.error("Erro ao gravar.")

        st.divider()
        st.subheader("📋 Estado da Frota")
        st.dataframe(df_alertas, use_container_width=True, hide_index=True,
                     column_config={
                         "Data_Seguro": st.column_config.DateColumn("Seguro", format="DD/MM/YYYY"),
                         "Data_Inspecao": st.column_config.DateColumn("Inspeção", format="DD/MM/YYYY"),
                         "Data_IUC": st.column_config.DateColumn("IUC", format="DD/MM/YYYY")
                     })
