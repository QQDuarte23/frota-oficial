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
    div[data-testid="metric-container"] {
        background-color: #F0F2F6; padding: 10px; border-radius: 5px;
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
        try: wb.sheet1.append_row(dados); return True
        except: return False
    return False

def eliminar_registo(indice):
    wb = conectar_gsheets()
    if wb:
        try: wb.sheet1.delete_rows(indice + 2); return True
        except: return False
    return False

# --- FUNÇÕES DE DADOS (VALIDADES) ---
def carregar_validades():
    wb = conectar_gsheets()
    if wb:
        try:
            sheet = wb.worksheet("Validades")
            data = sheet.get_all_records()
            if not data: return pd.DataFrame(columns=["Matricula", "Data_Seguro", "Data_Inspecao", "Data_IUC", "Observacoes"])
            return pd.DataFrame(data)
        except: return pd.DataFrame()
    return pd.DataFrame()

# Função nova para buscar dados de UMA viatura específica
def get_validade_viatura(matricula):
    df = carregar_validades()
    if df.empty: return None, None, None, ""
    
    # Filtra pela matrícula
    viatura = df[df["Matricula"] == matricula]
    if viatura.empty: return None, None, None, ""
    
    # Pega na primeira linha encontrada
    row = viatura.iloc[0]
    
    # Converte strings de data para objetos de data (ou None se vazio)
    def parse_date(d_str):
        if not d_str or str(d_str).strip() == "": return None
        try: return datetime.strptime(str(d_str), "%Y-%m-%d").date()
        except: return None

    return parse_date(row.get("Data_Seguro")), parse_date(row.get("Data_Inspecao")), parse_date(row.get("Data_IUC")), row.get("Observacoes", "")

def guardar_validade_nova(dados):
    wb = conectar_gsheets()
    if wb:
        try:
            sheet = wb.worksheet("Validades")
            matricula_alvo = dados[0]
            try: cell = sheet.find(matricula_alvo)
            except: cell = None

            if cell:
                # Atualiza a linha existente
                linha = cell.row
                sheet.update(f"B{linha}:E{linha}", [[dados[1], dados[2], dados[3], dados[4]]])
                return True
            else:
                # Adiciona nova linha (segurança)
                sheet.append_row(dados)
                return True
        except: return False
    return False

# --- FUNÇÃO DO LOGO ---
def mostrar_logo():
    caminhos = [".streamlit/logo.png", "logo.png", ".streamlit/Logo.png", "Logo.png", "logo.jpg"]
    encontrou = False
    for c in caminhos:
        try: st.image(c, use_container_width=True); encontrou = True; break
        except: continue
    if not encontrou: st.header("QERQUEIJO 🧀")

# --- ALERTAS ---
def verificar_alertas(df_val):
    if df_val.empty: return
    hoje = datetime.now().date()
    for _, row in df_val.iterrows():
        mat = row['Matricula']
        verificacoes = {"Seguro": row.get('Data_Seguro'), "Inspeção": row.get('Data_Inspecao'), "IUC": row.get('Data_IUC')}
        for tipo, data_str in verificacoes.items():
            if data_str and str(data_str).strip() != "":
                try:
                    data_val = datetime.strptime(str(data_str), "%Y-%m-%d").date()
                    dias_restantes = (data_val - hoje).days
                    if dias_restantes < 0: st.error(f"🚨 **URGENTE ({mat}):** {tipo} expirou dia {data_val.strftime('%d/%m')}!")
                    elif dias_restantes <= 7: st.error(f"⏰ **CRÍTICO ({mat}):** {tipo} vence em {dias_restantes} dias!")
                    elif dias_restantes <= 30: st.warning(f"⚠️ **Atenção ({mat}):** {tipo} vence em {dias_restantes} dias.")
                except: continue

# --- APP PRINCIPAL ---
if 'logado' not in st.session_state: st.session_state['logado'] = False

if not st.session_state['logado']:
    col1, col2, col3 = st.columns([2, 2, 2])
    with col2:
        st.write(""); st.write("")
        mostrar_logo()
        senha = st.text_input("Senha", type="password")
        if st.button("Entrar", type="primary", use_container_width=True):
            if senha == "queijo123":
                st.session_state['logado'] = True; st.rerun()
            else: st.error("Senha errada!")
else:
    with st.sidebar:
        mostrar_logo()
        st.write("---")
        if st.button("Sair"): st.session_state['logado'] = False; st.rerun()

    df_alertas = carregar_validades()
    if not df_alertas.empty: verificar_alertas(df_alertas)

    st.title("🚛 Gestão de Frota")
    tab1, tab2, tab3 = st.tabs(["➕ Adicionar Despesa", "📊 Resumo Financeiro", "📅 Validades & Alertas"])
    
    # ABA 1: ADICIONAR
    with tab1:
        with st.form("nova_despesa", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                mat = st.selectbox("Viatura", LISTA_VIATURAS)
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
                        st.success("✅ Fatura registada!"); st.rerun()
                else: st.warning("Preenche Valor e Nº Fatura")

    # ABA 2: RESUMO
    with tab2:
        df = carregar_dados()
        if not df.empty:
            def corrigir_valor(v):
                try:
                    v_str = str(v).replace('€', '').replace(',', '.'); valor = float(v_str)
                    return valor / 100 if valor > 2000 else valor
                except: return 0.0
            df['Valor'] = df['Valor'].apply(corrigir_valor)
            df['Valor_Visual'] = df['Valor'].apply(lambda x: f"{x:,.2f} €".replace(",", "X").replace(".", ",").replace("X", "."))
            df['Data_Fatura'] = pd.to_datetime(df['Data_Fatura'])

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
            with st.expander("🔍 Configurar Filtros", expanded=True):
                c_f1, c_f2, c_f3 = st.columns(3)
                f_mats = c_f1.multiselect("Viaturas:", sorted(df["Matricula"].unique()))
                f_cats = c_f2.multiselect("Categorias:", sorted(df["Categoria"].unique()))
                f_doc = c_f3.text_input("Nº Fatura:")
            df_f = df.copy()
            if f_mats: df_f = df_f[df_f["Matricula"].isin(f_mats)]
            if f_cats: df_f = df_f[df_f["Categoria"].isin(f_cats)]
            if f_doc: df_f = df_f[df_f["Num_Fatura"].astype(str).str.contains(f_doc, case=False)]
            if not df_f.empty:
                col_g1, col_g2 = st.columns(2)
                df_ev = df_f.groupby(df_f['Data_Fatura'].dt.to_period('M'))['Valor'].sum().reset_index()
                df_ev['Data_Fatura'] = df_ev['Data_Fatura'].astype(str)
                col_g1.plotly_chart(px.line(df_ev, x='Data_Fatura', y='Valor', title="Evolução Mensal (€)", markers=True).update_traces(line_color='#002060'), use_container_width=True)
                col_g2.plotly_chart(px.pie(df_f, values='Valor', names='Categoria', title="Distribuição por Categoria", hole=0.4), use_container_width=True)
                st.dataframe(df_f, use_container_width=True, hide_index=True, column_config={"Valor_Visual": st.column_config.TextColumn("Valor (€)"), "Data_Fatura": st.column_config.DateColumn("Data", format="DD/MM/YYYY")})
            else: st.warning("Sem dados.")

    # --- ABA 3: VALIDADES (COM EDITOR INTELIGENTE) ---
    with tab3:
        st.header("📅 Controlo de Prazos")
        
        # 1. ESCOLHE A VIATURA PRIMEIRO
        st.info("ℹ️ Escolhe uma viatura para ver e editar as datas atuais.")
        v_mat_edit = st.selectbox("🔎 Selecionar Viatura para Editar:", LISTA_VIATURAS)
        
        # 2. CARREGA OS DADOS DESSA VIATURA
        d_seg_atual, d_insp_atual, d_iuc_atual, obs_atual = get_validade_viatura(v_mat_edit)
        
        # 3. MOSTRA O FORMULÁRIO JÁ PREENCHIDO
        with st.form("form_validade"):
            st.write(f"**A editar: {v_mat_edit}**")
            c_d1, c_d2, c_d3 = st.columns(3)
            
            # Os campos vêm preenchidos com o valor atual (ou None se vazio)
            # Para APAGAR: Basta o utilizador clicar no 'x' do calendário ou apagar a data
            d_seg = c_d1.date_input("Seguro", value=d_seg_atual)
            d_insp = c_d2.date_input("Inspeção", value=d_insp_atual)
            d_iuc = c_d3.date_input("IUC", value=d_iuc_atual)
            
            v_obs = st.text_input("Observações", value=obs_atual)
            
            st.caption("💡 Dica: Para remover uma data, limpa o campo e grava.")
            
            if st.form_submit_button("💾 Gravar Alterações", type="primary", use_container_width=True):
                dados_v = [
                    v_mat_edit,
                    str(d_seg) if d_seg else "", # Se estiver vazio, grava "" (apaga)
                    str(d_insp) if d_insp else "",
                    str(d_iuc) if d_iuc else "",
                    v_obs
                ]
                if guardar_validade_nova(dados_v):
                    st.success(f"✅ Dados da {v_mat_edit} atualizados!")
                    st.rerun()
                else: st.error("Erro ao gravar.")

        st.divider()
        st.subheader("📋 Estado Geral da Frota")
        
        df_vals = carregar_validades()
        if not df_vals.empty:
            st.dataframe(
                df_vals, use_container_width=True, hide_index=True,
                column_config={
                    "Matricula": st.column_config.TextColumn("Viatura", width="small"),
                    "Data_Seguro": st.column_config.DateColumn("Seguro", format="DD/MM/YYYY"),
                    "Data_Inspecao": st.column_config.DateColumn("Inspeção", format="DD/MM/YYYY"),
                    "Data_IUC": st.column_config.DateColumn("IUC", format="DD/MM/YYYY"),
                    "Observacoes": st.column_config.TextColumn("Notas")
                }
            )
