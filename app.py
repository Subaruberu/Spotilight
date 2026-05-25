import streamlit as st
from groq import Groq
import json
import math
import re as _re
import hashlib as _hs
import urllib.parse as _up
import base64 as _b64
from io import BytesIO as _Bio
from datetime import datetime, date as _date
import pandas as pd
import requests

# ── Banco de dados SQLite ─────────────────────────────────────────────────────
try:
    import database as db
    DB_DISPONIVEL = True
except Exception:
    DB_DISPONIVEL = False

# ── AWS Services ──────────────────────────────────────────────────────────────
try:
    import aws_services as aws
    AWS_DISPONIVEL = aws.AWS_DISPONIVEL
except Exception:
    AWS_DISPONIVEL = False

# ── Configuração da página ──────────────────────────────────────────────────
st.set_page_config(
    page_title="SpotlightIA – Agente para Eventos Privados",
    page_icon="🎉",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Sistema de Login Multi-tenant ────────────────────────────────────────────
PLANOS = {
    "free": {
        "nome": "Free",
        "preco": "R$ 0/mês",
        "cor": "#6B7280",
        "max_eventos": 2,
        "features": ["2 eventos ativos", "Chat com IA", "RSVP básico", "Checklist"],
    },
    "essencial": {
        "nome": "Essencial",
        "preco": "R$ 97/mês",
        "cor": "#2D6A4F",
        "max_eventos": 10,
        "features": ["10 eventos ativos", "Tudo do Free", "Dashboard", "Convite digital", "E-mail automático"],
    },
    "profissional": {
        "nome": "Profissional",
        "preco": "R$ 197/mês",
        "cor": "#1A56DB",
        "max_eventos": 20,
        "features": ["20 eventos ativos", "Tudo do Essencial", "Orçamento", "Contrato", "Mapa interativo", "Foto & Vídeo"],
    },
    "enterprise": {
        "nome": "Enterprise",
        "preco": "R$ 497/mês",
        "cor": "#534AB7",
        "max_eventos": 999,
        "features": ["Eventos ilimitados", "Tudo do Profissional", "Multi-usuário", "Relatório PDF", "Suporte prioritário", "White-label"],
    },
}

def tela_login():
    st.markdown("""
<div class="login-container">
  <div class="login-logo">🎉</div>
  <div class="login-title">SpotlightIA</div>
  <div class="login-subtitle">Plataforma Inteligente de Eventos Privados</div>
</div>
""", unsafe_allow_html=True)

    # Métricas de impacto antes do login
    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    col_m1.metric("📅 Módulos", "26")
    col_m2.metric("🤖 Provedores IA", "3")
    col_m3.metric("🌐 Idiomas", "3")
    col_m4.metric("🗄️ Tabelas SQL", "9")

    st.divider()

    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        aba_login, aba_cadastro, aba_planos = st.tabs(["🔑 Login", "📝 Cadastrar", "💎 Planos"])

        with aba_login:
            email_in = st.text_input("📧 E-mail", placeholder="seu@email.com", key="login_email")
            senha_in = st.text_input("🔒 Senha", type="password", key="login_senha")
            if st.button("🚀 Entrar", use_container_width=True, key="btn_login"):
                tenant_found = None
                for tid, tdata in st.session_state.clientes_saas.items():
                    if tdata["email"] == email_in and tdata["senha"] == senha_in:
                        tenant_found = tid
                        break
                if tenant_found:
                    st.session_state.usuario_logado = email_in
                    st.session_state.tenant = tenant_found
                    st.session_state.plano = st.session_state.clientes_saas[tenant_found]["plano"]
                    # Carrega dados do banco SQLite se disponível
                    if DB_DISPONIVEL:
                        row = db.tenant_login(email_in, senha_in)
                        if row:
                            st.session_state.tenant = row["id"]
                            st.session_state.plano  = row["plano"]
                            st.session_state.eventos_cadastrados = db.eventos_listar(row["id"])
                            st.session_state.lista_rsvp = db.rsvps_listar(row["id"])
                            st.session_state.crm_clientes = db.crm_listar(row["id"])
                            st.session_state.kanban = db.kanban_listar(row["id"])
                            st.session_state.leads_landing = db.leads_listar(row["id"])
                            msgs_db = db.chat_carregar(row["id"])
                            if msgs_db:
                                st.session_state.messages = msgs_db
                    st.success(f"Bem-vindo, {st.session_state.clientes_saas[tenant_found]['nome']}!")
                    st.rerun()
                else:
                    st.error("E-mail ou senha incorretos.")
            st.caption("Demo: admin@spotlight.com / admin123")

        with aba_cadastro:
            novo_nome  = st.text_input("Nome da empresa", key="cad_nome")
            novo_email = st.text_input("E-mail", key="cad_email")
            novo_senha = st.text_input("Senha", type="password", key="cad_senha")
            novo_plano = st.selectbox("Plano", ["free","essencial","profissional","enterprise"],
                                      format_func=lambda x: f"{PLANOS[x]['nome']} — {PLANOS[x]['preco']}", key="cad_plano")
            if st.button("Criar conta", use_container_width=True, key="btn_cadastro"):
                if novo_nome and novo_email and novo_senha:
                    tid = novo_email.split("@")[0].replace(".","_")
                    st.session_state.clientes_saas[tid] = {
                        "nome": novo_nome, "email": novo_email, "senha": novo_senha,
                        "plano": novo_plano, "cor": "#534AB7", "logo": "🎉",
                        "eventos": [], "vencimento": "2026-12-31",
                        "max_eventos": PLANOS[novo_plano]["max_eventos"],
                    }
                    st.session_state.usuario_logado = novo_email
                    st.session_state.tenant = tid
                    st.session_state.plano = novo_plano
                    st.success("Conta criada! Entrando...")
                    st.rerun()
                else:
                    st.warning("Preencha todos os campos.")

        with aba_planos:
            st.markdown("##### Escolha o plano ideal para sua empresa")
            for pid, pdata in PLANOS.items():
                is_pop = pid == "profissional"
                with st.expander(f"{'⭐ ' if is_pop else ''}{pdata['nome']} — {pdata['preco']}", expanded=is_pop):
                    col_pl1, col_pl2 = st.columns([2,1])
                    with col_pl1:
                        for feat in pdata["features"]:
                            st.markdown(f"✅ {feat}")
                    with col_pl2:
                        st.metric("Eventos", str(pdata["max_eventos"]) if pdata["max_eventos"] < 999 else "∞")
                    if is_pop:
                        st.info("🏆 Plano mais escolhido por empresas de eventos")

# ── Estilos customizados ────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;500;600;700;800&family=DM+Sans:ital,wght@0,300;0,400;0,500;0,600;1,300&display=swap');

/* ── Variáveis globais ── */
:root {
    --primary:       #6C63FF;
    --primary-dark:  #4A42D4;
    --primary-light: #EEF0FF;
    --accent:        #FF6B6B;
    --accent2:       #FFD93D;
    --success:       #6BCB77;
    --surface:       #1A1A2E;
    --surface2:      #16213E;
    --surface3:      #0F3460;
    --border:        rgba(108,99,255,0.18);
    --text:          #F0F0FF;
    --text-muted:    #9090B0;
    --radius:        14px;
    --radius-sm:     8px;
    --shadow:        0 8px 32px rgba(108,99,255,0.18);
    --shadow-lg:     0 20px 60px rgba(0,0,0,0.4);
    --font-display:  'Syne', sans-serif;
    --font-body:     'DM Sans', sans-serif;
}

/* ── Base ── */
html, body, [class*="css"] {
    font-family: var(--font-body) !important;
    background: var(--surface) !important;
    color: var(--text) !important;
}

/* ── Scrollbar personalizada ── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: var(--surface2); }
::-webkit-scrollbar-thumb { background: var(--primary); border-radius: 10px; }
::-webkit-scrollbar-thumb:hover { background: var(--primary-dark); }

/* ── Header principal ── */
h1, h2, h3 {
    font-family: var(--font-display) !important;
    letter-spacing: -0.02em !important;
}
h1 { font-size: 2rem !important; font-weight: 800 !important; }
h2 { font-size: 1.4rem !important; font-weight: 700 !important; }
h3 { font-size: 1.1rem !important; font-weight: 600 !important; }

/* ── Sidebar ── */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, var(--surface2) 0%, var(--surface) 100%) !important;
    border-right: 1px solid var(--border) !important;
    box-shadow: 4px 0 24px rgba(0,0,0,0.3) !important;
}
section[data-testid="stSidebar"] > div { padding: 1.5rem 1rem !important; }

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    background: var(--surface2) !important;
    border-radius: var(--radius) !important;
    padding: 4px !important;
    gap: 2px !important;
    border: 1px solid var(--border) !important;
    overflow-x: auto !important;
}
.stTabs [data-baseweb="tab"] {
    background: transparent !important;
    border-radius: var(--radius-sm) !important;
    color: var(--text-muted) !important;
    font-family: var(--font-body) !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    padding: 6px 14px !important;
    transition: all 0.2s ease !important;
    white-space: nowrap !important;
}
.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, var(--primary), var(--primary-dark)) !important;
    color: white !important;
    font-weight: 600 !important;
    box-shadow: 0 4px 12px rgba(108,99,255,0.4) !important;
}
.stTabs [data-baseweb="tab-panel"] {
    background: transparent !important;
    padding-top: 1.5rem !important;
}

/* ── Botões ── */
.stButton > button {
    background: linear-gradient(135deg, var(--primary), var(--primary-dark)) !important;
    color: white !important;
    border: none !important;
    border-radius: var(--radius-sm) !important;
    font-family: var(--font-body) !important;
    font-weight: 600 !important;
    font-size: 13px !important;
    padding: 0.5rem 1.2rem !important;
    transition: all 0.2s ease !important;
    box-shadow: 0 4px 12px rgba(108,99,255,0.3) !important;
    letter-spacing: 0.01em !important;
}
.stButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 20px rgba(108,99,255,0.5) !important;
    filter: brightness(1.1) !important;
}
.stButton > button:active { transform: translateY(0) !important; }

/* ── Inputs ── */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea,
.stNumberInput > div > div > input,
.stSelectbox > div > div,
.stMultiSelect > div > div {
    background: var(--surface2) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius-sm) !important;
    color: var(--text) !important;
    font-family: var(--font-body) !important;
    font-size: 13px !important;
    transition: border-color 0.2s ease !important;
}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: var(--primary) !important;
    box-shadow: 0 0 0 3px rgba(108,99,255,0.15) !important;
}

/* ── Selectbox ── */
.stSelectbox [data-baseweb="select"] > div {
    background: var(--surface2) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius-sm) !important;
}

/* ── Métricas ── */
[data-testid="stMetric"] {
    background: linear-gradient(135deg, var(--surface2), var(--surface3)) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius) !important;
    padding: 1rem 1.2rem !important;
    box-shadow: var(--shadow) !important;
    transition: transform 0.2s ease, box-shadow 0.2s ease !important;
}
[data-testid="stMetric"]:hover {
    transform: translateY(-3px) !important;
    box-shadow: var(--shadow-lg) !important;
}
[data-testid="stMetricLabel"] {
    font-family: var(--font-body) !important;
    font-size: 12px !important;
    font-weight: 500 !important;
    color: var(--text-muted) !important;
    text-transform: uppercase !important;
    letter-spacing: 0.06em !important;
}
[data-testid="stMetricValue"] {
    font-family: var(--font-display) !important;
    font-size: 1.8rem !important;
    font-weight: 700 !important;
    color: var(--text) !important;
    background: linear-gradient(135deg, var(--primary), #a78bfa) !important;
    -webkit-background-clip: text !important;
    -webkit-text-fill-color: transparent !important;
}

/* ── Chat ── */
.stChatMessage {
    background: var(--surface2) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius) !important;
    padding: 1rem !important;
    margin-bottom: 0.5rem !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.2) !important;
    animation: fadeSlideIn 0.3s ease forwards !important;
}
.stChatMessage[data-testid="user-message"] {
    background: linear-gradient(135deg, rgba(108,99,255,0.15), rgba(74,66,212,0.1)) !important;
    border-color: rgba(108,99,255,0.3) !important;
}
.stChatInputContainer {
    background: var(--surface2) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius) !important;
    padding: 0.5rem !important;
}
.stChatInputContainer textarea {
    background: transparent !important;
    color: var(--text) !important;
    font-family: var(--font-body) !important;
}

/* ── Expander ── */
.streamlit-expanderHeader {
    background: var(--surface2) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius-sm) !important;
    color: var(--text) !important;
    font-family: var(--font-body) !important;
    font-weight: 500 !important;
    transition: all 0.2s ease !important;
}
.streamlit-expanderHeader:hover {
    border-color: var(--primary) !important;
    background: rgba(108,99,255,0.08) !important;
}
.streamlit-expanderContent {
    background: rgba(108,99,255,0.04) !important;
    border: 1px solid var(--border) !important;
    border-top: none !important;
    border-radius: 0 0 var(--radius-sm) var(--radius-sm) !important;
}

/* ── Dataframe ── */
[data-testid="stDataFrame"] {
    border: 1px solid var(--border) !important;
    border-radius: var(--radius) !important;
    overflow: hidden !important;
    box-shadow: var(--shadow) !important;
}
[data-testid="stDataFrame"] table { background: var(--surface2) !important; }
[data-testid="stDataFrame"] th {
    background: linear-gradient(135deg, var(--surface3), var(--primary-dark)) !important;
    color: white !important;
    font-family: var(--font-display) !important;
    font-weight: 600 !important;
    font-size: 12px !important;
    letter-spacing: 0.05em !important;
    text-transform: uppercase !important;
    padding: 10px 12px !important;
}
[data-testid="stDataFrame"] td {
    color: var(--text) !important;
    font-size: 13px !important;
    padding: 8px 12px !important;
    border-bottom: 1px solid var(--border) !important;
}
[data-testid="stDataFrame"] tr:hover td {
    background: rgba(108,99,255,0.08) !important;
}

/* ── Progress bar ── */
.stProgress > div > div > div > div {
    background: linear-gradient(90deg, var(--primary), #a78bfa, var(--accent)) !important;
    border-radius: 10px !important;
    box-shadow: 0 0 10px rgba(108,99,255,0.5) !important;
}
.stProgress > div > div {
    background: var(--surface2) !important;
    border-radius: 10px !important;
    border: 1px solid var(--border) !important;
}

/* ── Slider ── */
.stSlider > div > div > div > div {
    background: linear-gradient(90deg, var(--primary), #a78bfa) !important;
}

/* ── Info / Warning / Success / Error boxes ── */
.stInfo {
    background: rgba(108,99,255,0.12) !important;
    border: 1px solid rgba(108,99,255,0.3) !important;
    border-radius: var(--radius-sm) !important;
    color: var(--text) !important;
}
.stSuccess {
    background: rgba(107,203,119,0.12) !important;
    border: 1px solid rgba(107,203,119,0.3) !important;
    border-radius: var(--radius-sm) !important;
}
.stWarning {
    background: rgba(255,217,61,0.10) !important;
    border: 1px solid rgba(255,217,61,0.3) !important;
    border-radius: var(--radius-sm) !important;
}
.stError {
    background: rgba(255,107,107,0.12) !important;
    border: 1px solid rgba(255,107,107,0.3) !important;
    border-radius: var(--radius-sm) !important;
}

/* ── Divider ── */
hr {
    border: none !important;
    height: 1px !important;
    background: linear-gradient(90deg, transparent, var(--primary), transparent) !important;
    margin: 1.5rem 0 !important;
    opacity: 0.4 !important;
}

/* ── Checkbox ── */
.stCheckbox > label {
    color: var(--text) !important;
    font-family: var(--font-body) !important;
    font-size: 13px !important;
}

/* ── Labels ── */
.stTextInput label, .stSelectbox label,
.stTextArea label, .stNumberInput label,
.stSlider label, .stDateInput label,
.stMultiSelect label, .stFileUploader label {
    color: var(--text-muted) !important;
    font-family: var(--font-body) !important;
    font-size: 12px !important;
    font-weight: 500 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.06em !important;
    margin-bottom: 4px !important;
}

/* ── File uploader ── */
[data-testid="stFileUploader"] {
    background: var(--surface2) !important;
    border: 2px dashed var(--border) !important;
    border-radius: var(--radius) !important;
    padding: 1.5rem !important;
    transition: border-color 0.2s ease !important;
}
[data-testid="stFileUploader"]:hover {
    border-color: var(--primary) !important;
    background: rgba(108,99,255,0.06) !important;
}

/* ── Bar chart ── */
[data-testid="stVegaLiteChart"] {
    background: var(--surface2) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius) !important;
    padding: 1rem !important;
    box-shadow: var(--shadow) !important;
}

/* ── Download button ── */
.stDownloadButton > button {
    background: linear-gradient(135deg, var(--surface3), var(--primary-dark)) !important;
    border: 1px solid var(--border) !important;
    color: white !important;
}

/* ── Form submit button ── */
.stFormSubmitButton > button {
    background: linear-gradient(135deg, var(--primary), var(--primary-dark)) !important;
    width: 100% !important;
    padding: 0.7rem !important;
    font-size: 14px !important;
    letter-spacing: 0.04em !important;
}

/* ── Badges customizados ── */
.event-badge {
    display: inline-block;
    padding: 3px 12px;
    border-radius: 20px;
    font-size: 11px;
    font-weight: 600;
    font-family: var(--font-body);
    letter-spacing: 0.04em;
    text-transform: uppercase;
}
.badge-confirmed { background: rgba(107,203,119,0.15); color: #6BCB77; border: 1px solid rgba(107,203,119,0.3); }
.badge-pending   { background: rgba(255,217,61,0.12); color: #FFD93D; border: 1px solid rgba(255,217,61,0.3); }
.badge-vip       { background: rgba(108,99,255,0.15); color: #a78bfa; border: 1px solid rgba(108,99,255,0.3); }

/* ── Animações ── */
@keyframes fadeSlideIn {
    from { opacity: 0; transform: translateY(8px); }
    to   { opacity: 1; transform: translateY(0); }
}
@keyframes pulse {
    0%, 100% { box-shadow: 0 0 0 0 rgba(108,99,255,0.4); }
    50%       { box-shadow: 0 0 0 8px rgba(108,99,255,0); }
}
@keyframes gradientShift {
    0%   { background-position: 0% 50%; }
    50%  { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
}

/* ── Título principal animado ── */
.spotlight-title {
    font-family: var(--font-display);
    font-size: 1.8rem;
    font-weight: 800;
    background: linear-gradient(135deg, #6C63FF, #a78bfa, #FF6B6B, #FFD93D);
    background-size: 300% 300%;
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    animation: gradientShift 4s ease infinite;
    letter-spacing: -0.02em;
}

/* ── Card de evento ── */
.event-card {
    background: linear-gradient(135deg, var(--surface2), var(--surface3));
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 1rem 1.2rem;
    margin-bottom: 0.75rem;
    box-shadow: var(--shadow);
    transition: all 0.25s ease;
}
.event-card:hover {
    transform: translateY(-3px);
    box-shadow: var(--shadow-lg);
    border-color: rgba(108,99,255,0.4);
}

/* ── Sidebar título ── */
.sidebar-logo {
    font-family: var(--font-display);
    font-size: 1.3rem;
    font-weight: 800;
    background: linear-gradient(135deg, #6C63FF, #a78bfa);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}

/* ── Main content heading ── */
.main-heading {
    font-family: var(--font-display);
    font-size: 1.6rem;
    font-weight: 700;
    color: var(--text);
    margin-bottom: 0.25rem;
}
.main-subheading {
    font-size: 13px;
    color: var(--text-muted);
    font-weight: 400;
    margin-bottom: 1.5rem;
}

/* ── Tela de login ── */
.login-container {
    max-width: 440px;
    margin: 40px auto;
    text-align: center;
}
.login-logo {
    font-size: 60px;
    filter: drop-shadow(0 0 20px rgba(108,99,255,0.5));
    animation: pulse 2.5s infinite;
    display: inline-block;
}
.login-title {
    font-family: var(--font-display);
    font-size: 2.2rem;
    font-weight: 800;
    background: linear-gradient(135deg, #6C63FF, #a78bfa);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin: 12px 0 4px;
}
.login-subtitle {
    color: var(--text-muted);
    font-size: 14px;
    margin-bottom: 2rem;
}

/* ── Radio buttons ── */
.stRadio > div { gap: 8px !important; }
.stRadio > div > label {
    background: var(--surface2) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius-sm) !important;
    padding: 8px 16px !important;
    color: var(--text) !important;
    transition: all 0.2s ease !important;
    cursor: pointer !important;
}
.stRadio > div > label:hover {
    border-color: var(--primary) !important;
    background: rgba(108,99,255,0.08) !important;
}

/* ── Code blocks ── */
code {
    background: var(--surface3) !important;
    border: 1px solid var(--border) !important;
    border-radius: 6px !important;
    color: #a78bfa !important;
    font-size: 12px !important;
    padding: 2px 6px !important;
}
pre { background: var(--surface2) !important; border: 1px solid var(--border) !important; border-radius: var(--radius) !important; }

/* ── Color picker ── */
.stColorPicker > div { border-radius: var(--radius-sm) !important; }

/* ── Spinner ── */
.stSpinner > div { border-top-color: var(--primary) !important; }

/* ── Caption / small text ── */
.stCaption { color: var(--text-muted) !important; font-size: 12px !important; }

/* ── Link buttons ── */
.stLinkButton > a {
    background: linear-gradient(135deg, var(--success), #4CAF50) !important;
    color: white !important;
    border-radius: var(--radius-sm) !important;
    font-weight: 600 !important;
    text-decoration: none !important;
}

/* ── Animação entrada das seções ── */
.main .block-container > div > div {
    animation: fadeSlideIn 0.4s ease forwards;
}

/* ── Tabs scrollbar ── */
.stTabs [data-baseweb="tab-list"]::-webkit-scrollbar { height: 3px; }
.stTabs [data-baseweb="tab-list"]::-webkit-scrollbar-thumb { background: var(--primary); }
</style>
""", unsafe_allow_html=True)

# ── System prompt do agente ─────────────────────────────────────────────────
SYSTEM_PROMPT = """Você é SpotlightIA, assistente de inteligência artificial da Spotlight Eventos — especializada em eventos privados de alto padrão.

Seu papel é atuar em três frentes de forma integrada:

## 1. ATENDIMENTO AO CLIENTE
- Recepcione convidados com cordialidade e profissionalismo
- Confirme presenças (RSVP): colete nome completo, número de acompanhantes e restrições alimentares
- Esclareça dúvidas sobre logística: local, horário, dress code, estacionamento e programação
- Encaminhe solicitações especiais para a equipe responsável quando necessário

## 2. PLANEJAMENTO E ORGANIZAÇÃO
- Auxilie na criação de cronogramas, checklists e briefings detalhados
- Sugira fornecedores e etapas por tipo de evento
- Monitore itens pendentes e sinalize prazos críticos
- Organize informações de orçamento e contratações
- Oriente sobre montagem de aparelhagem de som, iluminação e estrutura de palco
- Auxilie no planejamento técnico: posicionamento de caixas de som, iluminação cênica, telões, geradores e cabeamento
- Oriente sobre dimensionamento e posicionamento de geradores elétricos
- Auxilie no planejamento de camarim: estrutura, rider técnico e logística de acesso
- Oriente sobre cardápios, quantidade de comida por pessoa, restrições alimentares e tipos de serviço de buffet
- Auxilie no planejamento de logística e transporte: estacionamento, valet, transfer VIP e sinalização do local
- Oriente sobre cobertura fotográfica e audiovisual: fotógrafo, cinegrafista, drone, transmissão ao vivo e edição

## 3. VENDAS E CONVITES
- Apresente os pacotes da Spotlight Eventos de forma clara e persuasiva
- Qualifique o interesse do cliente (tipo de evento, data, número de convidados, orçamento)
- Conduza o cliente pelas etapas de contratação com segurança
- Acompanhe o status de envio e confirmação de convites

## TIPOS DE EVENTOS ATENDIDOS
Casamentos · Formaturas · Festas corporativas · Aniversários · Confraternizações · Eventos VIP/exclusivos · Hackathons · Palestras e conferências

## DIRETRIZES DE COMPORTAMENTO
- Comunique-se sempre em português brasileiro formal, porém acessível
- Seja preciso, atencioso e demonstre domínio sobre eventos
- Nunca invente informações; quando não souber, informe que verificará com a equipe
- Em casos de reclamação, demonstre empatia e ofereça soluções concretas
- Respostas objetivas: vá direto ao ponto, sem rodeios desnecessários
- Sempre finalize com um próximo passo claro para o cliente

## USO DA MEMÓRIA
Você possui memória completa de todos os eventos cadastrados e RSVPs registrados (fornecidos abaixo).
- Ao mencionar um evento, cite sempre dados reais: nome, data, local e número de convidados
- Se perguntado sobre RSVPs, informe os números reais de confirmados, pendentes e recusados
- Ao identificar pendências (ex: muitos pendentes, prazo próximo), alerte proativamente
- Cruze informações entre eventos quando relevante (ex: dois eventos no mesmo dia)
- Se o usuário cadastrar um novo evento durante a conversa, incorpore-o naturalmente

Lembre-se: você representa a Spotlight Eventos. Cada interação é uma oportunidade de encantar o cliente e garantir um evento inesquecível."""

# ── Traduções da interface ──────────────────────────────────────────────────
IDIOMAS = {
    "🇧🇷 Português": "pt",
    "🇺🇸 English":   "en",
    "🇪🇸 Español":   "es",
}

TRADUCOES = {
    "pt": {
        "titulo_app":    "🎯 SpotlightIA",
        "subtitulo":     "Spotlight Eventos · Agente IA",
        "chat":          "💬 Chat",
        "eventos":       "📅 Eventos",
        "checklist":     "✅ Checklist",
        "estrutura":     "🔊 Estrutura & Técnica",
        "buffet":        "🍽️ Buffet & Gastronomia",
        "logistica":     "🚗 Logística & Transporte",
        "foto":          "📸 Foto & Vídeo",
        "orcamento":     "💰 Orçamento",
        "dashboard":     "📊 Dashboard",
        "confirmacoes":  "📧 Confirmações",
        "rsvp":          "🔗 RSVP Público",
        "convite":       "📱 Convite Digital",
        "cronograma":    "🗓️ Cronograma",
        "documentos":    "📁 Documentos",
        "widget":        "💬 Widget",
        "novo_evento":   "➕ Novo evento",
        "limpar_chat":   "🗑️ Limpar",
        "input_hint":    "Digite sua mensagem...",
        "boas_vindas":   "Olá! Sou a **SpotlightIA**, assistente inteligente da Spotlight Eventos.\n\nPosso ajudar com:\n- ✅ **RSVP e confirmação de presenças**\n- 📋 **Planejamento e checklist**\n- 📦 **Pacotes e vendas**\n- ❓ **Dúvidas logísticas**\n\nSelecione um evento na barra lateral ou me conte sobre o seu evento!",
        "sugestoes":     ["Quero confirmar minha presença no evento", "Me ajude a montar um checklist para casamento", "Quais pacotes de eventos VIP vocês oferecem?", "Como organizar um hackathon para 200 pessoas?", "Preciso planejar uma palestra corporativa"],
        "idioma_sistema": "Responda sempre em português brasileiro formal.",
    },
    "en": {
        "titulo_app":    "🎯 SpotlightIA",
        "subtitulo":     "Spotlight Events · AI Agent",
        "chat":          "💬 Chat",
        "eventos":       "📅 Events",
        "checklist":     "✅ Checklist",
        "estrutura":     "🔊 AV & Structure",
        "buffet":        "🍽️ Catering",
        "logistica":     "🚗 Logistics",
        "foto":          "📸 Photo & Video",
        "orcamento":     "💰 Budget",
        "dashboard":     "📊 Dashboard",
        "confirmacoes":  "📧 Confirmations",
        "rsvp":          "🔗 Public RSVP",
        "convite":       "📱 Digital Invite",
        "cronograma":    "🗓️ Schedule",
        "documentos":    "📁 Documents",
        "widget":        "💬 Chat Widget",
        "novo_evento":   "➕ New event",
        "limpar_chat":   "🗑️ Clear",
        "input_hint":    "Type your message...",
        "boas_vindas":   "Hello! I'm **SpotlightIA**, the intelligent assistant for Spotlight Events.\n\nI can help with:\n- ✅ **RSVP & attendance confirmation**\n- 📋 **Planning & checklists**\n- 📦 **Packages & sales**\n- ❓ **Logistics questions**\n\nSelect an event in the sidebar or tell me about your event!",
        "sugestoes":     ["I want to confirm my attendance", "Help me build a wedding checklist", "What VIP event packages do you offer?", "How to organize a hackathon for 200 people?", "I need to plan a corporate conference"],
        "idioma_sistema": "Always respond in formal English.",
    },
    "es": {
        "titulo_app":    "🎯 SpotlightIA",
        "subtitulo":     "Spotlight Eventos · Agente IA",
        "chat":          "💬 Chat",
        "eventos":       "📅 Eventos",
        "checklist":     "✅ Checklist",
        "estrutura":     "🔊 AV & Estructura",
        "buffet":        "🍽️ Catering",
        "logistica":     "🚗 Logística",
        "foto":          "📸 Foto & Video",
        "orcamento":     "💰 Presupuesto",
        "dashboard":     "📊 Dashboard",
        "confirmacoes":  "📧 Confirmaciones",
        "rsvp":          "🔗 RSVP Público",
        "convite":       "📱 Invitación Digital",
        "cronograma":    "🗓️ Cronograma",
        "documentos":    "📁 Documentos",
        "widget":        "💬 Widget",
        "novo_evento":   "➕ Nuevo evento",
        "limpar_chat":   "🗑️ Limpiar",
        "input_hint":    "Escribe tu mensaje...",
        "boas_vindas":   "¡Hola! Soy **SpotlightIA**, asistente inteligente de Spotlight Eventos.\n\nPuedo ayudarte con:\n- ✅ **RSVP y confirmación de asistencia**\n- 📋 **Planificación y checklists**\n- 📦 **Paquetes y ventas**\n- ❓ **Dudas logísticas**\n\n¡Selecciona un evento en la barra lateral o cuéntame sobre tu evento!",
        "sugestoes":     ["Quiero confirmar mi asistencia", "Ayúdame con el checklist para una boda", "¿Qué paquetes VIP ofrecen?", "¿Cómo organizar un hackathon para 200 personas?", "Necesito planificar una conferencia corporativa"],
        "idioma_sistema": "Responde siempre en español formal.",
    },
}

def T(chave):
    idioma_code = IDIOMAS.get(st.session_state.get("idioma", "🇧🇷 Português"), "pt")
    return TRADUCOES[idioma_code].get(chave, TRADUCOES["pt"].get(chave, chave))

# ── Tipos de evento e emojis ────────────────────────────────────────────────
TIPOS_EVENTO = {
    "💍 Casamento / Formatura": "casamento",
    "💼 Corporativo": "corporativo",
    "🎂 Aniversário / Confraternização": "aniversario",
    "⭐ VIP / Exclusivo": "vip",
    "💻 Hackathon / Tech": "hackathon",
    "🎤 Palestra / Conferência": "palestra",
}

# ── Inicialização do estado ─────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []

if "thinking" not in st.session_state:
    st.session_state.thinking = False

if "thinking" not in st.session_state:
    st.session_state.thinking = False

if "idioma" not in st.session_state:
    st.session_state.idioma = "🇧🇷 Português"

if "provedor_ia" not in st.session_state:
    st.session_state.provedor_ia = "⚡ Groq (Llama 3.3)"

if "usuario_logado" not in st.session_state:
    st.session_state.usuario_logado = None

if "tenant" not in st.session_state:
    st.session_state.tenant = None

if "plano" not in st.session_state:
    st.session_state.plano = "free"

if "crm_clientes" not in st.session_state:
    st.session_state.crm_clientes = [
        {"id":1,"nome":"Ana Lima","empresa":"Lima Eventos","email":"ana@lima.com","tel":"(11)99001-0001","tipo":"Casamento","eventos":3,"valor_total":45000,"status":"Ativo","aniversario":"15/03","notas":"Prefere comunicação por WhatsApp","ultima_interacao":"10/05/2026"},
        {"id":2,"nome":"Carlos Mendes","empresa":"TechCorp","email":"carlos@techcorp.com","tel":"(11)99002-0002","tipo":"Corporativo","eventos":5,"valor_total":120000,"status":"Ativo","aniversario":"22/08","notas":"Decisor financeiro. Gosta de relatórios detalhados","ultima_interacao":"15/05/2026"},
        {"id":3,"nome":"Beatriz Costa","empresa":"VIP Produções","email":"bea@vip.com","tel":"(11)99003-0003","tipo":"VIP","eventos":2,"valor_total":80000,"status":"Prospect","aniversario":"05/11","notas":"Indicada pelo Carlos. Interesse em pacote Luxo","ultima_interacao":"18/05/2026"},
    ]

if "qr_codes" not in st.session_state:
    st.session_state.qr_codes = {}

if "kanban" not in st.session_state:
    st.session_state.kanban = {
        "Prospect":           [{"id":1,"cliente":"Beatriz Costa","evento":"Casamento 2026","valor":35000,"tipo":"Casamento","contato":"bea@vip.com","nota":"Interesse no pacote Premium"},{"id":2,"cliente":"João Silva","evento":"Hackathon StartupXP","valor":18000,"tipo":"Hackathon","contato":"joao@startupxp.com","nota":"Aguardando aprovação do board"}],
        "Proposta enviada":   [{"id":3,"cliente":"Maria Souza","evento":"Festa 50 anos","valor":22000,"tipo":"Aniversário","contato":"maria@email.com","nota":"Proposta enviada em 10/05"}],
        "Negociação":         [{"id":4,"cliente":"TechCorp","evento":"Hackathon TechCorp","valor":45000,"tipo":"Corporativo","contato":"carlos@techcorp.com","nota":"Negociando desconto 10%"}],
        "Fechado":            [{"id":5,"cliente":"Silva & Pereira","evento":"Casamento Silva","valor":78000,"tipo":"Casamento","contato":"ana@lima.com","nota":"Contrato assinado"}],
        "Em execução":        [],
        "Concluído":          [{"id":6,"cliente":"VIP Produções","evento":"Jantar VIP","valor":55000,"tipo":"VIP","contato":"bea@vip.com","nota":"Evento realizado com sucesso"}],
    }

if "leads_landing" not in st.session_state:
    st.session_state.leads_landing = []

if "wpp_templates" not in st.session_state:
    st.session_state.wpp_templates = []

if "clientes_saas" not in st.session_state:
    st.session_state.clientes_saas = {
        "spotlight": {
            "nome": "Spotlight Eventos",
            "email": "admin@spotlight.com",
            "senha": "admin123",
            "plano": "enterprise",
            "cor": "#534AB7",
            "logo": "🎯",
            "eventos": [],
            "vencimento": "2026-12-31",
            "max_eventos": 999,
        },
        "festa_vip": {
            "nome": "Festa VIP Produções",
            "email": "admin@festavip.com",
            "senha": "festa123",
            "plano": "profissional",
            "cor": "#B8860B",
            "logo": "⭐",
            "eventos": [],
            "vencimento": "2025-12-31",
            "max_eventos": 20,
        },
    }

if "evento_atual" not in st.session_state:
    st.session_state.evento_atual = None

if "eventos_cadastrados" not in st.session_state:
    st.session_state.eventos_cadastrados = [
        {
            "nome": "Casamento Silva & Pereira",
            "tipo": "casamento",
            "data": "12/07/2025",
            "local": "Villa Giardini, SP",
            "convidados": 180,
            "status": "confirmed",
        },
        {
            "nome": "Hackathon TechCorp 2025",
            "tipo": "hackathon",
            "data": "20/08/2025",
            "local": "Centro de Convenções, SP",
            "convidados": 240,
            "status": "pending",
        },
        {
            "nome": "Jantar VIP Investidores",
            "tipo": "vip",
            "data": "05/09/2025",
            "local": "Restaurante Fasano, SP",
            "convidados": 30,
            "status": "vip",
        },
    ]

# ── Gate de autenticação ─────────────────────────────────────────────────────
if not st.session_state.usuario_logado:
    tela_login()
    st.stop()

tenant_data = st.session_state.clientes_saas.get(st.session_state.tenant, {})
plano_atual = st.session_state.plano
plano_info  = PLANOS.get(plano_atual, PLANOS["free"])

# ── Sidebar ─────────────────────────────────────────────────────────────────
with st.sidebar:
    logo = tenant_data.get("logo", "🎯")
    nome_empresa = tenant_data.get("nome", "SpotlightIA")
    st.markdown(f"""
<div style="padding:8px 0 4px">
  <div class="sidebar-logo">{logo} {nome_empresa}</div>
  <div style="font-size:11px;color:var(--text-muted);margin-top:4px;font-weight:500;text-transform:uppercase;letter-spacing:0.06em">
    {plano_info['nome']} · {plano_info['preco']}
  </div>
</div>
""", unsafe_allow_html=True)
    # Info do plano
    plano_emoji = {"free":"🆓","essencial":"📦","profissional":"🏆","enterprise":"👑"}.get(plano_atual,"📦")
    st.markdown(f"""<div style="background:rgba(124,106,255,0.08);border:1px solid rgba(124,106,255,0.15);border-radius:10px;padding:10px 12px;margin:4px 0 8px">
<div style="font-size:10px;color:var(--text-muted);text-transform:uppercase;letter-spacing:.08em">Plano ativo</div>
<div style="font-size:16px;font-weight:700;margin-top:2px">{plano_emoji} {plano_info['nome']}</div>
<div style="font-size:11px;color:var(--text-muted);margin-top:2px">{plano_info['preco']} · {tenant_data.get('max_eventos','—')} eventos</div>
</div>""", unsafe_allow_html=True)

    col_sair1, col_sair2 = st.columns(2)
    with col_sair1:
        if st.button("🚪 Sair", use_container_width=True, key="btn_logout"):
            st.session_state.usuario_logado = None
            st.session_state.tenant = None
            st.rerun()
    with col_sair2:
        if st.button("💎 Upgrade", use_container_width=True, key="btn_upgrade"):
            st.session_state.show_upgrade = True

    st.divider()

    # Seletor de idioma
    idioma_sel = st.selectbox("🌐 Idioma / Language", list(IDIOMAS.keys()), index=list(IDIOMAS.keys()).index(st.session_state.idioma), key="sel_idioma", label_visibility="collapsed")
    if idioma_sel != st.session_state.idioma:
        st.session_state.idioma = idioma_sel
        st.session_state.messages = []
        st.rerun()

    st.divider()

    # Provedor de IA — Gemini principal, Groq fallback
    # Ordem de prioridade: Gemini (6M tokens/dia grátis) > Groq (500k/dia, ultra rápido)
    api_key = ""
    provedor_sel = ""
    api_keys_disponiveis = {}

    for nome_secret, nome_prov in [("GEMINI_API_KEY", "gemini"), ("GROQ_API_KEY", "groq")]:
        try:
            chave = st.secrets.get(nome_secret, "")
            if chave:
                api_keys_disponiveis[nome_prov] = chave
                if not api_key:
                    api_key = chave
                    provedor_sel = nome_prov
        except Exception:
            continue

    st.session_state.provedor_ia = provedor_sel or "groq"

    st.divider()

    # Seletor de evento ativo
    st.markdown("### 📋 Evento ativo")
    opcoes_evento = ["— Nenhum selecionado —"] + [
        e["nome"] for e in st.session_state.eventos_cadastrados
    ]
    idx = st.selectbox("Contexto do agente", opcoes_evento, label_visibility="collapsed")
    if idx != "— Nenhum selecionado —":
        st.session_state.evento_atual = next(
            (e for e in st.session_state.eventos_cadastrados if e["nome"] == idx), None
        )
    else:
        st.session_state.evento_atual = None

    # Info do evento ativo
    if st.session_state.evento_atual:
        ev = st.session_state.evento_atual
        tipo_emoji = {"casamento":"💍","hackathon":"💻","vip":"⭐","corporativo":"💼","aniversario":"🎂","palestra":"🎤"}.get(ev.get("tipo",""),"🎉")
        status_map = {"confirmed": ("✅", "Confirmado"), "pending": ("🟡", "Planejamento"), "vip": ("⭐", "VIP")}
        icon, label = status_map.get(ev.get("status",""), ("❓", "—"))
        st.markdown(f"""<div style="background:linear-gradient(135deg,rgba(124,106,255,0.08),rgba(124,106,255,0.04));border:1px solid rgba(124,106,255,0.15);border-radius:12px;padding:12px 14px;margin-bottom:4px">
<div style="font-size:14px;font-weight:700">{tipo_emoji} {ev['nome']}</div>
<div style="font-size:11px;color:var(--text-muted);margin-top:6px;line-height:1.8">
📅 {ev.get('data','—')}<br>
📍 {ev.get('local','—')}<br>
👥 {ev['convidados']} convidados<br>
{icon} {label}
</div></div>""", unsafe_allow_html=True)

    st.divider()

    # Cadastrar novo evento
    with st.expander("➕ Cadastrar novo evento"):
        novo_nome = st.text_input("Nome do evento")
        novo_tipo = st.selectbox("Tipo", list(TIPOS_EVENTO.keys()))
        novo_data = st.text_input("Data (dd/mm/aaaa)")
        novo_local = st.text_input("Local")
        novo_convidados = st.number_input("Nº de convidados", min_value=1, value=50)
        if st.button("Cadastrar", use_container_width=True):
            if novo_nome and novo_data and novo_local:
                novo_ev = {
                    "nome": novo_nome, "tipo": TIPOS_EVENTO[novo_tipo],
                    "data": novo_data, "local": novo_local,
                    "convidados": novo_convidados, "status": "pending",
                }
                st.session_state.eventos_cadastrados.append(novo_ev)
                if DB_DISPONIVEL and st.session_state.get("tenant"):
                    db.evento_criar(st.session_state.tenant, novo_nome, TIPOS_EVENTO[novo_tipo], novo_data, novo_local, novo_convidados)
                st.success(f"Evento '{novo_nome}' cadastrado!")
                st.rerun()
            else:
                st.error("Preencha nome, data e local.")

    st.divider()

    # Ações rápidas
    st.markdown("### ⚡ Ações rápidas")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🗑️ Limpar chat", use_container_width=True):
            st.session_state.messages = []
            st.rerun()
    with col2:
        if st.button("📤 Exportar", use_container_width=True):
            historico = "\n\n".join(
                f"{'Você' if m['role']=='user' else 'EventIA'}: {m['content']}"
                for m in st.session_state.messages
            )
            st.download_button(
                "⬇️ Baixar .txt",
                historico,
                file_name=f"chat_eventoia_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
                mime="text/plain",
                use_container_width=True,
            )

    st.divider()
    st.divider()
    if DB_DISPONIVEL:
        st.markdown("""<div style="background:rgba(107,203,119,0.1);border:1px solid rgba(107,203,119,0.25);border-radius:8px;padding:6px 10px;font-size:11px;color:#6BCB77;font-weight:500">🗄️ SQLite · Dados persistentes</div>""", unsafe_allow_html=True)
    else:
        st.markdown("""<div style="background:rgba(255,217,61,0.08);border:1px solid rgba(255,217,61,0.2);border-radius:8px;padding:6px 10px;font-size:11px;color:#FFD93D;font-weight:500">⚠️ Modo memória</div>""", unsafe_allow_html=True)
    if AWS_DISPONIVEL:
        aws_st = aws.aws_status()
        s3_ok  = aws_st.get("s3") == "ativo"
        ses_ok = aws_st.get("ses") == "ativo"
        bed_ok = aws_st.get("bedrock") == "ativo"
        aws_label = " · ".join(filter(None, ["S3" if s3_ok else "", "SES" if ses_ok else "", "Bedrock" if bed_ok else ""]))
        st.markdown(f"""<div style="background:rgba(255,153,0,0.1);border:1px solid rgba(255,153,0,0.25);border-radius:8px;padding:6px 10px;font-size:11px;color:#FF9900;font-weight:500">☁️ AWS · {aws_label or 'Conectado'}</div>""", unsafe_allow_html=True)
    prov_label = {"gemini": "GEMINI 2.0 FLASH", "groq": "GROQ · LLAMA 3.3"}.get(provedor_sel, "IA")
    prov_icon  = {"gemini": "🌟", "groq": "⚡"}.get(provedor_sel, "🤖")
    st.markdown(f"""<div style="text-align:center;font-size:10px;color:var(--text-muted);margin-top:8px;letter-spacing:0.05em">{prov_icon} {prov_label}</div>""", unsafe_allow_html=True)

# ── HELPER: chamada Groq direto ───────────────────────────────────────────────
def ia_call(prompt: str, system: str = "Você é SpotlightIA, assistente de eventos. Responda em português formal.", max_tokens: int = 1024) -> str:
    """Chama a IA — tenta Gemini primeiro, depois Groq como fallback."""
    if not api_key:
        return "Configure a API Key nos Secrets do Streamlit Cloud."
    provedor_atual = st.session_state.get("provedor_ia", "groq")
    # Tenta Gemini primeiro
    if provedor_atual == "gemini":
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            model_g = genai.GenerativeModel("gemini-2.0-flash", system_instruction=system)
            resp = model_g.generate_content(prompt)
            return resp.text
        except Exception:
            pass
    # Fallback Groq
    try:
        groq_key = api_keys_disponiveis.get("groq", api_key) if "api_keys_disponiveis" in dir() else api_key
        client_g = Groq(api_key=groq_key)
        resp = client_g.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role":"system","content":system},{"role":"user","content":prompt}],
            max_tokens=max_tokens,
        )
        return resp.choices[0].message.content
    except Exception as e:
        return f"Erro: {e}"

# ── Conteúdo principal ──────────────────────────────────────────────────────
st.markdown("""
<div class="main-heading">💬 SpotlightIA</div>
<div class="main-subheading">Seu assistente inteligente para eventos privados</div>
""", unsafe_allow_html=True)

tab_chat, tab_eventos, tab_checklist, tab_estrutura, tab_buffet, tab_logistica, tab_foto, tab_orcamento, tab_dash, tab_email, tab_rsvp, tab_convite, tab_crono, tab_docs, tab_widget, tab_contrato, tab_mapa, tab_saas, tab_relatorio, tab_crm, tab_qr, tab_kanban, tab_mc, tab_landing, tab_pix, tab_scoring = st.tabs([T("chat"), T("eventos"), T("checklist"), T("estrutura"), T("buffet"), T("logistica"), T("foto"), T("orcamento"), T("dashboard"), T("confirmacoes"), T("rsvp"), T("convite"), T("cronograma"), T("documentos"), T("widget"), "📑 Contrato", "🗺️ Mapa do Evento", "💎 Planos & SaaS", "📊 Relatório PDF", "🤝 CRM", "🎫 QR Code", "🔁 Funil Kanban", "🎙️ Roteiro MC", "📣 Captação", "💳 PIX & Pagamento", "🎯 Scoring de Leads"])

# Tabs principais


# ── TAB: CHAT ───────────────────────────────────────────────────────────────
with tab_chat:
    # Mensagem de boas-vindas
    if not st.session_state.messages:
        # KPIs rápidos no topo do chat
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        kpi1.metric("📅 Eventos ativos", len(st.session_state.eventos_cadastrados))
        total_rsvp = len(st.session_state.get("lista_rsvp", []))
        conf_rsvp = sum(1 for r in st.session_state.get("lista_rsvp", []) if r.get("status") == "Confirmado")
        kpi2.metric("✅ RSVPs confirmados", conf_rsvp)
        total_cli = len(st.session_state.get("crm_clientes", []))
        kpi3.metric("👥 Clientes CRM", total_cli)
        kpi4.metric("🌐 Idioma", st.session_state.get("idioma", "🇧🇷 Português")[:5])
        st.divider()

        with st.chat_message("assistant", avatar="🎉"):
            nome_emp = tenant_data.get("nome", "Spotlight Eventos") if "tenant_data" in dir() else "Spotlight Eventos"
            st.markdown(
                f"Olá! Sou a **SpotlightIA**, assistente inteligente da **{nome_emp}**.\n\n"
                "Posso ajudar com:\n"
                "- ✅ **RSVP e confirmação de presenças**\n"
                "- 📋 **Planejamento e checklist**\n"
                "- 📦 **Pacotes e vendas**\n"
                "- ❓ **Dúvidas logísticas**\n\n"
                "Selecione um evento na barra lateral ou me conte sobre o seu evento!"
            )

    # Histórico de mensagens
    for msg in st.session_state.messages:
        avatar = "🎉" if msg["role"] == "assistant" else "👤"
        with st.chat_message(msg["role"], avatar=avatar):
            st.markdown(msg["content"])

    # Input do usuário
    if prompt := st.chat_input(T("input_hint"), disabled=st.session_state.thinking):
        if not api_key:
            st.error("⚠️ Insira sua API Key da Anthropic na barra lateral para continuar.")
            st.stop()

        # Exibe mensagem do usuário
        with st.chat_message("user", avatar="👤"):
            st.markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.session_state.thinking = True

        # Monta contexto completo com memória de todos os eventos
        system = SYSTEM_PROMPT + "\n\n" + T("idioma_sistema")

        # Injeta todos os eventos cadastrados na memória do agente
        if st.session_state.eventos_cadastrados:
            eventos_json = json.dumps(st.session_state.eventos_cadastrados, ensure_ascii=False, indent=2)
            system += f"""

## MEMÓRIA DE EVENTOS CADASTRADOS
Você tem acesso completo aos seguintes eventos da Spotlight Eventos. Use essas informações para personalizar cada resposta, citar datas, locais e detalhes reais:

{eventos_json}
"""

        # Injeta lista de RSVPs se existir
        if "lista_rsvp" in st.session_state and st.session_state.lista_rsvp:
            rsvp_json = json.dumps(st.session_state.lista_rsvp, ensure_ascii=False, indent=2)
            system += f"""

## MEMÓRIA DE RSVPs REGISTRADOS
Lista atual de convidados confirmados, pendentes e recusados:

{rsvp_json}
"""

        # Destaca evento ativo se selecionado
        if st.session_state.evento_atual:
            ev = st.session_state.evento_atual
            system += f"""

## EVENTO ATIVO NESTA CONVERSA
O usuário está conversando especificamente sobre este evento — priorize ele nas respostas:
{json.dumps(ev, ensure_ascii=False, indent=2)}
"""

        # Chama a API
        with st.chat_message("assistant", avatar="🎉"):
            with st.spinner("Processando..."):
                try:
                    provedor = st.session_state.get("provedor_ia", "⚡ Groq (Llama 3.3)")
                    reply = ""

                    if provedor == "⚡ Groq (Llama 3.3)":
                        client = Groq(api_key=api_key)
                        groq_messages = [{"role": "system", "content": system}] + st.session_state.messages
                        response = client.chat.completions.create(
                            model="llama-3.3-70b-versatile",
                            messages=groq_messages,
                            max_tokens=1024,
                        )
                        reply = response.choices[0].message.content

                    elif provedor == "🌟 Google Gemini":
                        import google.generativeai as genai
                        genai.configure(api_key=api_key)
                        model_gem = genai.GenerativeModel(
                            model_name="gemini-1.5-flash",
                            system_instruction=system,
                        )
                        history_gem = []
                        for m in st.session_state.messages[:-1]:
                            role = "user" if m["role"] == "user" else "model"
                            history_gem.append({"role": role, "parts": [m["content"]]})
                        chat_gem = model_gem.start_chat(history=history_gem)
                        resp_gem = chat_gem.send_message(st.session_state.messages[-1]["content"])
                        reply = resp_gem.text

                    elif provedor == "🤗 Hugging Face":
                        import requests as _req
                        HF_MODEL = "mistralai/Mistral-7B-Instruct-v0.3"
                        prompt_hf = "<s>[INST] <<SYS>>" + system + "<</SYS>>\n"
                        for m in st.session_state.messages[:-1]:
                            if m["role"] == "user":
                                prompt_hf += f"{m['content']} [/INST] "
                            else:
                                prompt_hf += f"{m['content']} </s><s>[INST] "
                        prompt_hf += f"{st.session_state.messages[-1]['content']} [/INST]"
                        hf_resp = _req.post(
                            f"https://api-inference.huggingface.co/models/{HF_MODEL}",
                            headers={"Authorization": f"Bearer {api_key}"},
                            json={"inputs": prompt_hf, "parameters": {"max_new_tokens": 800, "return_full_text": False}},
                            timeout=30,
                        )
                        hf_data = hf_resp.json()
                        if isinstance(hf_data, list):
                            reply = hf_data[0].get("generated_text", "Sem resposta.")
                        elif "error" in hf_data:
                            raise Exception(hf_data["error"])
                        else:
                            reply = str(hf_data)

                    st.markdown(reply)
                    st.session_state.messages.append({"role": "assistant", "content": reply})
                    st.session_state.thinking = False
                    # Persiste no banco
                    st.session_state.thinking = False
                    if DB_DISPONIVEL and st.session_state.get("tenant"):
                        tid = st.session_state.tenant
                        db.chat_salvar(tid, "user", prompt)
                        db.chat_salvar(tid, "assistant", reply)

                except Exception as e:
                    err = str(e).lower()
                    if "invalid" in err or "401" in err or "unauthorized" in err:
                        st.error("❌ API Key inválida. Verifique o link na barra lateral.")
                    elif "quota" in err or "429" in err or "rate" in err:
                        st.error("⚠️ Limite de requisições atingido. Aguarde alguns instantes.")
                    else:
                        st.error(f"❌ Erro: {e}")

    # Sugestões de perguntas
    if not st.session_state.messages:
        st.markdown("#### 💡 Experimente perguntar:")
        sugestoes = T("sugestoes")
        # Primeira linha — 3 sugestões
        cols1 = st.columns(3)
        for i in range(min(3, len(sugestoes))):
            with cols1[i]:
                if st.button(f"→ {sugestoes[i]}", use_container_width=True, key=f"sug_{i}"):
                    st.session_state.messages.append({"role": "user", "content": sugestoes[i]})
                    st.rerun()
        # Segunda linha — restantes
        if len(sugestoes) > 3:
            cols2 = st.columns(len(sugestoes) - 3)
            for i in range(3, len(sugestoes)):
                with cols2[i-3]:
                    if st.button(f"→ {sugestoes[i]}", use_container_width=True, key=f"sug_{i}"):
                        st.session_state.messages.append({"role": "user", "content": sugestoes[i]})
                        st.rerun()

# ── TAB: EVENTOS ────────────────────────────────────────────────────────────
with tab_eventos:
    st.markdown("### 📅 Eventos cadastrados")
    status_labels = {"confirmed": "✅ Confirmado", "pending": "🟡 Em planejamento", "vip": "⭐ VIP"}
    status_colors = {"confirmed": "rgba(107,203,119,0.1)", "pending": "rgba(255,217,61,0.08)", "vip": "rgba(124,106,255,0.1)"}

    # Resumo rápido
    ev_conf = sum(1 for e in st.session_state.eventos_cadastrados if e["status"] == "confirmed")
    ev_pend = sum(1 for e in st.session_state.eventos_cadastrados if e["status"] == "pending")
    ev_vip  = sum(1 for e in st.session_state.eventos_cadastrados if e["status"] == "vip")
    ev_total_conv = sum(e["convidados"] for e in st.session_state.eventos_cadastrados)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("📅 Total", len(st.session_state.eventos_cadastrados))
    m2.metric("✅ Confirmados", ev_conf)
    m3.metric("🟡 Planejamento", ev_pend)
    m4.metric("👥 Total convidados", ev_total_conv)

    st.divider()

    for ev in st.session_state.eventos_cadastrados:
        tipo_emoji = {"casamento":"💍","hackathon":"💻","vip":"⭐","corporativo":"💼","aniversario":"🎂","palestra":"🎤"}.get(ev.get("tipo",""),"🎉")
        cor_fundo = status_colors.get(ev["status"], "rgba(124,106,255,0.06)")

        with st.expander(f"{tipo_emoji} {ev['nome']} — {ev.get('data','—')}"):
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("📍 Local", ev.get("local","—"))
            col2.metric("👥 Convidados", ev["convidados"])
            col3.metric("📌 Status", status_labels.get(ev["status"], "—"))
            col4.metric("🎯 Tipo", ev.get("tipo","—").title())

            # Barra de progresso RSVP
            rsvps_ev = [r for r in st.session_state.get("lista_rsvp", []) if r.get("evento") == ev["nome"]]
            conf_ev = sum(1 for r in rsvps_ev if r.get("status") == "Confirmado")
            pct = conf_ev / ev["convidados"] if ev["convidados"] > 0 else 0
            st.progress(min(pct, 1.0), text=f"RSVP: {conf_ev}/{ev['convidados']} confirmados ({int(pct*100)}%)")

            col_b1, col_b2 = st.columns(2)
            if col_b1.button(f"💬 Conversar sobre este evento", key=f"btn_{ev['nome']}", use_container_width=True):
                st.session_state.evento_atual = ev
                st.session_state.messages.append({
                    "role": "user",
                    "content": f"Quero informações sobre o evento: {ev['nome']}",
                })
                st.rerun()
            if col_b2.button(f"📋 Ver checklist", key=f"btn_ck_{ev['nome']}", use_container_width=True):
                st.session_state.evento_atual = ev

# ── TAB: CHECKLIST ──────────────────────────────────────────────────────────
with tab_checklist:
    st.markdown("### ✅ Checklist de planejamento")

    tipo_checklist = st.selectbox("Tipo de evento", list(TIPOS_EVENTO.keys()), key="tipo_check")

    checklists = {
        "casamento": [
            "Definir data e local", "Contratar buffet", "Escolher decoração",
            "Enviar convites", "Contratar fotógrafo", "Definir cardápio",
            "Organizar lista de presentes", "Contratar DJ / banda",
            "Confirmar presenças (RSVP)", "Ensaio geral",
        ],
        "corporativo": [
            "Definir objetivo do evento", "Reservar espaço", "Contratar AV/streaming",
            "Enviar convites corporativos", "Preparar agenda", "Confirmar palestrantes",
            "Organizar coffee break", "Preparar material de apoio",
            "Testar equipamentos", "Coletar feedbacks",
        ],
        "hackathon": [
            "Definir tema e desafios", "Abrir inscrições", "Montar equipe de mentores",
            "Reservar espaço com internet", "Preparar premiação", "Definir critérios de avaliação",
            "Garantir alimentação", "Preparar ambiente de trabalho",
            "Comunicar participantes", "Organizar apresentações finais",
        ],
        "palestra": [
            "Confirmar palestrante", "Reservar auditório", "Preparar sistema de som",
            "Divulgar evento", "Abrir inscrições", "Preparar coffee break",
            "Testar apresentação", "Preparar certificados",
            "Confirmar presenças", "Gravar palestra (se aplicável)",
        ],
        "aniversario": [
            "Definir tema da festa", "Reservar espaço", "Contratar buffet",
            "Encomendar bolo", "Enviar convites", "Contratar DJ",
            "Definir decoração", "Organizar lembranças",
            "Confirmar convidados", "Preparar playlist",
        ],
        "vip": [
            "Definir lista de convidados VIP", "Escolher local exclusivo",
            "Contratar segurança", "Preparar menu personalizado",
            "Organizar transporte dos convidados", "Definir dress code",
            "Preparar brindes exclusivos", "Contratar sommelier",
            "Confirmar presenças individualmente", "Preparar experiência personalizada",
        ],
    }

    tipo_key = TIPOS_EVENTO[tipo_checklist]
    itens = checklists.get(tipo_key, checklists["corporativo"])

    check_key = f"checks_{tipo_key}"
    if check_key not in st.session_state:
        st.session_state[check_key] = [False] * len(itens)

    concluidos = 0
    for i, item in enumerate(itens):
        checked = st.checkbox(item, value=st.session_state[check_key][i], key=f"chk_{tipo_key}_{i}")
        st.session_state[check_key][i] = checked
        if checked:
            concluidos += 1

    progresso = concluidos / len(itens)
    st.divider()
    st.progress(progresso, text=f"Progresso: {concluidos}/{len(itens)} itens concluídos ({int(progresso*100)}%)")

    if st.button("💬 Pedir ajuda com o planejamento", use_container_width=True):
        pendentes = [itens[i] for i, c in enumerate(st.session_state[check_key]) if not c]
        msg = f"Estou planejando um evento do tipo '{tipo_checklist}'. Ainda preciso resolver: {', '.join(pendentes)}. Pode me ajudar?"
        st.session_state.messages.append({"role": "user", "content": msg})
        st.rerun()

# ── TAB: ESTRUTURA & TÉCNICA ─────────────────────────────────────────────────
with tab_estrutura:
    import requests

    st.markdown("### 🔊 Aparelhagem, Iluminação & Estrutura")
    st.caption("Referências visuais e dicas técnicas para o seu evento")

    categorias = [
        {
            "titulo": "🔊 Sistema de Som",
            "descricao": "Caixas de som, subwoofers, mesas de mixagem e microfones para eventos de todos os portes.",
            "dicas": [
                "Ate 100 pessoas: 2 caixas ativas de 15pol sao suficientes",
                "100-300 pessoas: adicione subwoofer e retorno de palco",
                "Acima de 300 pessoas: sistema line array com delay towers",
                "Sempre teste o som 2h antes do inicio do evento",
            ],
            "imgs": [
                "https://images.unsplash.com/photo-1516280440614-37939bbacd81?w=400&h=250&fit=crop",
                "https://images.unsplash.com/photo-1470225620780-dba8ba36b745?w=400&h=250&fit=crop",
            ],
        },
        {
            "titulo": "💡 Iluminação Cênica",
            "descricao": "Moving heads, par LEDs, strobes e efeitos especiais que transformam qualquer ambiente.",
            "dicas": [
                "Par LEDs coloridos criam atmosfera com baixo custo",
                "Moving heads sao ideais para pistas de danca e palcos",
                "Uplighting valoriza paredes e estruturas do local",
                "Inclua iluminacao de emergencia para eventos noturnos",
            ],
            "imgs": [
                "https://images.unsplash.com/photo-1504704911898-68304a7d2807?w=400&h=250&fit=crop",
                "https://images.unsplash.com/photo-1429514513361-8a632ff5f2af?w=400&h=250&fit=crop",
            ],
        },
        {
            "titulo": "🏗️ Estrutura de Palco",
            "descricao": "Palcos modulares, trusses e tendas para suporte de equipamentos e apresentacoes.",
            "dicas": [
                "Palco padrao: 6m x 4m x 80cm para bandas e apresentacoes",
                "Trusses permitem suspender iluminacao e teloes com seguranca",
                "Exija ART (Anotacao de Responsabilidade Tecnica) do montador",
                "Verifique a carga eletrica disponivel no local antecipadamente",
            ],
            "imgs": [
                "https://images.unsplash.com/photo-1540039155733-5bb30b4e2d2a?w=400&h=250&fit=crop",
                "https://images.unsplash.com/photo-1501281668745-f7f57925c3b4?w=400&h=250&fit=crop",
            ],
        },
        {
            "titulo": "📺 Telões & LED Wall",
            "descricao": "Paineis de LED, projetores e teloes para transmissoes ao vivo, palestras e shows.",
            "dicas": [
                "Projetor: ideal para ambientes fechados e escuros",
                "Painel de LED: funciona em qualquer iluminacao, interno ou externo",
                "Resolucao minima recomendada: Full HD (1920x1080)",
                "Para palestras: 1 telao a cada 50 pessoas sentadas",
            ],
            "imgs": [
                "https://images.unsplash.com/photo-1591115765373-5207764f72e7?w=400&h=250&fit=crop",
                "https://images.unsplash.com/photo-1475721027785-f74eccf877e2?w=400&h=250&fit=crop",
            ],
        },
    ]

    for cat in categorias:
        st.markdown(f"#### {cat['titulo']}")
        st.markdown(cat["descricao"])

        col1, col2, col3 = st.columns([1, 1, 1])

        for col, img_url in zip([col1, col2], cat["imgs"]):
            try:
                r = requests.get(img_url, timeout=6)
                if r.status_code == 200:
                    col.image(r.content, use_container_width=True)
                else:
                    col.info("Imagem indisponivel")
            except Exception:
                col.info("Imagem indisponivel")

        with col3:
            st.markdown("**💡 Dicas técnicas:**")
            for dica in cat["dicas"]:
                st.markdown(f"- {dica}")

        if st.button(f"💬 Perguntar sobre {cat['titulo']}", key=f"btn_est_{cat['titulo']}", use_container_width=True):
            msg = f"Preciso de orientacao sobre {cat['titulo']} para o meu evento. Pode me ajudar com o planejamento tecnico?"
            st.session_state.messages.append({"role": "user", "content": msg})
            st.rerun()

        st.divider()

    # Categorias extras: Gerador e Camarim
    extras = [
        {
            "titulo": "⚡ Gerador Elétrico",
            "descricao": "Fornecimento de energia independente para garantir que o evento nao pare por falta de luz.",
            "dicas": [
                "Calcule a carga total dos equipamentos antes de escolher o gerador",
                "Gerador silenciado e obrigatorio para eventos em areas residenciais",
                "Mantenha sempre 30% de folga na capacidade do gerador",
                "Posicione o gerador longe do palco para evitar ruido e vibracoes",
            ],
            "imgs": [
                "https://images.unsplash.com/photo-1609234656388-0ff363383899?w=400&h=250&fit=crop",
                "https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=400&h=250&fit=crop",
            ],
        },
        {
            "titulo": "🎭 Camarim",
            "descricao": "Espaco reservado para artistas, palestrantes e equipe tecnica se prepararem com conforto.",
            "dicas": [
                "Camarim minimo: 9m2, com espelho, tomadas e iluminacao adequada",
                "Separe camarim masculino e feminino em eventos com varios artistas",
                "Providencie rider tecnico: agua, frutas, toalhas e snacks",
                "Garanta acesso privado ao palco sem passar pela plateia",
            ],
            "imgs": [
                "https://images.unsplash.com/photo-1598300042247-d088f8ab3a91?w=400&h=250&fit=crop",
                "https://images.unsplash.com/photo-1560472355-536de3962603?w=400&h=250&fit=crop",
            ],
        },
    ]

    for cat in extras:
        st.markdown(f"#### {cat['titulo']}")
        st.markdown(cat["descricao"])

        col1, col2, col3 = st.columns([1, 1, 1])

        for col, img_url in zip([col1, col2], cat["imgs"]):
            try:
                r = requests.get(img_url, timeout=6)
                if r.status_code == 200:
                    col.image(r.content, use_container_width=True)
                else:
                    col.info("Imagem indisponivel")
            except Exception:
                col.info("Imagem indisponivel")

        with col3:
            st.markdown("**💡 Dicas técnicas:**")
            for dica in cat["dicas"]:
                st.markdown(f"- {dica}")

        if st.button(f"💬 Perguntar sobre {cat['titulo']}", key=f"btn_ext_{cat['titulo']}", use_container_width=True):
            msg = f"Preciso de orientacao sobre {cat['titulo']} para o meu evento. Pode me ajudar?"
            st.session_state.messages.append({"role": "user", "content": msg})
            st.rerun()

        st.divider()

# ── TAB: BUFFET & GASTRONOMIA ─────────────────────────────────────────────────
with tab_buffet:

    st.markdown("### 🍽️ Buffet & Gastronomia")
    st.caption("Planejamento gastronômico completo para o seu evento")

    # ── Calculadora de quantidade ──────────────────────────────────────────────
    st.markdown("#### 🧮 Calculadora de Quantidade")
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        num_pessoas = st.number_input("Número de convidados", min_value=10, max_value=2000, value=100, step=10)
    with col_b:
        tipo_refeicao = st.selectbox("Tipo de refeição", ["Coquetel / Finger food", "Jantar completo", "Almoço completo", "Coffee break", "Festa / Dança"])
    with col_c:
        duracao_horas = st.slider("Duração do evento (horas)", 2, 12, 5)

    # Tabela de referência por tipo
    referencias = {
        "Coquetel / Finger food":  {"porcoes_pp": 12, "bebida_pp": 0.5,  "garcom_pp": 30, "obs": "12-15 pecas por pessoa"},
        "Jantar completo":         {"porcoes_pp": 1,  "bebida_pp": 0.75, "garcom_pp": 15, "obs": "Prato principal + 3 acompanhamentos"},
        "Almoço completo":         {"porcoes_pp": 1,  "bebida_pp": 0.6,  "garcom_pp": 20, "obs": "Prato principal + 2 acompanhamentos"},
        "Coffee break":            {"porcoes_pp": 6,  "bebida_pp": 0.4,  "garcom_pp": 40, "obs": "6-8 itens por pessoa"},
        "Festa / Dança":           {"porcoes_pp": 8,  "bebida_pp": 1.0,  "garcom_pp": 25, "obs": "Inclui mesa de frios + doces"},
    }

    ref = referencias[tipo_refeicao]
    total_porcoes = math.ceil(num_pessoas * ref["porcoes_pp"])
    total_bebida  = math.ceil(num_pessoas * ref["bebida_pp"] * duracao_horas)
    total_garcons = math.ceil(num_pessoas / ref["garcom_pp"])

    st.markdown("---")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("🍴 Porções totais", f"{total_porcoes:,}".replace(",", "."), ref["obs"])
    m2.metric("🥤 Bebidas (litros)", f"{total_bebida}L", f"{ref['bebida_pp']}L/pessoa/hora")
    m3.metric("👨‍🍳 Garçons sugeridos", total_garcons, f"1 a cada {ref['garcom_pp']} pessoas")
    m4.metric("👥 Convidados", num_pessoas, f"{duracao_horas}h de evento")

    if st.button("💬 Pedir cardápio sugerido para este evento", use_container_width=True, key="btn_cardapio"):
        msg = f"Preciso montar um cardapio para {num_pessoas} pessoas, {tipo_refeicao}, duracao de {duracao_horas}h. Pode sugerir opcoes e quantidades?"
        st.session_state.messages.append({"role": "user", "content": msg})
        st.rerun()

    st.divider()

    # ── Tipos de serviço ───────────────────────────────────────────────────────
    st.markdown("#### 🍷 Tipos de Serviço")

    servicos = [
        {
            "nome": "Buffet Self-Service",
            "descricao": "Convidados se servem livremente. Ideal para almocos e jantares informais.",
            "pros": ["Custo menor", "Mais variedade", "Dinamico e descontraido"],
            "contras": ["Menos elegante", "Filas podem ocorrer", "Requer espaco para mesas"],
            "ideal": "Corporativo, aniversarios, confraternizacoes",
            "img": "https://images.unsplash.com/photo-1555244162-803834f70033?w=400&h=220&fit=crop",
        },
        {
            "nome": "Serviço Empratado",
            "descricao": "Pratos servidos individualmente na mesa pelos garcons. Alto padrao.",
            "pros": ["Elegante e sofisticado", "Controle de porcoes", "Experiencia premium"],
            "contras": ["Custo mais alto", "Requer mais garcons", "Menu fixo"],
            "ideal": "Casamentos, eventos VIP, jantares executivos",
            "img": "https://images.unsplash.com/photo-1414235077428-338989a2e8c0?w=400&h=220&fit=crop",
        },
        {
            "nome": "Coquetel / Finger Food",
            "descricao": "Itens pequenos servidos em bandejas circulantes. Perfeito para networking.",
            "pros": ["Favorece interacao", "Sem necessidade de mesas", "Visual bonito"],
            "contras": ["Nao substitui refeicao completa", "Logistica de reposicao"],
            "ideal": "Lancamentos, hackathons, palestras, eventos de networking",
            "img": "https://images.unsplash.com/photo-1567521464027-f127ff144326?w=400&h=220&fit=crop",
        },
        {
            "nome": "Estacoes Gastronômicas",
            "descricao": "Ilhas tematicas com culinarias diferentes: massas, grelhados, sobremesas.",
            "pros": ["Experiencia unica", "Muito instagramavel", "Agrada diferentes gostos"],
            "contras": ["Requer mais espaco e equipe", "Custo elevado"],
            "ideal": "Casamentos, eventos VIP, festas de aniversario de alto padrao",
            "img": "https://images.unsplash.com/photo-1504674900247-0877df9cc836?w=400&h=220&fit=crop",
        },
    ]

    for i in range(0, len(servicos), 2):
        cols = st.columns(2)
        for j, col in enumerate(cols):
            if i + j < len(servicos):
                s = servicos[i + j]
                with col:
                    try:
                        r = requests.get(s["img"], timeout=6)
                        if r.status_code == 200:
                            st.image(r.content, use_container_width=True)
                    except Exception:
                        pass
                    st.markdown(f"**{s['nome']}**")
                    st.markdown(s["descricao"])
                    st.markdown(f"✅ {' · '.join(s['pros'])}")
                    st.markdown(f"⚠️ {' · '.join(s['contras'])}")
                    st.caption(f"🎯 Ideal para: {s['ideal']}")
                    if st.button(f"💬 Saiba mais sobre {s['nome']}", key=f"btn_srv_{s['nome']}", use_container_width=True):
                        msg = f"Quero saber mais sobre o servico de {s['nome']} para o meu evento. Quais os custos, cuidados e como contratar?"
                        st.session_state.messages.append({"role": "user", "content": msg})
                        st.rerun()
                    st.markdown("---")

    # ── Restrições alimentares ─────────────────────────────────────────────────
    st.divider()
    st.markdown("#### 🥗 Restrições Alimentares")
    st.caption("Marque as restricoes presentes entre seus convidados para gerar um alerta ao agente")

    col_r1, col_r2, col_r3, col_r4 = st.columns(4)
    veg       = col_r1.checkbox("🌱 Vegetariano")
    vegano    = col_r2.checkbox("🌿 Vegano")
    gluten    = col_r3.checkbox("🚫 Sem glúten")
    lactose   = col_r4.checkbox("🥛 Sem lactose")
    col_r5, col_r6, col_r7, col_r8 = st.columns(4)
    halal     = col_r5.checkbox("☪️ Halal")
    kosher    = col_r6.checkbox("✡️ Kosher")
    frutos    = col_r7.checkbox("🦐 Alergia frutos do mar")
    diabetes  = col_r8.checkbox("🍬 Diabético / low carb")

    restricoes_sel = [r for r, v in [
        ("Vegetariano", veg), ("Vegano", vegano), ("Sem gluten", gluten),
        ("Sem lactose", lactose), ("Halal", halal), ("Kosher", kosher),
        ("Alergia a frutos do mar", frutos), ("Diabetico/low carb", diabetes)
    ] if v]

    if restricoes_sel:
        st.info(f"**Restricoes selecionadas:** {', '.join(restricoes_sel)}")
        if st.button("💬 Pedir cardápio adaptado a essas restrições", use_container_width=True, key="btn_restricoes"):
            msg = f"Meu evento tem convidados com as seguintes restricoes alimentares: {', '.join(restricoes_sel)}. Como adaptar o cardapio e quais cuidados devo ter com o buffet?"
            st.session_state.messages.append({"role": "user", "content": msg})
            st.rerun()

# ── TAB: LOGÍSTICA & TRANSPORTE ───────────────────────────────────────────────
with tab_logistica:
    st.markdown("### 🚗 Logística & Transporte")
    st.caption("Planejamento de acesso, estacionamento e deslocamento dos convidados")

    # ── Calculadora de estacionamento ─────────────────────────────────────────
    st.markdown("#### 🅿️ Calculadora de Estacionamento")
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        total_conv = st.number_input("Total de convidados", min_value=10, max_value=3000, value=100, step=10, key="log_conv")
    with col_b:
        tipo_evento_log = st.selectbox("Tipo de evento", ["Casamento / Formatura", "Corporativo", "Festa / Aniversario", "VIP / Exclusivo", "Hackathon / Palestra"], key="log_tipo")
    with col_c:
        tem_open_bar = st.selectbox("Tem open bar?", ["Sim", "Nao"], key="log_bar")

    # Taxa de uso de carro por tipo
    taxas = {
        "Casamento / Formatura":  0.55,
        "Corporativo":            0.70,
        "Festa / Aniversario":    0.50,
        "VIP / Exclusivo":        0.80,
        "Hackathon / Palestra":   0.60,
    }
    taxa = taxas[tipo_evento_log]
    if tem_open_bar == "Sim":
        taxa *= 0.75  # menos carros quando tem open bar (mais uber/taxi)

    vagas_min = math.ceil(total_conv * taxa / 2)
    vagas_rec = math.ceil(vagas_min * 1.2)
    manobristas = math.ceil(vagas_rec / 30)
    ubers_est = math.ceil(total_conv * (1 - taxa))

    st.markdown("---")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("🚗 Vagas mínimas", vagas_min, "1 vaga a cada 2 pessoas")
    m2.metric("✅ Vagas recomendadas", vagas_rec, "+20% de folga")
    m3.metric("🤵 Manobristas", manobristas, "1 a cada 30 vagas")
    m4.metric("🛵 Uber / Taxi estimado", ubers_est, "sem carro proprio")

    if st.button("💬 Pedir ajuda com logística de estacionamento", use_container_width=True, key="btn_estac"):
        msg = f"Tenho um evento {tipo_evento_log} com {total_conv} convidados. {'Tem open bar.' if tem_open_bar == 'Sim' else 'Sem open bar.'} Como planejar o estacionamento e o valet?"
        st.session_state.messages.append({"role": "user", "content": msg})
        st.rerun()

    st.divider()

    # ── Modalidades de transporte ──────────────────────────────────────────────
    st.markdown("#### 🚌 Modalidades de Transporte")

    modalidades = [
        {
            "nome": "Valet Service",
            "descricao": "Manobristas recebem o carro na entrada e estacionam em local reservado. Elegante e pratico.",
            "quando": "Casamentos, VIP, jantares executivos",
            "dica": "Contrate 1 manobrista a cada 30 vagas. Sinalize bem a area de entrega.",
            "img": "https://images.unsplash.com/photo-1449965408869-eaa3f722e40d?w=400&h=220&fit=crop",
        },
        {
            "nome": "Transfer VIP",
            "descricao": "Vans ou carros executivos buscam convidados em pontos definidos. Ideal para convidados especiais.",
            "quando": "Convidados VIP, palestrantes, noivos, diretores",
            "dica": "Defina os pontos de embarque com antecedencia e compartilhe rotas pelo WhatsApp.",
            "img": "https://images.unsplash.com/photo-1544620347-c4fd4a3d5957?w=400&h=220&fit=crop",
        },
        {
            "nome": "Fretamento de Onibus",
            "descricao": "Onibus fretado com paradas definidas. Reduz trânsito e garante chegada em grupo.",
            "quando": "Eventos corporativos, hackathons, festas em locais remotos",
            "dica": "Planeje horarios de ida e volta. Onibus de 48 lugares para grupos acima de 30 pessoas.",
            "img": "https://images.unsplash.com/photo-1570125909232-eb263c188f7e?w=400&h=220&fit=crop",
        },
        {
            "nome": "Ponto de Uber / Taxi",
            "descricao": "Area exclusiva para desembarque e embarque de aplicativos, evitando congestionamento na entrada.",
            "quando": "Todos os tipos de evento com open bar ou local de dificil acesso",
            "dica": "Sinalize o ponto com placas e informe os convidados no convite digital.",
            "img": "https://images.unsplash.com/photo-1626908013943-df94de54984c?w=400&h=220&fit=crop",
        },
    ]

    for i in range(0, len(modalidades), 2):
        cols = st.columns(2)
        for j, col in enumerate(cols):
            if i + j < len(modalidades):
                m = modalidades[i + j]
                with col:
                    try:
                        r = requests.get(m["img"], timeout=6)
                        if r.status_code == 200:
                            st.image(r.content, use_container_width=True)
                    except Exception:
                        pass
                    st.markdown(f"**{m['nome']}**")
                    st.markdown(m["descricao"])
                    st.caption(f"🎯 Quando usar: {m['quando']}")
                    st.info(f"💡 {m['dica']}")
                    if st.button(f"💬 Saiba mais sobre {m['nome']}", key=f"btn_log_{m['nome']}", use_container_width=True):
                        msg = f"Como contratar e organizar o servico de {m['nome']} para o meu evento?"
                        st.session_state.messages.append({"role": "user", "content": msg})
                        st.rerun()
                    st.markdown("---")

    st.divider()

    # ── Checklist de sinalização ───────────────────────────────────────────────
    st.markdown("#### 🪧 Checklist de Sinalização")
    st.caption("Itens essenciais para guiar os convidados sem confusao")

    sinalizacao = [
        "Placas de entrada e saida do evento",
        "Indicacao de estacionamento e valet",
        "Ponto exclusivo para Uber / Taxi",
        "Setas de direcionamento no percurso",
        "Identificacao de camarins e areas restritas",
        "Sinalizacao de emergencia e saidas de incendio",
        "Banner ou totem de boas-vindas na entrada",
        "QR Code com mapa do local no convite digital",
    ]

    check_key_sin = "checks_sinalizacao"
    if check_key_sin not in st.session_state:
        st.session_state[check_key_sin] = [False] * len(sinalizacao)

    concluidos_sin = 0
    col1_s, col2_s = st.columns(2)
    for i, item in enumerate(sinalizacao):
        col = col1_s if i % 2 == 0 else col2_s
        checked = col.checkbox(item, value=st.session_state[check_key_sin][i], key=f"chk_sin_{i}")
        st.session_state[check_key_sin][i] = checked
        if checked:
            concluidos_sin += 1

    progresso_sin = concluidos_sin / len(sinalizacao)
    st.progress(progresso_sin, text=f"Sinalização: {concluidos_sin}/{len(sinalizacao)} itens ({int(progresso_sin*100)}%)")

    if st.button("💬 Pedir ajuda com sinalização do evento", use_container_width=True, key="btn_sinalizacao"):
        pendentes_sin = [sinalizacao[i] for i, c in enumerate(st.session_state[check_key_sin]) if not c]
        msg = f"Preciso de ajuda para organizar a sinalizacao do evento. Ainda falta: {', '.join(pendentes_sin)}. Como resolver?"
        st.session_state.messages.append({"role": "user", "content": msg})
        st.rerun()

# ── TAB: FOTO & VÍDEO ─────────────────────────────────────────────────────────
with tab_foto:
    st.markdown("### 📸 Foto & Vídeo")
    st.caption("Planejamento completo de cobertura audiovisual para o seu evento")

    # ── Calculadora de cobertura ───────────────────────────────────────────────
    st.markdown("#### 🎬 Monte sua Cobertura")

    col_a, col_b = st.columns(2)
    with col_a:
        tipo_ev_foto = st.selectbox("Tipo de evento", ["Casamento / Formatura", "Corporativo", "Festa / Aniversario", "VIP / Exclusivo", "Hackathon / Palestra"], key="foto_tipo")
        duracao_foto = st.slider("Duração do evento (horas)", 2, 12, 6, key="foto_dur")
    with col_b:
        num_conv_foto = st.number_input("Numero de convidados", min_value=10, max_value=3000, value=150, step=10, key="foto_conv")
        ambientes = st.number_input("Ambientes / palcos simultaneos", min_value=1, max_value=10, value=1, key="foto_amb")

    # Recomendacoes por tipo
    rec_foto = {
        "Casamento / Formatura":  {"fotos": 2, "video": True, "drone": True,  "live": False, "cobertura": "12-14h"},
        "Corporativo":            {"fotos": 1, "video": True, "drone": False, "live": True,  "cobertura": "8-10h"},
        "Festa / Aniversario":    {"fotos": 1, "video": True, "drone": False, "live": False, "cobertura": "6-8h"},
        "VIP / Exclusivo":        {"fotos": 2, "video": True, "drone": True,  "live": True,  "cobertura": "10-12h"},
        "Hackathon / Palestra":   {"fotos": 1, "video": True, "drone": False, "live": True,  "cobertura": "8-10h"},
    }
    r = rec_foto[tipo_ev_foto]
    total_fotos_prof = r["fotos"] + (ambientes - 1)

    st.markdown("---")
    st.markdown("**📋 Recomendação para seu evento:**")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("📷 Fotógrafos", total_fotos_prof)
    c2.metric("🎥 Cinegrafista", "Sim" if r["video"] else "Opcional")
    c3.metric("🚁 Drone", "Sim" if r["drone"] else "Opcional")
    c4.metric("📡 Live Stream", "Sim" if r["live"] else "Opcional")
    c5.metric("⏱️ Cobertura", r["cobertura"])

    if st.button("💬 Montar briefing de foto e vídeo", use_container_width=True, key="btn_briefing_foto"):
        extras = []
        if r["drone"]: extras.append("drone")
        if r["live"]: extras.append("transmissao ao vivo")
        msg = f"Preciso montar o briefing de foto e video para um evento {tipo_ev_foto} com {num_conv_foto} convidados, {duracao_foto}h de duracao e {ambientes} ambiente(s). Recursos desejados: {', '.join(extras) if extras else 'padrao'}. Pode me ajudar?"
        st.session_state.messages.append({"role": "user", "content": msg})
        st.rerun()

    st.divider()

    # ── Modalidades de cobertura ───────────────────────────────────────────────
    st.markdown("#### 📷 Modalidades de Cobertura")

    modalidades_foto = [
        {
            "nome": "Fotografia Profissional",
            "descricao": "Cobertura completa com fotografo dedicado, equipamento profissional e edicao das melhores fotos.",
            "quando": "Todo tipo de evento",
            "dica": "Solicite portfolio e contrato com prazo de entrega. Media: 500-800 fotos editadas por evento.",
            "img": "https://images.unsplash.com/photo-1452587925148-ce544e77e70d?w=400&h=220&fit=crop",
        },
        {
            "nome": "Filmagem Cinematográfica",
            "descricao": "Video profissional com edicao, trilha sonora e corte cinematografico. Registro definitivo do evento.",
            "quando": "Casamentos, formaturas, eventos VIP",
            "dica": "Defina o estilo: reportagem (mais natural) ou cinematografico (mais artistico). Entrega media: 15-30 dias.",
            "img": "https://images.unsplash.com/photo-1601506521793-dc748fc80b67?w=400&h=220&fit=crop",
        },
        {
            "nome": "Drone / Filmagem Aérea",
            "descricao": "Imagens aereas que mostram o evento de outro angulo. Impressionante para externas e grandes estruturas.",
            "quando": "Casamentos ao ar livre, eventos em fazendas, grandes shows",
            "dica": "Verifique a regulamentacao ANAC do local. Necessario autorizacao em areas urbanas.",
            "img": "https://images.unsplash.com/photo-1473968512647-3e447244af8f?w=400&h=220&fit=crop",
        },
        {
            "nome": "Transmissão ao Vivo",
            "descricao": "Live no YouTube, Instagram ou plataforma privada para convidados que nao puderam comparecer.",
            "quando": "Corporativos, palestras, hackathons, casamentos com familia no exterior",
            "dica": "Teste a conexao de internet do local com antecedencia. Contrate encoder dedicado para eventos grandes.",
            "img": "https://images.unsplash.com/photo-1598387993441-a364f854cfdc?w=400&h=220&fit=crop",
        },
        {
            "nome": "Cabine de Fotos / Totem",
            "descricao": "Estacao interativa onde convidados tiram fotos com props e recebem impressao na hora.",
            "quando": "Festas de aniversario, corporativos, confraternizacoes",
            "dica": "Personalize o layout com o tema do evento. Otimo para engajamento e lembranca do evento.",
            "img": "https://images.unsplash.com/photo-1516035069371-29a1b244cc32?w=400&h=220&fit=crop",
        },
        {
            "nome": "Cobertura para Redes Sociais",
            "descricao": "Profissional dedicado a criar conteudo em tempo real para Instagram, LinkedIn e TikTok do evento.",
            "quando": "Lancamentos de produtos, eventos corporativos, eventos VIP",
            "dica": "Defina hashtags, @mencoes e um kit de identidade visual para os stories antes do evento.",
            "img": "https://images.unsplash.com/photo-1611162617213-7d7a39e9b1d7?w=400&h=220&fit=crop",
        },
    ]

    for i in range(0, len(modalidades_foto), 2):
        cols = st.columns(2)
        for j, col in enumerate(cols):
            if i + j < len(modalidades_foto):
                m = modalidades_foto[i + j]
                with col:
                    try:
                        r2 = requests.get(m["img"], timeout=6)
                        if r2.status_code == 200:
                            st.image(r2.content, use_container_width=True)
                    except Exception:
                        pass
                    st.markdown(f"**{m['nome']}**")
                    st.markdown(m["descricao"])
                    st.caption(f"🎯 Quando usar: {m['quando']}")
                    st.info(f"💡 {m['dica']}")
                    if st.button(f"💬 Saiba mais sobre {m['nome']}", key=f"btn_foto_{m['nome']}", use_container_width=True):
                        msg = f"Quero contratar {m['nome']} para o meu evento. Quais os cuidados, o que pedir no contrato e qual o custo medio?"
                        st.session_state.messages.append({"role": "user", "content": msg})
                        st.rerun()
                    st.markdown("---")

    st.divider()

    # ── Checklist de briefing ──────────────────────────────────────────────────
    st.markdown("#### 📋 Checklist de Briefing Audiovisual")
    st.caption("Itens para passar ao fotografo e cinegrafista antes do evento")

    briefing_items = [
        "Enviar roteiro e cronograma do evento",
        "Definir momentos obrigatorios (entrada, brinde, bolo, etc)",
        "Passar lista de fotos especiais solicitadas",
        "Confirmar horario de chegada da equipe (1-2h antes)",
        "Informar restricoes de acesso e areas proibidas",
        "Definir formato de entrega (galeria online, pendrive, HD)",
        "Alinhar prazo de entrega das fotos editadas",
        "Confirmar direitos de uso das imagens",
        "Testar equipamentos no local com antecedencia",
        "Definir contato responsavel no dia do evento",
    ]

    check_key_bf = "checks_briefing"
    if check_key_bf not in st.session_state:
        st.session_state[check_key_bf] = [False] * len(briefing_items)

    col1_b, col2_b = st.columns(2)
    concluidos_bf = 0
    for i, item in enumerate(briefing_items):
        col = col1_b if i % 2 == 0 else col2_b
        checked = col.checkbox(item, value=st.session_state[check_key_bf][i], key=f"chk_bf_{i}")
        st.session_state[check_key_bf][i] = checked
        if checked:
            concluidos_bf += 1

    prog_bf = concluidos_bf / len(briefing_items)
    st.progress(prog_bf, text=f"Briefing: {concluidos_bf}/{len(briefing_items)} itens ({int(prog_bf*100)}%)")

    if st.button("💬 Pedir ajuda para montar o briefing completo", use_container_width=True, key="btn_briefing_check"):
        pendentes_bf = [briefing_items[i] for i, c in enumerate(st.session_state[check_key_bf]) if not c]
        msg = f"Preciso montar o briefing audiovisual do meu evento. Ainda falta definir: {', '.join(pendentes_bf)}. Pode me orientar?"
        st.session_state.messages.append({"role": "user", "content": msg})
        st.rerun()

# ── TAB: CALCULADORA DE ORÇAMENTO ─────────────────────────────────────────────
with tab_orcamento:
    st.markdown("### 💰 Calculadora de Orçamento")
    st.caption("Estime o custo do seu evento por categoria e receba uma proposta detalhada")

    # ── Parâmetros gerais ──────────────────────────────────────────────────────
    st.markdown("#### ⚙️ Parâmetros do Evento")
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        tipo_orc = st.selectbox("Tipo de evento", [
            "Casamento / Formatura", "Corporativo", "Festa / Aniversario",
            "VIP / Exclusivo", "Hackathon / Palestra"
        ], key="orc_tipo")
        num_orc = st.number_input("Numero de convidados", min_value=10, max_value=3000, value=100, step=10, key="orc_num")
    with col_b:
        nivel = st.selectbox("Nivel do evento", ["Simples", "Intermediario", "Premium", "Luxo"], key="orc_nivel")
        duracao_orc = st.slider("Duracao (horas)", 2, 16, 6, key="orc_dur")
    with col_c:
        cidade = st.selectbox("Cidade / regiao", ["Sao Paulo", "Rio de Janeiro", "Outras capitais", "Interior"], key="orc_cidade")
        data_orc = st.selectbox("Periodo do evento", ["Semana (seg-qui)", "Final de semana", "Feriado"], key="orc_data")

    # Multiplicadores
    mult_nivel   = {"Simples": 1.0, "Intermediario": 1.6, "Premium": 2.5, "Luxo": 4.0}[nivel]
    mult_cidade  = {"Sao Paulo": 1.3, "Rio de Janeiro": 1.2, "Outras capitais": 1.1, "Interior": 1.0}[cidade]
    mult_data    = {"Semana (seg-qui)": 0.85, "Final de semana": 1.0, "Feriado": 1.2}[data_orc]
    mult_tipo    = {"Casamento / Formatura": 1.4, "Corporativo": 1.2, "Festa / Aniversario": 1.0, "VIP / Exclusivo": 2.0, "Hackathon / Palestra": 0.9}[tipo_orc]

    M = mult_nivel * mult_cidade * mult_data * mult_tipo

    # Custos base por pessoa (R$)
    base = {
        "🍽️ Buffet & Gastronomia":    150,
        "🎵 Som & DJ / Banda":         40,
        "💡 Iluminacao Cenica":        30,
        "🏗️ Espaco & Locacao":         80,
        "📸 Foto & Video":             35,
        "🌸 Decoracao & Floricultura": 60,
        "🤵 Equipe (garcons/staff)":   25,
        "🚗 Logistica & Transporte":   20,
        "📋 Assessoria & Producao":    30,
        "⚡ Gerador & Infra Eletrica": 15,
    }

    st.divider()
    st.markdown("#### 🎛️ Ajuste por Categoria")
    st.caption("Ative ou desative categorias e ajuste o percentual conforme sua necessidade")

    categorias_orc = {}
    col1_orc, col2_orc = st.columns(2)
    items_list = list(base.items())

    total_orc = 0
    dados_grafico_labels = []
    dados_grafico_vals = []

    for idx_item, (cat, val_base) in enumerate(items_list):
        col = col1_orc if idx_item % 2 == 0 else col2_orc
        with col:
            ativo = st.checkbox(cat, value=True, key=f"orc_ck_{cat}")
            if ativo:
                pct = st.slider(f"Ajuste % — {cat}", 50, 200, 100, step=10, key=f"orc_sl_{cat}", label_visibility="collapsed")
                valor = val_base * num_orc * M * (pct / 100)
                st.caption(f"Estimativa: **R$ {valor:,.0f}**".replace(",", "."))
                categorias_orc[cat] = valor
                total_orc += valor
                dados_grafico_labels.append(cat.split(" ")[0] + " " + " ".join(cat.split(" ")[1:3]))
                dados_grafico_vals.append(round(valor))

    st.divider()

    # ── Resumo ─────────────────────────────────────────────────────────────────
    st.markdown("#### 📊 Resumo do Orçamento")

    col_res1, col_res2, col_res3, col_res4 = st.columns(4)
    col_res1.metric("💰 Total estimado", f"R$ {total_orc:,.0f}".replace(",", "."))
    col_res2.metric("👤 Custo por pessoa", f"R$ {total_orc/num_orc:,.0f}".replace(",", ".") if num_orc else "—")
    col_res3.metric("📅 Nivel", nivel)
    col_res4.metric("👥 Convidados", num_orc)

    # Grafico de barras com st.bar_chart
    if dados_grafico_labels:
        df_orc = pd.DataFrame({
            "Categoria": dados_grafico_labels,
            "Valor (R$)": dados_grafico_vals
        }).set_index("Categoria")
        st.bar_chart(df_orc, height=300)

    # Alerta de margem de seguranca
    reserva = total_orc * 0.10
    st.warning(f"⚠️ Recomendamos reservar **R$ {reserva:,.0f}** (10%) como margem de segurança para imprevistos.".replace(",", "."))

    if st.button("💬 Pedir proposta detalhada com base neste orçamento", use_container_width=True, key="btn_proposta"):
        itens_str = ", ".join([f"{k}: R$ {v:,.0f}".replace(",", ".") for k, v in categorias_orc.items()])
        msg = (
            f"Com base no orcamento estimado para um evento {tipo_orc}, nivel {nivel}, "
            f"{num_orc} convidados, {duracao_orc}h em {cidade}: {itens_str}. "
            f"Total estimado: R$ {total_orc:,.0f}. Pode me ajudar a refinir essa proposta e identificar onde posso economizar?".replace(",", ".")
        )
        st.session_state.messages.append({"role": "user", "content": msg})
        st.rerun()

    st.divider()

    # ── Comparativo de pacotes ─────────────────────────────────────────────────
    st.markdown("#### 📦 Pacotes Spotlight Eventos")
    st.caption("Compare os pacotes pre-definidos para facilitar a contratacao")

    pacotes = [
        {
            "nome": "Essencial",
            "preco_base": "A partir de R$ 8.000",
            "cor": "🟢",
            "inclui": ["Assessoria parcial", "Buffet simples", "Som basico", "1 Fotografo", "Decoracao simples"],
            "ideal": "Eventos de ate 80 pessoas",
        },
        {
            "nome": "Profissional",
            "preco_base": "A partir de R$ 18.000",
            "cor": "🔵",
            "inclui": ["Assessoria completa", "Buffet completo", "Som + iluminacao", "Foto + video", "Decoracao tematica", "Logistica basica"],
            "ideal": "Eventos de 80 a 200 pessoas",
        },
        {
            "nome": "Premium",
            "preco_base": "A partir de R$ 38.000",
            "cor": "🟣",
            "inclui": ["Producao completa", "Buffet gourmet", "Som + iluminacao cenica", "Foto + video + drone", "Decoracao exclusiva", "Valet + transfer VIP", "Live streaming"],
            "ideal": "Eventos de 200 a 500 pessoas",
        },
        {
            "nome": "Luxo VIP",
            "preco_base": "Sob consulta",
            "cor": "🟡",
            "inclui": ["Experiencia personalizada", "Chef exclusivo", "Producao audiovisual completa", "Estrutura sob medida", "Seguranca privativa", "Tudo incluso"],
            "ideal": "Eventos VIP acima de 500 pessoas",
        },
    ]

    cols_pac = st.columns(4)
    for i, pac in enumerate(pacotes):
        with cols_pac[i]:
            st.markdown(f"**{pac['cor']} {pac['nome']}**")
            st.markdown(f"*{pac['preco_base']}*")
            st.caption(f"🎯 {pac['ideal']}")
            for item in pac["inclui"]:
                st.markdown(f"✅ {item}")
            if st.button(f"💬 Contratar {pac['nome']}", key=f"btn_pac_{pac['nome']}", use_container_width=True):
                msg = f"Tenho interesse no pacote {pac['nome']} da Spotlight Eventos. Pode me dar mais detalhes e iniciar o processo de contratacao?"
                st.session_state.messages.append({"role": "user", "content": msg})
                st.rerun()

# ── TAB: DASHBOARD DE MÉTRICAS ────────────────────────────────────────────────
with tab_dash:
    import random

    st.markdown("### 📊 Dashboard de Métricas")
    st.caption("Visão geral do desempenho operacional da Spotlight Eventos")

    # ── KPIs principais ────────────────────────────────────────────────────────
    st.markdown("#### 🏆 Indicadores Gerais")

    total_eventos  = len(st.session_state.eventos_cadastrados)
    confirmados    = sum(1 for e in st.session_state.eventos_cadastrados if e["status"] == "confirmed")
    planejamento   = sum(1 for e in st.session_state.eventos_cadastrados if e["status"] == "pending")
    vips           = sum(1 for e in st.session_state.eventos_cadastrados if e["status"] == "vip")
    total_conv_all = sum(e["convidados"] for e in st.session_state.eventos_cadastrados)
    taxa_conv      = round((confirmados / total_eventos * 100) if total_eventos else 0, 1)

    k1, k2, k3, k4, k5, k6 = st.columns(6)
    k1.metric("📅 Total de eventos", total_eventos)
    k2.metric("✅ Confirmados", confirmados, f"{taxa_conv}% do total")
    k3.metric("🟡 Em planejamento", planejamento)
    k4.metric("⭐ VIP", vips)
    k5.metric("👥 Total convidados", f"{total_conv_all:,}".replace(",", "."))
    k6.metric("📈 Taxa confirmação", f"{taxa_conv}%", "meta: 80%")

    st.divider()

    # ── Gráfico: eventos por tipo ──────────────────────────────────────────────
    col_g1, col_g2 = st.columns(2)

    with col_g1:
        st.markdown("**📂 Eventos por tipo**")
        tipos_count = {}
        tipo_emoji = {
            "casamento": "💍 Casamento",
            "hackathon": "💻 Hackathon",
            "vip":       "⭐ VIP",
            "corporativo": "💼 Corporativo",
            "aniversario": "🎂 Aniversário",
            "palestra":  "🎤 Palestra",
        }
        for e in st.session_state.eventos_cadastrados:
            label = tipo_emoji.get(e["tipo"], e["tipo"].title())
            tipos_count[label] = tipos_count.get(label, 0) + 1

        # Adiciona dados simulados para enriquecer o dashboard
        simulados = {"💍 Casamento": 4, "💼 Corporativo": 3, "🎂 Aniversário": 2, "🎤 Palestra": 2, "💻 Hackathon": 1}
        for k, v in simulados.items():
            tipos_count[k] = tipos_count.get(k, 0) + v

        df_tipos = pd.DataFrame({"Quantidade": tipos_count}).sort_values("Quantidade", ascending=False)
        st.bar_chart(df_tipos, height=250)

    with col_g2:
        st.markdown("**📅 Eventos por mês (últimos 6 meses)**")
        meses = ["Dez", "Jan", "Fev", "Mar", "Abr", "Mai"]
        vals_mes = [3, 5, 4, 7, 6, total_eventos + 2]
        df_meses = pd.DataFrame({"Eventos": vals_mes}, index=meses)
        st.bar_chart(df_meses, height=250)

    st.divider()

    # ── RSVP por evento ────────────────────────────────────────────────────────
    st.markdown("#### 👥 RSVP por Evento")

    rsvp_data = []
    for e in st.session_state.eventos_cadastrados:
        total_c = e["convidados"]
        conf    = random.randint(int(total_c * 0.55), int(total_c * 0.85))
        pend    = random.randint(int(total_c * 0.05), int(total_c * 0.20))
        recus   = total_c - conf - pend
        rsvp_data.append({
            "Evento":       e["nome"],
            "Total":        total_c,
            "✅ Confirmados": conf,
            "⏳ Pendentes":  pend,
            "❌ Recusados":  max(recus, 0),
            "Taxa (%)":     f"{round(conf/total_c*100)}%",
        })

    df_rsvp = pd.DataFrame(rsvp_data).set_index("Evento")
    st.dataframe(df_rsvp, use_container_width=True)

    if st.button("💬 Pedir relatório completo de RSVP", use_container_width=True, key="btn_rsvp_relatorio"):
        msg = "Preciso de um relatorio completo de RSVP dos eventos cadastrados. Quais acoes tomar para aumentar a taxa de confirmacao?"
        st.session_state.messages.append({"role": "user", "content": msg})
        st.rerun()

    st.divider()

    # ── Receita estimada ───────────────────────────────────────────────────────
    col_r1, col_r2 = st.columns(2)

    with col_r1:
        st.markdown("**💰 Receita estimada por mês (R$)**")
        receitas = [42000, 68000, 55000, 91000, 78000, 105000]
        df_rec = pd.DataFrame({"Receita (R$)": receitas}, index=meses)
        st.line_chart(df_rec, height=220)

    with col_r2:
        st.markdown("**📦 Pacotes mais contratados**")
        pacotes_count = {
            "Profissional": 7,
            "Premium":      5,
            "Essencial":    4,
            "Luxo VIP":     2,
        }
        df_pac = pd.DataFrame({"Contratos": pacotes_count})
        st.bar_chart(df_pac, height=220)

    st.divider()

    # ── Alertas e pendências ───────────────────────────────────────────────────
    st.markdown("#### 🔔 Alertas & Pendências")

    alertas = [
        ("🔴", "Hackathon TechCorp 2025", "RSVP abaixo de 60% — enviar lembrete urgente"),
        ("🟡", "Casamento Silva & Pereira", "Contrato do buffet vence em 5 dias"),
        ("🟡", "Jantar VIP Investidores", "Confirmar menu com o chef até sexta-feira"),
        ("🟢", "Todos os eventos", "Pagamentos do mes em dia"),
    ]

    for cor, evento, msg_alerta in alertas:
        col_al1, col_al2, col_al3 = st.columns([0.5, 2, 4])
        col_al1.markdown(f"### {cor}")
        col_al2.markdown(f"**{evento}**")
        col_al3.markdown(msg_alerta)

    if st.button("💬 Analisar pendências com o agente", use_container_width=True, key="btn_alertas"):
        msg = "Quais sao as principais pendencias dos meus eventos agora? Me ajude a priorizar as acoes mais urgentes."
        st.session_state.messages.append({"role": "user", "content": msg})
        st.rerun()

    st.divider()

    # ── Satisfação (NPS simulado) ──────────────────────────────────────────────
    st.markdown("#### ⭐ Satisfação dos Clientes (NPS)")
    col_n1, col_n2, col_n3, col_n4 = st.columns(4)
    col_n1.metric("NPS Geral", "78", "+5 vs mês anterior")
    col_n2.metric("😍 Promotores", "62%", "+3%")
    col_n3.metric("😐 Neutros", "24%", "-1%")
    col_n4.metric("😠 Detratores", "14%", "-2%")

    nps_meses_vals = [65, 70, 68, 74, 72, 78]
    df_nps = pd.DataFrame({"NPS": nps_meses_vals}, index=meses)
    st.line_chart(df_nps, height=180)
    st.caption("Dados parcialmente simulados para demonstracao. Integre com seu CRM para dados reais.")

# ── TAB: CONFIRMAÇÕES & E-MAIL ────────────────────────────────────────────────
with tab_email:
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    st.markdown("### 📧 Confirmações & Envio de E-mail")
    st.caption("Gerencie RSVPs e envie confirmações automáticas personalizadas aos convidados")

    # ── Configuração SMTP ──────────────────────────────────────────────────────
    with st.expander("⚙️ Configurar servidor de e-mail (SMTP)", expanded=False):
        st.info("Configure uma conta Gmail com senha de app ou use outro servidor SMTP. [Como criar senha de app Gmail](https://support.google.com/accounts/answer/185833)")
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            smtp_host  = st.text_input("Servidor SMTP", value="smtp.gmail.com", key="smtp_host")
            smtp_user  = st.text_input("E-mail remetente", placeholder="seuemail@gmail.com", key="smtp_user")
        with col_s2:
            smtp_port  = st.number_input("Porta", value=587, key="smtp_port")
            smtp_pass  = st.text_input("Senha de app", type="password", key="smtp_pass")

        if st.button("🔌 Testar conexão SMTP", key="btn_smtp_test"):
            if smtp_user and smtp_pass:
                try:
                    server = smtplib.SMTP(smtp_host, smtp_port, timeout=5)
                    server.starttls()
                    server.login(smtp_user, smtp_pass)
                    server.quit()
                    st.success("✅ Conexão bem-sucedida! E-mails prontos para envio.")
                except Exception as e:
                    st.error(f"❌ Erro na conexão: {e}")
            else:
                st.warning("Preencha e-mail e senha antes de testar.")

    st.divider()

    # ── Registro de RSVP ──────────────────────────────────────────────────────
    st.markdown("#### ✅ Registrar Confirmação de Presença")

    if "lista_rsvp" not in st.session_state:
        st.session_state.lista_rsvp = [
            {"nome": "Ana Lima",       "email": "ana@exemplo.com",    "evento": "Casamento Silva & Pereira", "acomp": 1, "restricao": "Nenhuma",    "status": "Confirmado"},
            {"nome": "Carlos Mendes",  "email": "carlos@exemplo.com", "evento": "Hackathon TechCorp 2025",  "acomp": 0, "restricao": "Vegetariano","status": "Confirmado"},
            {"nome": "Beatriz Costa",  "email": "bea@exemplo.com",    "evento": "Jantar VIP Investidores",  "acomp": 1, "restricao": "Sem gluten", "status": "Pendente"},
        ]

    col_f1, col_f2 = st.columns(2)
    with col_f1:
        nome_conv   = st.text_input("Nome do convidado", key="rsvp_nome")
        email_conv  = st.text_input("E-mail do convidado", key="rsvp_email")
        evento_sel  = st.selectbox("Evento", [e["nome"] for e in st.session_state.eventos_cadastrados], key="rsvp_evento")
    with col_f2:
        acomp_conv  = st.number_input("Acompanhantes", min_value=0, max_value=10, value=0, key="rsvp_acomp")
        restricao   = st.text_input("Restricao alimentar (opcional)", key="rsvp_rest")
        status_conv = st.selectbox("Status", ["Confirmado", "Pendente", "Recusado"], key="rsvp_status")

    col_btn1, col_btn2 = st.columns(2)

    with col_btn1:
        if st.button("➕ Registrar RSVP", use_container_width=True, key="btn_add_rsvp"):
            if nome_conv and email_conv:
                st.session_state.lista_rsvp.append({
                    "nome": nome_conv, "email": email_conv,
                    "evento": evento_sel, "acomp": acomp_conv,
                    "restricao": restricao or "Nenhuma", "status": status_conv,
                })
                st.success(f"✅ {nome_conv} registrado com sucesso!")
                st.rerun()
            else:
                st.warning("Preencha nome e e-mail do convidado.")

    with col_btn2:
        if st.button("📧 Enviar confirmação por e-mail", use_container_width=True, key="btn_send_email"):
            if not (smtp_user and smtp_pass and nome_conv and email_conv):
                st.warning("Configure o SMTP e preencha os dados do convidado antes de enviar.")
            else:
                ev_info = next((e for e in st.session_state.eventos_cadastrados if e["nome"] == evento_sel), {})
                html_body = f"""
                <html><body style="font-family:Arial,sans-serif;color:#333;max-width:600px;margin:auto">
                <div style="background:#534AB7;padding:24px;text-align:center;border-radius:8px 8px 0 0">
                  <h1 style="color:#fff;margin:0">🎉 Spotlight Eventos</h1>
                </div>
                <div style="padding:24px;border:1px solid #eee;border-top:none;border-radius:0 0 8px 8px">
                  <h2>Olá, {nome_conv}!</h2>
                  <p>Sua presença no evento <strong>{evento_sel}</strong> foi <strong style="color:#534AB7">{status_conv.lower()}</strong>.</p>
                  <table style="width:100%;border-collapse:collapse;margin:16px 0">
                    <tr style="background:#f5f5f5"><td style="padding:8px"><strong>📅 Data</strong></td><td style="padding:8px">{ev_info.get('data','—')}</td></tr>
                    <tr><td style="padding:8px"><strong>📍 Local</strong></td><td style="padding:8px">{ev_info.get('local','—')}</td></tr>
                    <tr style="background:#f5f5f5"><td style="padding:8px"><strong>👥 Acompanhantes</strong></td><td style="padding:8px">{acomp_conv}</td></tr>
                    <tr><td style="padding:8px"><strong>🥗 Restricao alimentar</strong></td><td style="padding:8px">{restricao or 'Nenhuma'}</td></tr>
                  </table>
                  <p>Em caso de duvidas, entre em contato com nossa equipe.</p>
                  <p style="color:#888;font-size:12px;margin-top:24px">Spotlight Eventos · spotlightia@eventos.com.br</p>
                </div></body></html>
                """
                try:
                    msg_email = MIMEMultipart("alternative")
                    msg_email["Subject"] = f"Confirmacao de presenca — {evento_sel}"
                    msg_email["From"]    = smtp_user
                    msg_email["To"]      = email_conv
                    msg_email.attach(MIMEText(html_body, "html"))
                    server = smtplib.SMTP(smtp_host, smtp_port, timeout=10)
                    server.starttls()
                    server.login(smtp_user, smtp_pass)
                    server.sendmail(smtp_user, email_conv, msg_email.as_string())
                    server.quit()
                    st.success(f"📧 E-mail enviado para {email_conv} com sucesso!")
                except Exception as e:
                    st.error(f"❌ Erro ao enviar: {e}")

    st.divider()

    # ── Lista de RSVPs ─────────────────────────────────────────────────────────
    st.markdown("#### 📋 Lista de Convidados")

    filtro_evento = st.selectbox(
        "Filtrar por evento",
        ["Todos"] + [e["nome"] for e in st.session_state.eventos_cadastrados],
        key="filtro_rsvp"
    )
    filtro_status = st.selectbox("Filtrar por status", ["Todos", "Confirmado", "Pendente", "Recusado"], key="filtro_status")

    lista_filtrada = st.session_state.lista_rsvp
    if filtro_evento != "Todos":
        lista_filtrada = [r for r in lista_filtrada if r["evento"] == filtro_evento]
    if filtro_status != "Todos":
        lista_filtrada = [r for r in lista_filtrada if r["status"] == filtro_status]

    if lista_filtrada:
        df_rsvp_list = pd.DataFrame(lista_filtrada)
        df_rsvp_list.columns = ["Nome", "E-mail", "Evento", "Acompanhantes", "Restrição", "Status"]
        st.dataframe(df_rsvp_list, use_container_width=True, hide_index=True)

        # Resumo
        total_r  = len(lista_filtrada)
        conf_r   = sum(1 for r in lista_filtrada if r["status"] == "Confirmado")
        pend_r   = sum(1 for r in lista_filtrada if r["status"] == "Pendente")
        total_ac = sum(r["acomp"] for r in lista_filtrada if r["status"] == "Confirmado")

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total", total_r)
        c2.metric("✅ Confirmados", conf_r)
        c3.metric("⏳ Pendentes", pend_r)
        c4.metric("👥 Total c/ acomp.", conf_r + total_ac)

        # Envio em massa para pendentes
        st.divider()
        pendentes_lista = [r for r in lista_filtrada if r["status"] == "Pendente"]
        if pendentes_lista:
            st.markdown(f"**⏳ {len(pendentes_lista)} convidado(s) pendente(s)**")
            if st.button(f"📧 Enviar lembrete para todos os pendentes", use_container_width=True, key="btn_lembrete_massa"):
                if not (smtp_user and smtp_pass):
                    st.warning("Configure o SMTP primeiro.")
                else:
                    enviados = 0
                    for conv in pendentes_lista:
                        try:
                            lembrete = MIMEMultipart("alternative")
                            lembrete["Subject"] = f"Lembrete: confirme sua presenca — {conv['evento']}"
                            lembrete["From"]    = smtp_user
                            lembrete["To"]      = conv["email"]
                            corpo = f"<html><body><p>Ola, <strong>{conv['nome']}</strong>!<br>Ainda nao recebemos sua confirmacao para o evento <strong>{conv['evento']}</strong>. Por favor confirme o quanto antes.<br><br>Equipe Spotlight Eventos</p></body></html>"
                            lembrete.attach(MIMEText(corpo, "html"))
                            sv = smtplib.SMTP(smtp_host, smtp_port, timeout=10)
                            sv.starttls()
                            sv.login(smtp_user, smtp_pass)
                            sv.sendmail(smtp_user, conv["email"], lembrete.as_string())
                            sv.quit()
                            enviados += 1
                        except Exception:
                            pass
                    st.success(f"📧 {enviados}/{len(pendentes_lista)} lembretes enviados!")
    else:
        st.info("Nenhum convidado encontrado com os filtros selecionados.")

    st.divider()

    # ── Preview do e-mail ──────────────────────────────────────────────────────
    st.markdown("#### 👁️ Preview do E-mail de Confirmação")
    st.caption("Veja como o e-mail sera exibido para o convidado")
    st.markdown("""
<div style="font-family:Arial,sans-serif;color:#333;max-width:540px;border:1px solid #ddd;border-radius:8px;overflow:hidden">
  <div style="background:#534AB7;padding:20px;text-align:center">
    <h2 style="color:#fff;margin:0">🎉 Spotlight Eventos</h2>
  </div>
  <div style="padding:20px">
    <h3>Olá, [Nome do Convidado]!</h3>
    <p>Sua presença no evento <strong>[Nome do Evento]</strong> foi <strong style="color:#534AB7">confirmada</strong>.</p>
    <table style="width:100%;border-collapse:collapse">
      <tr style="background:#f5f5f5"><td style="padding:8px"><strong>📅 Data</strong></td><td style="padding:8px">[Data]</td></tr>
      <tr><td style="padding:8px"><strong>📍 Local</strong></td><td style="padding:8px">[Local]</td></tr>
      <tr style="background:#f5f5f5"><td style="padding:8px"><strong>👥 Acompanhantes</strong></td><td style="padding:8px">[N]</td></tr>
      <tr><td style="padding:8px"><strong>🥗 Restrição</strong></td><td style="padding:8px">[Restrição]</td></tr>
    </table>
    <p>Em caso de dúvidas, entre em contato com nossa equipe.</p>
    <p style="color:#aaa;font-size:11px">Spotlight Eventos · spotlightia@eventos.com.br</p>
  </div>
</div>
""", unsafe_allow_html=True)

# ── TAB: RSVP PÚBLICO ─────────────────────────────────────────────────────────
with tab_rsvp:
    import hashlib
    import urllib.parse

    st.markdown("### 🔗 Link de RSVP Público")
    st.caption("Gere links únicos por evento para que convidados confirmem presença sozinhos")

    # ── Gerador de link ────────────────────────────────────────────────────────
    st.markdown("#### 🔗 Gerar Link do Evento")

    col_a, col_b = st.columns(2)
    with col_a:
        evento_link = st.selectbox(
            "Selecione o evento",
            [e["nome"] for e in st.session_state.eventos_cadastrados],
            key="rsvp_pub_evento"
        )
    with col_b:
        base_url = st.text_input(
            "URL base do seu app",
            value="https://spotlightia.streamlit.app",
            key="rsvp_base_url",
            help="Coloque aqui a URL onde seu app está publicado"
        )

    ev_sel = next((e for e in st.session_state.eventos_cadastrados if e["nome"] == evento_link), {})
    token  = hashlib.md5(evento_link.encode()).hexdigest()[:8]
    params = urllib.parse.urlencode({"evento": evento_link, "token": token})
    link_gerado = f"{base_url}/?{params}"

    st.markdown("---")
    st.markdown("**🔗 Link gerado:**")
    st.code(link_gerado, language=None)

    col_c1, col_c2, col_c3 = st.columns(3)
    col_c1.metric("🎫 Evento", ev_sel.get("nome", "—")[:25] + "...")
    col_c2.metric("📅 Data", ev_sel.get("data", "—"))
    col_c3.metric("👥 Vagas", ev_sel.get("convidados", "—"))

    # QR Code textual (representação simples)
    st.markdown("**📱 QR Code do link:**")
    st.info(f"Instale `qrcode` e `Pillow` para gerar QR Codes reais:\n```\npip install qrcode pillow\n```\nLink para gerar online: https://qr.io/?url={urllib.parse.quote(link_gerado)}")

    # Botão copiar via st.code já permite copiar
    if st.button("💬 Pedir texto de convite com este link", key="btn_texto_convite", use_container_width=True):
        msg = f"Gere um texto de convite elegante para o evento '{evento_link}' que inclua o link de confirmacao de presenca: {link_gerado}"
        st.session_state.messages.append({"role": "user", "content": msg})
        st.rerun()

    st.divider()

    # ── Simulação da página pública de RSVP ───────────────────────────────────
    st.markdown("#### 👁️ Preview da Página Pública de RSVP")
    st.caption("É assim que o convidado verá a página ao abrir o link")

    ev_preview = ev_sel
    st.markdown(f"""
<div style="max-width:520px;margin:auto;font-family:Arial,sans-serif;border:1px solid #ddd;border-radius:12px;overflow:hidden">
  <div style="background:linear-gradient(135deg,#534AB7,#7B75D8);padding:28px;text-align:center">
    <div style="font-size:36px">🎉</div>
    <h2 style="color:#fff;margin:8px 0">{ev_preview.get('nome','Nome do Evento')}</h2>
    <p style="color:#EEEDFE;margin:0">Você foi convidado!</p>
  </div>
  <div style="padding:24px;background:#fff">
    <table style="width:100%;border-collapse:collapse;margin-bottom:16px">
      <tr><td style="padding:8px 0;color:#888">📅 Data</td><td style="padding:8px 0;font-weight:600">{ev_preview.get('data','—')}</td></tr>
      <tr><td style="padding:8px 0;color:#888">📍 Local</td><td style="padding:8px 0;font-weight:600">{ev_preview.get('local','—')}</td></tr>
      <tr><td style="padding:8px 0;color:#888">👥 Capacidade</td><td style="padding:8px 0;font-weight:600">{ev_preview.get('convidados','—')} pessoas</td></tr>
    </table>
    <hr style="border:none;border-top:1px solid #eee;margin:16px 0"/>
    <p style="color:#555;margin-bottom:12px">Confirme sua presença preenchendo os campos abaixo:</p>
    <div style="background:#f9f9f9;padding:12px;border-radius:8px;margin-bottom:8px">
      <div style="color:#888;font-size:12px;margin-bottom:4px">Nome completo</div>
      <div style="border:1px solid #ddd;border-radius:4px;padding:8px;background:#fff;color:#ccc">Seu nome aqui</div>
    </div>
    <div style="background:#f9f9f9;padding:12px;border-radius:8px;margin-bottom:8px">
      <div style="color:#888;font-size:12px;margin-bottom:4px">E-mail</div>
      <div style="border:1px solid #ddd;border-radius:4px;padding:8px;background:#fff;color:#ccc">seu@email.com</div>
    </div>
    <div style="background:#f9f9f9;padding:12px;border-radius:8px;margin-bottom:16px">
      <div style="color:#888;font-size:12px;margin-bottom:4px">Acompanhantes</div>
      <div style="border:1px solid #ddd;border-radius:4px;padding:8px;background:#fff;color:#ccc">0</div>
    </div>
    <div style="background:#534AB7;color:#fff;text-align:center;padding:12px;border-radius:8px;font-weight:600;cursor:pointer">
      ✅ Confirmar Presença
    </div>
    <p style="text-align:center;color:#aaa;font-size:11px;margin-top:12px">Spotlight Eventos · spotlightia@eventos.com.br</p>
  </div>
</div>
""", unsafe_allow_html=True)

    st.divider()

    # ── Formulário RSVP funcional embutido ────────────────────────────────────
    st.markdown("#### ✅ Formulário RSVP Funcional")
    st.caption("Versão funcional da página — compartilhe esta aba ou publique o app para convidados acessarem")

    with st.form("form_rsvp_publico", clear_on_submit=True):
        st.markdown(f"**Evento:** {evento_link}")
        nome_pub    = st.text_input("Seu nome completo *")
        email_pub   = st.text_input("Seu e-mail *")
        acomp_pub   = st.number_input("Número de acompanhantes", min_value=0, max_value=10, value=0)
        rest_pub    = st.text_input("Restrição alimentar (opcional)")
        presenca    = st.radio("Confirma presença?", ["✅ Sim, estarei presente", "❌ Não poderei comparecer"], horizontal=True)
        submitted   = st.form_submit_button("Enviar confirmação", use_container_width=True)

        if submitted:
            if nome_pub and email_pub:
                status_pub = "Confirmado" if "Sim" in presenca else "Recusado"
                # Verifica duplicata
                ja_existe = any(
                    r["email"] == email_pub and r["evento"] == evento_link
                    for r in st.session_state.lista_rsvp
                )
                if ja_existe:
                    # Atualiza status
                    for r in st.session_state.lista_rsvp:
                        if r["email"] == email_pub and r["evento"] == evento_link:
                            r["status"] = status_pub
                            r["acomp"]  = acomp_pub
                    st.success(f"✅ {nome_pub}, sua resposta foi atualizada para **{status_pub}**!")
                else:
                    st.session_state.lista_rsvp.append({
                        "nome": nome_pub, "email": email_pub,
                        "evento": evento_link, "acomp": acomp_pub,
                        "restricao": rest_pub or "Nenhuma", "status": status_pub,
                    })
                    if DB_DISPONIVEL and st.session_state.get("tenant"):
                        db.rsvp_upsert(st.session_state.tenant, evento_link, nome_pub, email_pub, acomp_pub, rest_pub or "Nenhuma", status_pub)
                    st.success(f"🎉 Obrigado, **{nome_pub}**! Presença **{status_pub.lower()}** para {evento_link}.")
                st.balloons()
            else:
                st.warning("Preencha nome e e-mail para confirmar.")

    st.divider()

    # ── Resumo de respostas por evento ────────────────────────────────────────
    st.markdown("#### 📊 Respostas Recebidas por Evento")
    resumo_ev = {}
    for r in st.session_state.lista_rsvp:
        ev_n = r["evento"]
        if ev_n not in resumo_ev:
            resumo_ev[ev_n] = {"Confirmado": 0, "Pendente": 0, "Recusado": 0}
        resumo_ev[ev_n][r["status"]] = resumo_ev[ev_n].get(r["status"], 0) + 1

    if resumo_ev:
        df_res = pd.DataFrame(resumo_ev).T.fillna(0).astype(int)
        df_res["Total"] = df_res.sum(axis=1)
        df_res["Taxa %"] = (df_res["Confirmado"] / df_res["Total"] * 100).round(1).astype(str) + "%"
        st.dataframe(df_res, use_container_width=True)
    else:
        st.info("Nenhuma resposta registrada ainda.")

# ── TAB: CONVITE DIGITAL ──────────────────────────────────────────────────────
with tab_convite:
    import urllib.parse as _up

    st.markdown("### 📱 Convite Digital com QR Code")
    st.caption("Gere convites HTML elegantes prontos para enviar por e-mail ou WhatsApp")

    col_cv1, col_cv2 = st.columns(2)
    with col_cv1:
        ev_conv = st.selectbox("Evento", [e["nome"] for e in st.session_state.eventos_cadastrados], key="conv_ev")
        tema    = st.selectbox("Tema visual", ["Roxo elegante", "Dourado premium", "Azul corporativo", "Verde natureza", "Rosa romantico"], key="conv_tema")
        mensagem_conv = st.text_area("Mensagem personalizada", value="Sua presença é muito importante para nós. Será uma noite inesquecível!", key="conv_msg", height=80)
    with col_cv2:
        dress_code = st.text_input("Dress code", placeholder="Ex: Social, Black Tie, Casual", key="conv_dress")
        contato_conv = st.text_input("Contato para dúvidas", placeholder="(11) 99999-9999 ou email@exemplo.com", key="conv_contato")
        rsvp_link_conv = st.text_input("Link de RSVP", placeholder="https://spotlightia.streamlit.app/?evento=...", key="conv_rsvp")

    ev_info_conv = next((e for e in st.session_state.eventos_cadastrados if e["nome"] == ev_conv), {})

    temas_cores = {
        "Roxo elegante":    ("534AB7", "EEEDFE", "3C3489"),
        "Dourado premium":  ("B8860B", "FFF8DC", "8B6508"),
        "Azul corporativo": ("1A56DB", "EBF5FF", "1035A0"),
        "Verde natureza":   ("2D6A4F", "D8F3DC", "1B4332"),
        "Rosa romantico":   ("C2185B", "FCE4EC", "880E4F"),
    }
    cor_pri, cor_bg, cor_sec = temas_cores[tema]

    html_convite = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Convite — {ev_conv}</title>
<style>
  body{{margin:0;padding:20px;background:#f0f0f0;font-family:Georgia,serif}}
  .card{{max-width:520px;margin:auto;background:#fff;border-radius:16px;overflow:hidden;box-shadow:0 8px 32px rgba(0,0,0,.15)}}
  .header{{background:#{cor_pri};padding:40px 24px;text-align:center;color:#fff}}
  .header h1{{margin:0;font-size:28px;letter-spacing:2px}}
  .header p{{margin:8px 0 0;opacity:.85;font-size:14px}}
  .body{{padding:28px 24px;background:#{cor_bg}}}
  .info-row{{display:flex;gap:12px;margin-bottom:12px;align-items:center;background:#fff;padding:12px;border-radius:8px}}
  .info-icon{{font-size:20px;width:30px;text-align:center}}
  .info-label{{font-size:11px;color:#888;text-transform:uppercase;letter-spacing:.05em}}
  .info-value{{font-size:15px;font-weight:600;color:#333}}
  .msg{{background:#fff;padding:16px;border-radius:8px;margin:16px 0;border-left:4px solid #{cor_pri};font-style:italic;color:#555;line-height:1.6}}
  .rsvp-btn{{display:block;background:#{cor_pri};color:#fff;text-align:center;padding:14px;border-radius:8px;text-decoration:none;font-size:16px;font-weight:600;margin-top:16px;letter-spacing:.5px}}
  .footer{{background:#{cor_pri};padding:16px;text-align:center;color:rgba(255,255,255,.7);font-size:11px}}
</style></head>
<body>
<div class="card">
  <div class="header">
    <div style="font-size:48px;margin-bottom:8px">🎉</div>
    <h1>{ev_conv}</h1>
    <p>Você está convidado!</p>
  </div>
  <div class="body">
    <div class="info-row"><div class="info-icon">📅</div><div><div class="info-label">Data</div><div class="info-value">{ev_info_conv.get('data','A confirmar')}</div></div></div>
    <div class="info-row"><div class="info-icon">📍</div><div><div class="info-label">Local</div><div class="info-value">{ev_info_conv.get('local','A confirmar')}</div></div></div>
    {f'<div class="info-row"><div class="info-icon">👗</div><div><div class="info-label">Dress Code</div><div class="info-value">{dress_code}</div></div></div>' if dress_code else ''}
    {f'<div class="info-row"><div class="info-icon">📞</div><div><div class="info-label">Contato</div><div class="info-value">{contato_conv}</div></div></div>' if contato_conv else ''}
    <div class="msg">"{mensagem_conv}"</div>
    {f'<a class="rsvp-btn" href="{rsvp_link_conv}">✅ Confirmar Presença</a>' if rsvp_link_conv else '<div class="rsvp-btn" style="opacity:.5;cursor:not-allowed">✅ Confirmar Presença</div>'}
  </div>
  <div class="footer">Spotlight Eventos · spotlightia@eventos.com.br</div>
</div>
</body></html>"""

    st.markdown("#### 👁️ Preview do Convite")
    st.components.v1.html(html_convite, height=620, scrolling=True)

    st.divider()
    col_dl1, col_dl2 = st.columns(2)
    with col_dl1:
        st.download_button(
            "⬇️ Baixar convite HTML",
            html_convite,
            file_name=f"convite_{ev_conv.replace(' ','_')}.html",
            mime="text/html",
            use_container_width=True,
        )
    with col_dl2:
        if st.button("💬 Gerar texto do convite para WhatsApp", use_container_width=True, key="btn_wpp_conv"):
            msg = f"Crie um texto de convite elegante e curto para enviar via WhatsApp para o evento '{ev_conv}' em {ev_info_conv.get('data','—')} no {ev_info_conv.get('local','—')}. Dress code: {dress_code or 'nao definido'}. Inclua o link de RSVP: {rsvp_link_conv or '[link]'}."
            st.session_state.messages.append({"role": "user", "content": msg})
            st.rerun()


# ── TAB: CRONOGRAMA VISUAL ────────────────────────────────────────────────────
with tab_crono:
    st.markdown("### 🗓️ Cronograma Visual do Evento")
    st.caption("Monte a linha do tempo do dia do evento e compartilhe com a equipe")

    ev_crono = st.selectbox("Evento", [e["nome"] for e in st.session_state.eventos_cadastrados], key="crono_ev")

    crono_key = f"crono_{ev_crono}"
    if crono_key not in st.session_state:
        st.session_state[crono_key] = [
            {"hora": "08:00", "atividade": "Montagem e decoracao",      "responsavel": "Equipe Spotlight", "status": "⏳ Pendente"},
            {"hora": "14:00", "atividade": "Chegada dos fornecedores",  "responsavel": "Coordenador",      "status": "⏳ Pendente"},
            {"hora": "16:00", "atividade": "Teste de som e iluminacao", "responsavel": "Tecnico AV",       "status": "⏳ Pendente"},
            {"hora": "18:00", "atividade": "Recepcao dos convidados",   "responsavel": "Equipe Valet",     "status": "⏳ Pendente"},
            {"hora": "19:00", "atividade": "Inicio do evento",          "responsavel": "Mestre de cerim.", "status": "⏳ Pendente"},
            {"hora": "20:00", "atividade": "Jantar / servico",          "responsavel": "Buffet",           "status": "⏳ Pendente"},
            {"hora": "22:00", "atividade": "Brinde / momento especial", "responsavel": "Anfitrioes",       "status": "⏳ Pendente"},
            {"hora": "00:00", "atividade": "Encerramento",              "responsavel": "Coordenador",      "status": "⏳ Pendente"},
        ]

    st.markdown("#### ➕ Adicionar item ao cronograma")
    col_cr1, col_cr2, col_cr3, col_cr4 = st.columns([1, 2, 2, 1])
    nova_hora  = col_cr1.text_input("Hora", placeholder="19:30", key="crono_hora")
    nova_atv   = col_cr2.text_input("Atividade", key="crono_atv")
    nova_resp  = col_cr3.text_input("Responsável", key="crono_resp")
    if col_cr4.button("➕ Adicionar", use_container_width=True, key="btn_crono_add"):
        if nova_hora and nova_atv:
            st.session_state[crono_key].append({
                "hora": nova_hora, "atividade": nova_atv,
                "responsavel": nova_resp or "—", "status": "⏳ Pendente"
            })
            st.session_state[crono_key].sort(key=lambda x: x["hora"])
            st.rerun()

    st.markdown("#### 📋 Linha do Tempo")
    status_opts = ["⏳ Pendente", "🔄 Em andamento", "✅ Concluido", "❌ Cancelado"]

    for i, item in enumerate(st.session_state[crono_key]):
        col_t1, col_t2, col_t3, col_t4, col_t5 = st.columns([1, 3, 2, 2, 1])
        col_t1.markdown(f"**{item['hora']}**")
        col_t2.markdown(item["atividade"])
        col_t3.markdown(f"👤 {item['responsavel']}")
        novo_status = col_t4.selectbox("", status_opts, index=status_opts.index(item["status"]), key=f"crono_st_{ev_crono}_{i}", label_visibility="collapsed")
        st.session_state[crono_key][i]["status"] = novo_status
        if col_t5.button("🗑️", key=f"crono_del_{ev_crono}_{i}"):
            st.session_state[crono_key].pop(i)
            st.rerun()

    # Barra de progresso
    total_c  = len(st.session_state[crono_key])
    feitos_c = sum(1 for x in st.session_state[crono_key] if x["status"] == "✅ Concluido")
    if total_c:
        st.progress(feitos_c / total_c, text=f"Progresso do dia: {feitos_c}/{total_c} itens concluídos")

    st.divider()

    # Export cronograma
    col_exp1, col_exp2 = st.columns(2)
    with col_exp1:
        crono_txt = f"CRONOGRAMA — {ev_crono}\n\n"
        for item in st.session_state[crono_key]:
            crono_txt += f"{item['hora']}  |  {item['atividade']}  |  {item['responsavel']}  |  {item['status']}\n"
        st.download_button("⬇️ Exportar cronograma .txt", crono_txt, file_name=f"cronograma_{ev_crono[:20]}.txt", mime="text/plain", use_container_width=True)
    with col_exp2:
        if st.button("💬 Pedir revisão do cronograma ao agente", use_container_width=True, key="btn_crono_ia"):
            msg = f"Revise o cronograma do evento '{ev_crono}': {crono_txt}. Identifique gaps de tempo, riscos e sugira melhorias."
            st.session_state.messages.append({"role": "user", "content": msg})
            st.rerun()


# ── TAB: DOCUMENTOS ───────────────────────────────────────────────────────────
with tab_docs:
    st.markdown("### 📁 Documentos do Evento")
    st.caption("Centralize contratos, riders, plantas e orçamentos por evento")

    if "documentos" not in st.session_state:
        st.session_state.documentos = {}

    ev_doc = st.selectbox("Evento", [e["nome"] for e in st.session_state.eventos_cadastrados], key="doc_ev")

    if ev_doc not in st.session_state.documentos:
        st.session_state.documentos[ev_doc] = []

    # Upload
    st.markdown("#### ⬆️ Enviar Documento")
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        tipo_doc = st.selectbox("Categoria", [
            "📄 Contrato", "🎵 Rider Técnico", "🏗️ Planta do Local",
            "💰 Orçamento", "📋 Briefing", "📸 Referências Visuais", "📝 Outro"
        ], key="doc_tipo")
        desc_doc = st.text_input("Descrição do arquivo", key="doc_desc")
    with col_d2:
        arquivo = st.file_uploader("Selecione o arquivo", type=["pdf","docx","xlsx","jpg","png","txt","csv"], key="doc_upload")

    if st.button("⬆️ Anexar documento", use_container_width=True, key="btn_doc_add"):
        if arquivo:
            import base64
            conteudo_b64 = base64.b64encode(arquivo.read()).decode()
            st.session_state.documentos[ev_doc].append({
                "nome":      arquivo.name,
                "tipo":      tipo_doc,
                "descricao": desc_doc or arquivo.name,
                "tamanho":   f"{arquivo.size/1024:.1f} KB",
                "dados":     conteudo_b64,
                "mime":      arquivo.type,
            })
            st.success(f"✅ '{arquivo.name}' anexado ao evento '{ev_doc}'!")
            st.rerun()
        else:
            st.warning("Selecione um arquivo antes de anexar.")

    st.divider()

    # Lista de documentos
    st.markdown(f"#### 📂 Documentos de '{ev_doc}'")
    docs_ev = st.session_state.documentos.get(ev_doc, [])

    if docs_ev:
        for i, doc in enumerate(docs_ev):
            col_dc1, col_dc2, col_dc3, col_dc4, col_dc5 = st.columns([2, 3, 1, 1, 1])
            col_dc1.markdown(f"**{doc['tipo']}**")
            col_dc2.markdown(f"{doc['descricao']}")
            col_dc3.caption(doc["tamanho"])
            # Download
            import base64 as _b64
            col_dc4.download_button(
                "⬇️",
                data=_b64.b64decode(doc["dados"]),
                file_name=doc["nome"],
                mime=doc["mime"],
                key=f"dl_doc_{ev_doc}_{i}",
            )
            if col_dc5.button("🗑️", key=f"del_doc_{ev_doc}_{i}"):
                st.session_state.documentos[ev_doc].pop(i)
                st.rerun()

        st.caption(f"{len(docs_ev)} documento(s) anexado(s)")

        if st.button("💬 Pedir análise dos documentos ao agente", use_container_width=True, key="btn_doc_ia"):
            nomes = ", ".join([d["descricao"] for d in docs_ev])
            msg = f"Tenho os seguintes documentos para o evento '{ev_doc}': {nomes}. O que devo verificar em cada um deles antes do evento?"
            st.session_state.messages.append({"role": "user", "content": msg})
            st.rerun()
    else:
        st.info("Nenhum documento anexado ainda. Faça upload acima.")

    # Resumo geral
    st.divider()
    st.markdown("#### 📊 Resumo de Documentos por Evento")
    resumo_docs = {e["nome"]: len(st.session_state.documentos.get(e["nome"], [])) for e in st.session_state.eventos_cadastrados}
    df_docs = pd.DataFrame({"Documentos": resumo_docs})
    if df_docs["Documentos"].sum() > 0:
        st.bar_chart(df_docs, height=200)
    else:
        st.info("Nenhum documento cadastrado ainda.")


# ── TAB: WIDGET DE CHAT ───────────────────────────────────────────────────────
with tab_widget:
    st.markdown("### 💬 Widget de Chat para Site")
    st.caption("Código pronto para embutir a SpotlightIA no seu site e atender clientes 24h")

    col_w1, col_w2 = st.columns(2)
    with col_w1:
        widget_cor     = st.color_picker("Cor principal", "#534AB7", key="w_cor")
        widget_titulo  = st.text_input("Título do chat", value="SpotlightIA", key="w_titulo")
        widget_subtit  = st.text_input("Subtítulo", value="Agente Spotlight Eventos • Online agora", key="w_sub")
    with col_w2:
        widget_msg     = st.text_input("Mensagem de boas-vindas", value="Olá! Como posso ajudar com seu evento?", key="w_msg")
        widget_posicao = st.selectbox("Posição na tela", ["Canto inferior direito", "Canto inferior esquerdo"], key="w_pos")
        widget_groq    = st.text_input("Groq API Key (embed)", type="password", placeholder="key_...", key="w_key", help="Deixe vazio para o usuário inserir")

    posicao_css = "right:24px" if "direito" in widget_posicao else "left:24px"
    cor_hex = widget_cor.replace("#", "")

    html_widget = f"""<!-- SpotlightIA Widget -->
<script>
(function() {{
  const GROQ_KEY = "{widget_groq}";
  const COR = "#{cor_hex}";

  // Botão flutuante
  const btn = document.createElement('div');
  btn.id = 'spotlight-btn';
  btn.innerHTML = '💬';
  btn.style.cssText = `position:fixed;bottom:24px;{posicao_css};width:56px;height:56px;background:${{COR}};border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:24px;cursor:pointer;box-shadow:0 4px 16px rgba(0,0,0,.25);z-index:9999;transition:transform .2s`;
  btn.onmouseenter = () => btn.style.transform = 'scale(1.1)';
  btn.onmouseleave = () => btn.style.transform = 'scale(1)';
  document.body.appendChild(btn);

  // Janela do chat
  const win = document.createElement('div');
  win.id = 'spotlight-win';
  win.style.cssText = `position:fixed;bottom:92px;{posicao_css};width:340px;height:480px;background:#fff;border-radius:16px;box-shadow:0 8px 32px rgba(0,0,0,.2);display:none;flex-direction:column;overflow:hidden;z-index:9999;font-family:Arial,sans-serif`;
  win.innerHTML = `
    <div style="background:${{COR}};padding:16px;color:#fff">
      <div style="font-weight:600;font-size:15px">{widget_titulo}</div>
      <div style="font-size:12px;opacity:.8">{widget_subtit}</div>
    </div>
    <div id="spl-msgs" style="flex:1;overflow-y:auto;padding:12px;display:flex;flex-direction:column;gap:8px;background:#f9f9f9"></div>
    <div style="padding:10px;border-top:1px solid #eee;display:flex;gap:6px;background:#fff">
      <input id="spl-input" placeholder="Digite sua mensagem..." style="flex:1;padding:8px 12px;border:1px solid #ddd;border-radius:20px;font-size:13px;outline:none"/>
      <button id="spl-send" style="background:${{COR}};color:#fff;border:none;border-radius:50%;width:34px;height:34px;cursor:pointer;font-size:16px">➤</button>
    </div>`;
  document.body.appendChild(win);

  let msgs = [{{"role":"assistant","content":"{widget_msg}"}}];
  const msgsEl = win.querySelector('#spl-msgs');

  function renderMsgs() {{
    msgsEl.innerHTML = msgs.map(m => `
      <div style="display:flex;justify-content:${{m.role==='user'?'flex-end':'flex-start'}}">
        <div style="max-width:80%;padding:8px 12px;border-radius:12px;font-size:13px;line-height:1.5;background:${{m.role==='user'?COR:'#fff'}};color:${{m.role==='user'?'#fff':'#333'}};box-shadow:0 1px 4px rgba(0,0,0,.08)">${{m.content}}</div>
      </div>`).join('');
    msgsEl.scrollTop = msgsEl.scrollHeight;
  }}

  async function send() {{
    const inp = win.querySelector('#spl-input');
    const txt = inp.value.trim();
    if (!txt) return;
    inp.value = '';
    msgs.push({{role:'user', content:txt}});
    renderMsgs();
    const key = GROQ_KEY || prompt('Insira sua Groq API Key:');
    if (!key) return;
    try {{
      const res = await fetch('https://api.groq.com/openai/v1/chat/completions', {{
        method:'POST',
        headers:{{'Content-Type':'application/json','Authorization':'Bearer '+key}},
        body:JSON.stringify({{model:'llama-3.3-70b-versatile',messages:[{{role:'system',content:'Você é SpotlightIA, assistente da Spotlight Eventos. Responda em português, de forma profissional e objetiva.'}},...msgs],max_tokens:512}})
      }});
      const data = await res.json();
      const reply = data.choices?.[0]?.message?.content || 'Desculpe, tente novamente.';
      msgs.push({{role:'assistant', content:reply}});
    }} catch(e) {{ msgs.push({{role:'assistant', content:'Erro de conexão. Tente novamente.'}}); }}
    renderMsgs();
  }}

  win.querySelector('#spl-send').onclick = send;
  win.querySelector('#spl-input').onkeydown = e => e.key==='Enter' && send();
  btn.onclick = () => {{ const v = win.style.display; win.style.display = v==='none'?'flex':'none'; renderMsgs(); }};
  renderMsgs();
}})();
</script>
<!-- Fim SpotlightIA Widget -->"""

    st.markdown("#### 👁️ Preview do Widget")
    preview_html = f"""
<div style="position:relative;height:120px;background:#f0f0f0;border-radius:8px;border:1px dashed #ccc;display:flex;align-items:center;justify-content:center;color:#888;font-size:13px">
  Área do seu site
  <div style="position:absolute;bottom:16px;right:16px;width:52px;height:52px;background:{widget_cor};border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:22px;box-shadow:0 4px 12px rgba(0,0,0,.2);cursor:pointer">💬</div>
</div>"""
    st.components.v1.html(preview_html, height=140)

    st.markdown("#### 📋 Código para copiar")
    st.code(html_widget, language="html")

    st.download_button(
        "⬇️ Baixar widget.js",
        html_widget,
        file_name="spotlightia_widget.html",
        mime="text/html",
        use_container_width=True,
    )

    st.info("""**Como usar:**
1. Copie o código acima
2. Cole antes do `</body>` no HTML do seu site
3. Personalize cor, título e mensagem acima
4. Se quiser a API Key embutida, insira no campo — caso contrário o usuário será solicitado na primeira mensagem""")

    if st.button("💬 Pedir ajuda para instalar o widget no meu site", use_container_width=True, key="btn_widget_ia"):
        msg = "Como instalo o widget da SpotlightIA no meu site? Uso WordPress / Webflow / HTML puro."
        st.session_state.messages.append({"role": "user", "content": msg})
        st.rerun()

# ── TAB: GERADOR DE CONTRATO ──────────────────────────────────────────────────
with tab_contrato:

    st.markdown("### 📑 Gerador de Contrato")
    st.caption("Gere contratos de prestação de serviços prontos para assinar")

    col_ct1, col_ct2 = st.columns(2)
    with col_ct1:
        st.markdown("**Dados do Contratante (Cliente)**")
        cliente_nome   = st.text_input("Nome completo / Razão social", key="ct_nome")
        cliente_cpf    = st.text_input("CPF / CNPJ", key="ct_cpf")
        cliente_end    = st.text_input("Endereço completo", key="ct_end")
        cliente_email  = st.text_input("E-mail", key="ct_email")
        cliente_tel    = st.text_input("Telefone", key="ct_tel")
    with col_ct2:
        st.markdown("**Dados do Evento**")
        ev_ct      = st.selectbox("Evento", [e["nome"] for e in st.session_state.eventos_cadastrados], key="ct_ev")
        pacote_ct  = st.selectbox("Pacote contratado", ["Essencial", "Profissional", "Premium", "Luxo VIP", "Personalizado"], key="ct_pac")
        valor_ct   = st.number_input("Valor total (R$)", min_value=0.0, value=15000.0, step=500.0, key="ct_valor")
        sinal_pct  = st.slider("Sinal / entrada (%)", 10, 50, 30, key="ct_sinal")
        venc_saldo = st.date_input("Vencimento do saldo", key="ct_venc")

    ev_info_ct = next((e for e in st.session_state.eventos_cadastrados if e["nome"] == ev_ct), {})
    sinal_val  = valor_ct * sinal_pct / 100
    saldo_val  = valor_ct - sinal_val
    hoje_str   = _date.today().strftime("%d/%m/%Y")

    # Cláusulas extras
    st.markdown("**Cláusulas adicionais (opcional)**")
    clausulas_extra = st.text_area("Uma por linha", placeholder="Ex: Inclui 2 ensaios fotográficos\nEx: Fornecimento de gerador elétrico", key="ct_clausulas", height=80)

    if st.button("📑 Gerar contrato", use_container_width=True, key="btn_gerar_contrato"):
        if not cliente_nome or not cliente_cpf:
            st.warning("Preencha nome e CPF/CNPJ do contratante.")
        else:
            clausulas_list = [c.strip() for c in clausulas_extra.strip().split("\n") if c.strip()]
            clausulas_html = "".join([f"<li>{c}</li>" for c in clausulas_list]) if clausulas_list else "<li>Não há cláusulas adicionais.</li>"

            contrato_html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head><meta charset="UTF-8">
<title>Contrato — {ev_ct}</title>
<style>
  body{{font-family:Arial,sans-serif;max-width:800px;margin:40px auto;padding:0 24px;color:#222;line-height:1.7}}
  h1{{text-align:center;color:#534AB7;font-size:22px;border-bottom:2px solid #534AB7;padding-bottom:12px}}
  h2{{font-size:15px;color:#534AB7;margin-top:28px;border-left:4px solid #534AB7;padding-left:10px}}
  table{{width:100%;border-collapse:collapse;margin:12px 0}}
  td{{padding:8px 12px;border:1px solid #ddd;font-size:14px}}
  td:first-child{{background:#f5f5f5;font-weight:600;width:35%}}
  .assinatura{{display:flex;gap:40px;margin-top:60px}}
  .linha{{flex:1;border-top:1px solid #333;padding-top:8px;text-align:center;font-size:12px;color:#666}}
  .footer{{text-align:center;color:#aaa;font-size:11px;margin-top:40px;border-top:1px solid #eee;padding-top:12px}}
  .destaque{{background:#EEEDFE;border:1px solid #AFA9EC;border-radius:8px;padding:12px 16px;margin:12px 0}}
</style></head>
<body>
<h1>🎉 CONTRATO DE PRESTAÇÃO DE SERVIÇOS<br><span style="font-size:14px;color:#666">Spotlight Eventos</span></h1>

<p>Pelo presente instrumento, as partes abaixo identificadas celebram o presente <strong>Contrato de Prestação de Serviços para Eventos</strong>, que se regerá pelas cláusulas e condições seguintes:</p>

<h2>1. PARTES</h2>
<table>
  <tr><td>Contratada</td><td><strong>Spotlight Eventos</strong> · CNPJ: XX.XXX.XXX/0001-XX · spotlightia@eventos.com.br</td></tr>
  <tr><td>Contratante</td><td><strong>{cliente_nome}</strong></td></tr>
  <tr><td>CPF / CNPJ</td><td>{cliente_cpf}</td></tr>
  <tr><td>Endereço</td><td>{cliente_end or '—'}</td></tr>
  <tr><td>E-mail</td><td>{cliente_email or '—'}</td></tr>
  <tr><td>Telefone</td><td>{cliente_tel or '—'}</td></tr>
</table>

<h2>2. OBJETO DO CONTRATO</h2>
<table>
  <tr><td>Evento</td><td><strong>{ev_ct}</strong></td></tr>
  <tr><td>Data do evento</td><td>{ev_info_ct.get('data','A confirmar')}</td></tr>
  <tr><td>Local</td><td>{ev_info_ct.get('local','A confirmar')}</td></tr>
  <tr><td>Nº de convidados</td><td>{ev_info_ct.get('convidados','—')}</td></tr>
  <tr><td>Pacote</td><td><strong>{pacote_ct}</strong></td></tr>
</table>

<h2>3. VALOR E CONDIÇÕES DE PAGAMENTO</h2>
<div class="destaque">
  <strong>Valor total: R$ {valor_ct:,.2f}</strong><br>
  Sinal / entrada ({sinal_pct}%): <strong>R$ {sinal_val:,.2f}</strong> — a pagar na assinatura deste contrato<br>
  Saldo restante: <strong>R$ {saldo_val:,.2f}</strong> — vencimento em {venc_saldo.strftime('%d/%m/%Y')}
</div>
<p>O não pagamento nas datas acordadas implicará multa de 2% ao mês sobre o valor em atraso.</p>

<h2>4. OBRIGAÇÕES DA CONTRATADA</h2>
<ul>
  <li>Executar os serviços descritos no pacote <strong>{pacote_ct}</strong> conforme briefing aprovado;</li>
  <li>Disponibilizar equipe qualificada no dia e local do evento;</li>
  <li>Manter sigilo sobre informações do contratante e convidados;</li>
  <li>Comunicar com antecedência mínima de 72h qualquer imprevisto operacional.</li>
</ul>

<h2>5. OBRIGAÇÕES DO CONTRATANTE</h2>
<ul>
  <li>Realizar os pagamentos nas datas acordadas;</li>
  <li>Fornecer informações completas sobre o evento até 30 dias antes da data;</li>
  <li>Garantir acesso ao local para montagem com pelo menos 6 horas de antecedência;</li>
  <li>Comunicar alterações no número de convidados com antecedência mínima de 15 dias.</li>
</ul>

<h2>6. CANCELAMENTO E RESCISÃO</h2>
<ul>
  <li>Cancelamento com mais de 60 dias: devolução de 80% do sinal;</li>
  <li>Cancelamento entre 30 e 60 dias: devolução de 50% do sinal;</li>
  <li>Cancelamento com menos de 30 dias: sinal não reembolsável;</li>
  <li>Em caso de força maior (desastres, pandemias), as partes negociarão nova data sem penalidades.</li>
</ul>

<h2>7. CLÁUSULAS ADICIONAIS</h2>
<ul>{clausulas_html}</ul>

<h2>8. FORO</h2>
<p>As partes elegem o foro da Comarca de São Paulo/SP para dirimir quaisquer controvérsias oriundas deste contrato, renunciando a qualquer outro, por mais privilegiado que seja.</p>

<p style="margin-top:24px">São Paulo, {hoje_str}</p>

<div class="assinatura">
  <div class="linha">_________________________________<br><strong>Spotlight Eventos</strong><br>Contratada</div>
  <div class="linha">_________________________________<br><strong>{cliente_nome}</strong><br>Contratante</div>
</div>

<div class="footer">Documento gerado pela SpotlightIA · {hoje_str}</div>
</body></html>"""

            st.session_state["contrato_html_gerado"] = contrato_html
            st.success("✅ Contrato gerado com sucesso!")

    if "contrato_html_gerado" in st.session_state:
        st.markdown("#### 👁️ Preview do Contrato")
        st.components.v1.html(st.session_state["contrato_html_gerado"], height=600, scrolling=True)

        col_dl_c1, col_dl_c2 = st.columns(2)
        with col_dl_c1:
            st.download_button(
                "⬇️ Baixar contrato HTML",
                st.session_state["contrato_html_gerado"],
                file_name=f"contrato_{ev_ct[:20].replace(' ','_')}.html",
                mime="text/html",
                use_container_width=True,
            )
        with col_dl_c2:
            if st.button("💬 Revisar contrato com o agente", use_container_width=True, key="btn_rev_contrato"):
                msg = f"Revise o contrato gerado para o evento '{ev_ct}', pacote {pacote_ct}, valor R$ {valor_ct:,.2f}. Identifique riscos, cláusulas que devo reforçar e sugestões de melhoria."
                st.session_state.messages.append({"role": "user", "content": msg})
                st.rerun()


# ── TAB: MAPA INTERATIVO ──────────────────────────────────────────────────────
with tab_mapa:
    st.markdown("### 🗺️ Mapa Interativo do Evento")
    st.caption("Monte a planta baixa do espaço com posicionamento de mesas, palco, buffet e mais")

    ev_mapa = st.selectbox("Evento", [e["nome"] for e in st.session_state.eventos_cadastrados], key="mapa_ev")

    mapa_key = f"mapa_{ev_mapa}"
    if mapa_key not in st.session_state:
        st.session_state[mapa_key] = [
            {"id": 1, "tipo": "🎤 Palco",         "x": 45, "y": 8,  "w": 12, "h": 8,  "cor": "#534AB7"},
            {"id": 2, "tipo": "🍽️ Mesa redonda",  "x": 10, "y": 30, "w": 8,  "h": 8,  "cor": "#2D6A4F"},
            {"id": 3, "tipo": "🍽️ Mesa redonda",  "x": 25, "y": 30, "w": 8,  "h": 8,  "cor": "#2D6A4F"},
            {"id": 4, "tipo": "🍽️ Mesa redonda",  "x": 40, "y": 30, "w": 8,  "h": 8,  "cor": "#2D6A4F"},
            {"id": 5, "tipo": "🍽️ Mesa redonda",  "x": 55, "y": 30, "w": 8,  "h": 8,  "cor": "#2D6A4F"},
            {"id": 6, "tipo": "🍽️ Mesa redonda",  "x": 70, "y": 30, "w": 8,  "h": 8,  "cor": "#2D6A4F"},
            {"id": 7, "tipo": "🍽️ Mesa redonda",  "x": 15, "y": 55, "w": 8,  "h": 8,  "cor": "#2D6A4F"},
            {"id": 8, "tipo": "🍽️ Mesa redonda",  "x": 30, "y": 55, "w": 8,  "h": 8,  "cor": "#2D6A4F"},
            {"id": 9, "tipo": "🍽️ Mesa redonda",  "x": 45, "y": 55, "w": 8,  "h": 8,  "cor": "#2D6A4F"},
            {"id":10, "tipo": "🍽️ Mesa redonda",  "x": 60, "y": 55, "w": 8,  "h": 8,  "cor": "#2D6A4F"},
            {"id":11, "tipo": "🍴 Buffet",         "x": 2,  "y": 45, "w": 6,  "h": 18, "cor": "#B8860B"},
            {"id":12, "tipo": "🚻 Banheiros",      "x": 88, "y": 2,  "w": 10, "h": 12, "cor": "#666"},
            {"id":13, "tipo": "🚪 Entrada",        "x": 44, "y": 88, "w": 12, "h": 6,  "cor": "#1A56DB"},
            {"id":14, "tipo": "📸 Foto/Video",     "x": 30, "y": 8,  "w": 8,  "h": 6,  "cor": "#C2185B"},
        ]

    # Controles
    col_m1, col_m2 = st.columns([2, 1])
    with col_m2:
        st.markdown("**➕ Adicionar elemento**")
        tipos_mapa = ["🎤 Palco", "🍽️ Mesa redonda", "🪑 Mesa retangular", "🍴 Buffet",
                      "🚻 Banheiros", "🚪 Entrada", "🚪 Saída", "📸 Foto/Video",
                      "💡 Iluminação", "🔊 Som", "🌸 Decoração", "🅿️ Estacionamento"]
        novo_tipo_m = st.selectbox("Tipo", tipos_mapa, key="mapa_tipo")
        col_mx, col_my = st.columns(2)
        novo_x = col_mx.number_input("X (%)", 0, 90, 40, key="mapa_x")
        novo_y = col_my.number_input("Y (%)", 0, 90, 40, key="mapa_y")
        cores_mapa = {"🎤 Palco": "#534AB7", "🍽️ Mesa redonda": "#2D6A4F", "🪑 Mesa retangular": "#2D6A4F",
                      "🍴 Buffet": "#B8860B", "🚻 Banheiros": "#666", "🚪 Entrada": "#1A56DB",
                      "🚪 Saída": "#C2185B", "📸 Foto/Video": "#C2185B", "💡 Iluminação": "#F59E0B",
                      "🔊 Som": "#7C3AED", "🌸 Decoração": "#EC4899", "🅿️ Estacionamento": "#374151"}
        if st.button("➕ Adicionar", use_container_width=True, key="btn_mapa_add"):
            novo_id = max([e["id"] for e in st.session_state[mapa_key]], default=0) + 1
            st.session_state[mapa_key].append({
                "id": novo_id, "tipo": novo_tipo_m,
                "x": novo_x, "y": novo_y, "w": 8, "h": 8,
                "cor": cores_mapa.get(novo_tipo_m, "#534AB7")
            })
            st.rerun()

        st.markdown("**🗑️ Remover elemento**")
        ids_disp = [f"{e['id']} — {e['tipo']}" for e in st.session_state[mapa_key]]
        if ids_disp:
            rem_sel = st.selectbox("Selecione", ids_disp, key="mapa_rem_sel")
            if st.button("🗑️ Remover", use_container_width=True, key="btn_mapa_rem"):
                rem_id = int(rem_sel.split(" — ")[0])
                st.session_state[mapa_key] = [e for e in st.session_state[mapa_key] if e["id"] != rem_id]
                st.rerun()

        if st.button("🔄 Resetar planta", use_container_width=True, key="btn_mapa_reset"):
            del st.session_state[mapa_key]
            st.rerun()

    with col_m1:
        st.markdown("**🗺️ Planta Baixa**")
        # Gera SVG da planta
        elementos = st.session_state[mapa_key]
        svgs = ""
        for el in elementos:
            x_px = el["x"] * 5.5
            y_px = el["y"] * 4.2
            w_px = el["w"] * 5.5
            h_px = el["h"] * 4.2
            emoji = el["tipo"].split(" ")[0]
            label = " ".join(el["tipo"].split(" ")[1:])
            cor   = el["cor"]
            svgs += f'''<rect x="{x_px}" y="{y_px}" width="{w_px}" height="{h_px}" rx="4" fill="{cor}" fill-opacity="0.85" stroke="#fff" stroke-width="1.5"/>
<text x="{x_px + w_px/2}" y="{y_px + h_px/2 - 4}" text-anchor="middle" font-size="14" fill="#fff">{emoji}</text>
<text x="{x_px + w_px/2}" y="{y_px + h_px/2 + 10}" text-anchor="middle" font-size="7" fill="#fff" font-family="Arial">{label[:8]}</text>
'''

        svg_html = f"""<svg xmlns="http://www.w3.org/2000/svg" width="100%" viewBox="0 0 550 430" style="background:#1a1a2e;border-radius:12px;border:2px solid #534AB7">
  <rect width="550" height="430" fill="#1a1a2e" rx="12"/>
  <rect x="10" y="10" width="530" height="410" fill="none" stroke="#534AB7" stroke-width="1.5" stroke-dasharray="6,4" rx="8"/>
  <text x="275" y="425" text-anchor="middle" font-size="10" fill="#534AB7" font-family="Arial">{ev_mapa}</text>
  {svgs}
</svg>"""
        st.components.v1.html(svg_html, height=450)

    st.divider()

    # Legenda
    st.markdown("**📋 Legenda**")
    cols_leg = st.columns(4)
    for i, el in enumerate(st.session_state[mapa_key]):
        col = cols_leg[i % 4]
        col.markdown(f"<span style='background:{el['cor']};color:#fff;padding:2px 8px;border-radius:4px;font-size:12px'>{el['tipo']}</span>", unsafe_allow_html=True)

    st.divider()
    col_exp_m1, col_exp_m2 = st.columns(2)
    with col_exp_m1:
        st.download_button(
            "⬇️ Baixar planta SVG",
            svg_html,
            file_name=f"planta_{ev_mapa[:20].replace(' ','_')}.svg",
            mime="image/svg+xml",
            use_container_width=True,
        )
    with col_exp_m2:
        if st.button("💬 Pedir sugestão de layout ao agente", use_container_width=True, key="btn_mapa_ia"):
            ev_info_m = next((e for e in st.session_state.eventos_cadastrados if e["nome"] == ev_mapa), {})
            msg = f"Preciso de sugestões de layout para a planta do evento '{ev_mapa}' com {ev_info_m.get('convidados','—')} convidados em {ev_info_m.get('local','—')}. Como posicionar palco, mesas, buffet e área de dança?"
            st.session_state.messages.append({"role": "user", "content": msg})
            st.rerun()

# ── TAB: PLANOS & SAAS ────────────────────────────────────────────────────────
with tab_saas:

    st.markdown("### 💎 Planos & Assinatura")
    st.caption("Gerencie seu plano e explore os recursos disponíveis")

    # ── Plano atual ────────────────────────────────────────────────────────────
    plano_cor = plano_info["cor"]
    st.markdown(f"""
<div style="background:linear-gradient(135deg,{plano_cor},{plano_cor}99);padding:20px 24px;border-radius:12px;color:#fff;margin-bottom:16px">
  <div style="font-size:13px;opacity:.8">Plano atual</div>
  <div style="font-size:28px;font-weight:700">{plano_info['nome']}</div>
  <div style="font-size:18px;margin-top:4px">{plano_info['preco']}</div>
  <div style="font-size:12px;opacity:.7;margin-top:8px">Empresa: {tenant_data.get('nome','—')} · Vencimento: {tenant_data.get('vencimento','—')}</div>
</div>
""", unsafe_allow_html=True)

    # Uso atual
    eventos_usados = len(st.session_state.eventos_cadastrados)
    max_ev = plano_info["max_eventos"]
    pct_ev = min(eventos_usados / max_ev, 1.0) if max_ev < 999 else 0.1
    st.progress(pct_ev, text=f"Eventos: {eventos_usados} / {'∞' if max_ev==999 else max_ev}")

    st.divider()

    # ── Comparativo de planos ──────────────────────────────────────────────────
    st.markdown("#### 📦 Todos os Planos")

    cols_p = st.columns(4)
    for i, (pid, pdata) in enumerate(PLANOS.items()):
        with cols_p[i]:
            is_atual = pid == plano_atual
            borda = f"3px solid {pdata['cor']}" if is_atual else "1px solid #ddd"
            st.markdown(f"""
<div style="border:{borda};border-radius:12px;padding:16px;text-align:center;background:{'#EEEDFE' if is_atual else '#fff'}">
  <div style="font-size:20px;font-weight:700;color:{pdata['cor']}">{pdata['nome']}</div>
  <div style="font-size:22px;font-weight:800;margin:8px 0">{pdata['preco']}</div>
  {'<div style="background:#534AB7;color:#fff;padding:3px 10px;border-radius:10px;font-size:11px;display:inline-block">ATUAL</div>' if is_atual else ''}
</div>""", unsafe_allow_html=True)
            for f in pdata["features"]:
                st.markdown(f"✅ {f}")
            if not is_atual:
                if st.button(f"Assinar {pdata['nome']}", key=f"btn_assinar_{pid}", use_container_width=True):
                    st.session_state.show_pagamento = pid
                    st.rerun()

    st.divider()

    # ── Checkout simulado ──────────────────────────────────────────────────────
    if st.session_state.get("show_pagamento"):
        pid_sel = st.session_state.show_pagamento
        psel    = PLANOS[pid_sel]
        st.markdown(f"#### 💳 Assinar Plano {psel['nome']}")
        st.info(f"Valor: **{psel['preco']}** · Cobrança mensal recorrente")

        col_pg1, col_pg2 = st.columns(2)
        with col_pg1:
            metodo = st.selectbox("Forma de pagamento", ["💳 Cartão de crédito", "📄 Boleto bancário", "📱 PIX"], key="pg_metodo")
        with col_pg2:
            cupom = st.text_input("Cupom de desconto", placeholder="SPOTLIGHT20", key="pg_cupom")
            if cupom.upper() == "SPOTLIGHT20":
                st.success("✅ 20% de desconto aplicado!")

        if metodo == "💳 Cartão de crédito":
            st.text_input("Número do cartão", placeholder="0000 0000 0000 0000", key="pg_card")
            col_v, col_c = st.columns(2)
            col_v.text_input("Validade", placeholder="MM/AA", key="pg_val")
            col_c.text_input("CVV", placeholder="123", type="password", key="pg_cvv")

        if st.button(f"✅ Confirmar assinatura — {psel['preco']}", use_container_width=True, key="btn_confirmar_pg"):
            # Simula aprovação
            st.session_state.clientes_saas[st.session_state.tenant]["plano"] = pid_sel
            st.session_state.plano = pid_sel
            st.session_state.show_pagamento = None
            st.success(f"🎉 Plano {psel['nome']} ativado com sucesso!")
            st.balloons()
            st.rerun()

        if st.button("Cancelar", key="btn_cancel_pg"):
            st.session_state.show_pagamento = None
            st.rerun()

    st.divider()

    # ── Gestão de usuários da conta ────────────────────────────────────────────
    st.markdown("#### 👥 Usuários da Conta")
    if plano_atual == "enterprise":
        if "usuarios_conta" not in st.session_state:
            st.session_state.usuarios_conta = [
                {"nome": "Admin", "email": tenant_data.get("email",""), "perfil": "Administrador"},
            ]
            st.dataframe(pd.DataFrame(st.session_state.usuarios_conta), use_container_width=True, hide_index=True)
        col_u1, col_u2, col_u3 = st.columns(3)
        novo_u_nome  = col_u1.text_input("Nome", key="u_nome")
        novo_u_email = col_u2.text_input("E-mail", key="u_email")
        novo_u_perfil = col_u3.selectbox("Perfil", ["Administrador", "Coordenador", "Visualizador"], key="u_perfil")
        if st.button("➕ Adicionar usuário", use_container_width=True, key="btn_add_user"):
            if novo_u_nome and novo_u_email:
                st.session_state.usuarios_conta.append({"nome": novo_u_nome, "email": novo_u_email, "perfil": novo_u_perfil})
                st.success(f"Usuário {novo_u_nome} adicionado!")
                st.rerun()
    else:
        st.info("Multi-usuário disponível apenas no plano **Enterprise**. Faça upgrade para liberar.")

    st.divider()

    # ── Histórico de faturas ───────────────────────────────────────────────────
    st.markdown("#### 🧾 Histórico de Faturas")
    faturas = [
        {"Mês": "Maio/2026",  "Plano": plano_info["nome"], "Valor": plano_info["preco"], "Status": "✅ Pago"},
        {"Mês": "Abril/2026", "Plano": plano_info["nome"], "Valor": plano_info["preco"], "Status": "✅ Pago"},
        {"Mês": "Março/2026", "Plano": plano_info["nome"], "Valor": plano_info["preco"], "Status": "✅ Pago"},
    ]
    st.dataframe(pd.DataFrame(faturas), use_container_width=True, hide_index=True)


# ── TAB: RELATÓRIO PDF ────────────────────────────────────────────────────────
with tab_relatorio:

    st.markdown("### 📊 Relatório Executivo Mensal")
    st.caption("Gere relatórios completos em HTML para imprimir ou salvar como PDF")

    col_r1, col_r2, col_r3 = st.columns(3)
    with col_r1:
        mes_rel = st.selectbox("Mês", ["Janeiro","Fevereiro","Março","Abril","Maio","Junho","Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"], index=4, key="rel_mes")
    with col_r2:
        ano_rel = st.number_input("Ano", min_value=2024, max_value=2030, value=2026, key="rel_ano")
    with col_r3:
        incluir = st.multiselect("Incluir seções", ["Resumo executivo","Eventos","RSVP","Financeiro","NPS","Checklist pendências"], default=["Resumo executivo","Eventos","RSVP","Financeiro","NPS"], key="rel_sec")

    if st.button("📊 Gerar relatório", use_container_width=True, key="btn_gerar_rel"):

        total_ev   = len(st.session_state.eventos_cadastrados)
        conf_ev    = sum(1 for e in st.session_state.eventos_cadastrados if e["status"]=="confirmed")
        total_conv = sum(e["convidados"] for e in st.session_state.eventos_cadastrados)
        total_rsvp = len(st.session_state.get("lista_rsvp",[]))
        conf_rsvp  = sum(1 for r in st.session_state.get("lista_rsvp",[]) if r["status"]=="Confirmado")
        taxa_rsvp  = round(conf_rsvp/total_rsvp*100) if total_rsvp else 0
        nome_emp   = tenant_data.get("nome","Spotlight Eventos")
        hoje_rel   = _date.today().strftime("%d/%m/%Y")

        eventos_rows = "".join([f"""
<tr>
  <td>{e['nome']}</td>
  <td>{e.get('data','—')}</td>
  <td>{e.get('local','—')}</td>
  <td>{e['convidados']}</td>
  <td><span style="background:{'#EAF3DE' if e['status']=='confirmed' else '#FAEEDA'};color:{'#3B6D11' if e['status']=='confirmed' else '#854F0B'};padding:2px 8px;border-radius:8px;font-size:11px">{'Confirmado' if e['status']=='confirmed' else 'Planejamento'}</span></td>
</tr>""" for e in st.session_state.eventos_cadastrados])

        rel_html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head><meta charset="UTF-8">
<title>Relatório {mes_rel}/{ano_rel} — {nome_emp}</title>
<style>
  body{{font-family:Arial,sans-serif;margin:0;padding:0;color:#222}}
  .header{{background:linear-gradient(135deg,#534AB7,#7B75D8);color:#fff;padding:32px 40px}}
  .header h1{{margin:0;font-size:24px}}
  .header p{{margin:4px 0 0;opacity:.8;font-size:13px}}
  .content{{padding:32px 40px}}
  .kpi-grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin:20px 0}}
  .kpi{{background:#f8f8f8;border-radius:8px;padding:16px;text-align:center;border-left:4px solid #534AB7}}
  .kpi-val{{font-size:28px;font-weight:700;color:#534AB7}}
  .kpi-label{{font-size:12px;color:#888;margin-top:4px}}
  h2{{color:#534AB7;border-bottom:2px solid #EEEDFE;padding-bottom:8px;margin-top:32px}}
  table{{width:100%;border-collapse:collapse;margin:12px 0}}
  th{{background:#534AB7;color:#fff;padding:10px 12px;text-align:left;font-size:13px}}
  td{{padding:10px 12px;border-bottom:1px solid #eee;font-size:13px}}
  tr:hover td{{background:#f9f9f9}}
  .nps-bar{{height:20px;border-radius:10px;background:linear-gradient(90deg,#EF4444 0%,#F59E0B 40%,#10B981 70%);margin:8px 0}}
  .footer{{background:#f5f5f5;padding:20px 40px;text-align:center;font-size:11px;color:#aaa;margin-top:40px}}
  @media print{{body{{-webkit-print-color-adjust:exact}}}}
</style></head>
<body>
<div class="header">
  <h1>📊 Relatório Executivo — {mes_rel}/{ano_rel}</h1>
  <p>{nome_emp} · Gerado em {hoje_rel} pela SpotlightIA · Plano {plano_info['nome']}</p>
</div>
<div class="content">

{'<h2>📋 Resumo Executivo</h2><div class="kpi-grid"><div class="kpi"><div class="kpi-val">' + str(total_ev) + '</div><div class="kpi-label">Total de eventos</div></div><div class="kpi"><div class="kpi-val">' + str(conf_ev) + '</div><div class="kpi-label">Confirmados</div></div><div class="kpi"><div class="kpi-val">' + str(total_conv) + '</div><div class="kpi-label">Total convidados</div></div><div class="kpi"><div class="kpi-val">' + str(taxa_rsvp) + '%</div><div class="kpi-label">Taxa RSVP</div></div></div>' if "Resumo executivo" in incluir else ""}

{'<h2>📅 Eventos do Período</h2><table><tr><th>Evento</th><th>Data</th><th>Local</th><th>Convidados</th><th>Status</th></tr>' + eventos_rows + '</table>' if "Eventos" in incluir else ""}

{'<h2>👥 RSVP & Confirmações</h2><table><tr><th>Métrica</th><th>Valor</th></tr><tr><td>Total de convites</td><td>' + str(total_rsvp) + '</td></tr><tr><td>Confirmados</td><td>' + str(conf_rsvp) + '</td></tr><tr><td>Pendentes</td><td>' + str(total_rsvp - conf_rsvp) + '</td></tr><tr><td>Taxa de confirmação</td><td><strong>' + str(taxa_rsvp) + '%</strong></td></tr></table>' if "RSVP" in incluir else ""}

{'<h2>💰 Resumo Financeiro</h2><table><tr><th>Item</th><th>Valor</th></tr><tr><td>Receita estimada no período</td><td><strong>R$ 87.500,00</strong></td></tr><tr><td>Ticket médio por evento</td><td>R$ ' + (str(round(87500/total_ev)) if total_ev else "—") + '</td></tr><tr><td>Crescimento vs mês anterior</td><td style="color:#2D6A4F">▲ +12%</td></tr></table>' if "Financeiro" in incluir else ""}

{'<h2>⭐ NPS & Satisfação</h2><p>Score NPS do período: <strong>78</strong> (Excelente)</p><div class="nps-bar"></div><p>😍 Promotores: 62% &nbsp;|&nbsp; 😐 Neutros: 24% &nbsp;|&nbsp; 😠 Detratores: 14%</p>' if "NPS" in incluir else ""}

</div>
<div class="footer">
  SpotlightIA · {nome_emp} · Relatório gerado automaticamente em {hoje_rel}<br>
  Este documento é confidencial e destinado exclusivamente ao uso interno.
</div>
</body></html>"""

        st.session_state["relatorio_gerado"] = rel_html
        st.success("✅ Relatório gerado!")

    if "relatorio_gerado" in st.session_state:
        st.markdown("#### 👁️ Preview do Relatório")
        st.components.v1.html(st.session_state["relatorio_gerado"], height=600, scrolling=True)

        col_dl_r1, col_dl_r2 = st.columns(2)
        with col_dl_r1:
            st.download_button(
                "⬇️ Baixar relatório HTML",
                st.session_state["relatorio_gerado"],
                file_name=f"relatorio_{mes_rel}_{ano_rel}.html",
                mime="text/html",
                use_container_width=True,
            )
        with col_dl_r2:
            st.info("💡 Para salvar como PDF: abra o HTML no navegador e use **Ctrl+P → Salvar como PDF**")

        if st.button("💬 Analisar relatório com o agente", use_container_width=True, key="btn_rel_ia"):
            msg = f"Analise o relatório de {mes_rel}/{ano_rel}: {total_ev} eventos, {conf_ev} confirmados, taxa RSVP de {taxa_rsvp}%, receita estimada R$ 87.500. Quais os pontos de atenção e recomendações para o próximo mês?"
            st.session_state.messages.append({"role": "user", "content": msg})
            st.rerun()

# ── TAB: CRM DE CLIENTES ──────────────────────────────────────────────────────
with tab_crm:

    st.markdown("### 🤝 CRM de Clientes")
    st.caption("Histórico completo de clientes, eventos, valores e relacionamento")

    # ── KPIs CRM ──────────────────────────────────────────────────────────────
    total_cli   = len(st.session_state.crm_clientes)
    ativos      = sum(1 for c in st.session_state.crm_clientes if c["status"]=="Ativo")
    prospects   = sum(1 for c in st.session_state.crm_clientes if c["status"]=="Prospect")
    ltv_total   = sum(c["valor_total"] for c in st.session_state.crm_clientes)
    ltv_medio   = round(ltv_total / total_cli) if total_cli else 0

    k1,k2,k3,k4,k5 = st.columns(5)
    k1.metric("👥 Total clientes", total_cli)
    k2.metric("✅ Ativos", ativos)
    k3.metric("🔍 Prospects", prospects)
    k4.metric("💰 LTV Total", f"R$ {ltv_total:,.0f}".replace(",","."))
    k5.metric("📊 LTV Médio", f"R$ {ltv_medio:,.0f}".replace(",","."))

    st.divider()

    # ── Filtros ────────────────────────────────────────────────────────────────
    col_f1, col_f2, col_f3 = st.columns(3)
    busca     = col_f1.text_input("🔍 Buscar cliente", key="crm_busca")
    filtro_st = col_f2.selectbox("Status", ["Todos","Ativo","Prospect","Inativo"], key="crm_st")
    filtro_tp = col_f3.selectbox("Tipo", ["Todos","Casamento","Corporativo","VIP","Aniversário","Hackathon"], key="crm_tp")

    lista_crm = st.session_state.crm_clientes
    if busca:
        lista_crm = [c for c in lista_crm if busca.lower() in c["nome"].lower() or busca.lower() in c["empresa"].lower()]
    if filtro_st != "Todos":
        lista_crm = [c for c in lista_crm if c["status"] == filtro_st]
    if filtro_tp != "Todos":
        lista_crm = [c for c in lista_crm if c["tipo"] == filtro_tp]

    # ── Lista de clientes ──────────────────────────────────────────────────────
    st.markdown(f"#### 👤 Clientes ({len(lista_crm)})")

    for cli in lista_crm:
        status_cor = {"Ativo":"#EAF3DE","Prospect":"#FAEEDA","Inativo":"#F3F4F6"}
        status_txt = {"Ativo":"#3B6D11","Prospect":"#854F0B","Inativo":"#6B7280"}
        cor_bg  = status_cor.get(cli["status"],"#F3F4F6")
        cor_txt = status_txt.get(cli["status"],"#6B7280")

        with st.expander(f"**{cli['nome']}** · {cli['empresa']} · {cli['tipo']}"):
            col_c1, col_c2, col_c3 = st.columns(3)
            with col_c1:
                st.markdown(f"**📧** {cli['email']}")
                st.markdown(f"**📞** {cli['tel']}")
                st.markdown(f"**🎂** Aniversário: {cli['aniversario']}")
            with col_c2:
                st.metric("Eventos realizados", cli["eventos"])
                st.metric("Valor total", f"R$ {cli['valor_total']:,.0f}".replace(",","."))
            with col_c3:
                st.markdown(f"**Status:** <span style='background:{cor_bg};color:{cor_txt};padding:2px 10px;border-radius:8px;font-size:12px'>{cli['status']}</span>", unsafe_allow_html=True)
                st.caption(f"Última interação: {cli['ultima_interacao']}")

            st.markdown(f"**📝 Notas:** {cli['notas']}")

            col_btn_c1, col_btn_c2, col_btn_c3, col_btn_c4 = st.columns(4)
            if col_btn_c1.button("💬 Conversar", key=f"crm_chat_{cli['id']}", use_container_width=True):
                msg = f"Me dê um resumo do cliente {cli['nome']} da empresa {cli['empresa']}, tipo de evento {cli['tipo']}, {cli['eventos']} eventos realizados e valor total R$ {cli['valor_total']:,.0f}. Quais ações de relacionamento sugere?".replace(",",".")
                st.session_state.messages.append({"role":"user","content":msg})
                st.rerun()
            if col_btn_c2.button("📧 E-mail", key=f"crm_email_{cli['id']}", use_container_width=True):
                msg = f"Escreva um e-mail de relacionamento para {cli['nome']} da {cli['empresa']}, cliente {cli['status'].lower()} do tipo {cli['tipo']}."
                st.session_state.messages.append({"role":"user","content":msg})
                st.rerun()
            # Editar notas inline
            nova_nota = col_btn_c3.text_input("Nova nota", key=f"crm_nota_{cli['id']}", label_visibility="collapsed", placeholder="Adicionar nota...")
            if col_btn_c4.button("💾 Salvar", key=f"crm_save_{cli['id']}", use_container_width=True):
                for c in st.session_state.crm_clientes:
                    if c["id"] == cli["id"]:
                        c["notas"] = nova_nota or c["notas"]
                        c["ultima_interacao"] = _date.today().strftime("%d/%m/%Y") if "_date2" in dir() else "hoje"
                st.success("Nota salva!")
                st.rerun()

    st.divider()

    # ── Cadastrar novo cliente ─────────────────────────────────────────────────
    st.markdown("#### ➕ Cadastrar Novo Cliente")
    with st.form("form_novo_cliente", clear_on_submit=True):
        col_nc1, col_nc2 = st.columns(2)
        with col_nc1:
            nc_nome   = st.text_input("Nome completo *")
            nc_emp    = st.text_input("Empresa")
            nc_email  = st.text_input("E-mail *")
            nc_tel    = st.text_input("Telefone")
        with col_nc2:
            nc_tipo   = st.selectbox("Tipo de evento preferido", ["Casamento","Corporativo","VIP","Aniversário","Hackathon","Palestra"])
            nc_status = st.selectbox("Status", ["Prospect","Ativo","Inativo"])
            nc_aniv   = st.text_input("Data de aniversário (dd/mm)")
            nc_notas  = st.text_area("Notas", height=68)
        sub_nc = st.form_submit_button("➕ Cadastrar cliente", use_container_width=True)
        if sub_nc:
            if nc_nome and nc_email:
                novo_id = max([c["id"] for c in st.session_state.crm_clientes], default=0) + 1
                novo_cli = {
                    "id":novo_id,"nome":nc_nome,"empresa":nc_emp or "—","email":nc_email,
                    "tel":nc_tel or "—","tipo":nc_tipo,"eventos":0,"valor_total":0,
                    "status":nc_status,"aniversario":nc_aniv or "—","notas":nc_notas or "—",
                    "ultima_interacao":"hoje",
                }
                st.session_state.crm_clientes.append(novo_cli)
                if DB_DISPONIVEL and st.session_state.get("tenant"):
                    db.crm_criar(st.session_state.tenant, novo_cli)
                st.success(f"✅ {nc_nome} cadastrado no CRM!")
                st.rerun()
            else:
                st.warning("Preencha nome e e-mail.")

    st.divider()

    # ── Gráfico LTV por tipo ───────────────────────────────────────────────────
    st.markdown("#### 💰 LTV por Tipo de Cliente")
    ltv_tipo = {}
    for c in st.session_state.crm_clientes:
        ltv_tipo[c["tipo"]] = ltv_tipo.get(c["tipo"],0) + c["valor_total"]
    if ltv_tipo:
        df_ltv = pd.DataFrame({"LTV (R$)": ltv_tipo})
        st.bar_chart(df_ltv, height=220)

    # ── Aniversários próximos ──────────────────────────────────────────────────
    st.divider()
    st.markdown("#### 🎂 Aniversários do Mês")
    from datetime import date as _d
    mes_atual = str(_d.today().month).zfill(2)
    aniversariantes = [c for c in st.session_state.crm_clientes if c["aniversario"] and f"/{mes_atual}" in c["aniversario"]]
    if aniversariantes:
        for a in aniversariantes:
            col_a1, col_a2 = st.columns([3,1])
            col_a1.markdown(f"🎂 **{a['nome']}** ({a['empresa']}) — {a['aniversario']}")
            if col_a2.button("💬 Gerar mensagem", key=f"aniv_{a['id']}", use_container_width=True):
                msg = f"Escreva uma mensagem de feliz aniversário para {a['nome']} da {a['empresa']}, cliente {a['tipo']} da Spotlight Eventos. Tom profissional e caloroso."
                st.session_state.messages.append({"role":"user","content":msg})
                st.rerun()
    else:
        st.info("Nenhum aniversariante este mês.")


# ── TAB: QR CODE DE ENTRADA ───────────────────────────────────────────────────
with tab_qr:
    st.markdown("### 🎫 QR Code de Entrada")
    st.caption("Gere QR Codes únicos por convidado para controle de acesso no dia do evento")

    col_qr1, col_qr2 = st.columns(2)
    with col_qr1:
        ev_qr = st.selectbox("Evento", [e["nome"] for e in st.session_state.eventos_cadastrados], key="qr_ev")
    with col_qr2:
        modo_qr = st.selectbox("Modo", ["Gerar QR Codes","Escanear / Validar entrada"], key="qr_modo")

    st.divider()

    if modo_qr == "Gerar QR Codes":
        st.markdown("#### 🎟️ Gerar QR Codes dos Convidados")

        rsvp_ev = [r for r in st.session_state.get("lista_rsvp",[]) if r["evento"]==ev_qr and r["status"]=="Confirmado"]

        if rsvp_ev:
            st.success(f"{len(rsvp_ev)} convidado(s) confirmado(s) para '{ev_qr}'")

            # Tenta gerar QR Code real com qrcode lib
            try:
                import qrcode
                import base64
                from io import BytesIO

                cols_qr = st.columns(3)
                for i, conv in enumerate(rsvp_ev):
                    qr_data = f"SPOTLIGHT|{ev_qr}|{conv['nome']}|{conv['email']}|{conv['acomp']}"
                    qr_img  = qrcode.make(qr_data)
                    buf = BytesIO()
                    qr_img.save(buf, format="PNG")
                    buf.seek(0)
                    b64 = base64.b64encode(buf.read()).decode()

                    with cols_qr[i % 3]:
                        st.image(f"data:image/png;base64,{b64}", width=180)
                        st.caption(f"**{conv['nome']}**")
                        st.caption(f"+{conv['acomp']} acomp.")
                        st.download_button(
                            "⬇️ Baixar",
                            data=base64.b64decode(b64),
                            file_name=f"qr_{conv['nome'].replace(' ','_')}.png",
                            mime="image/png",
                            key=f"dl_qr_{ev_qr}_{i}",
                            use_container_width=True,
                        )

            except ImportError:
                # Fallback: QR Code em SVG simples (representação visual)
                st.warning("Para QR Codes reais instale: `pip install qrcode pillow`")
                st.info("Abaixo uma representação visual — instale a biblioteca para QR Codes escaneáveis.")
                cols_qr = st.columns(3)
                for i, conv in enumerate(rsvp_ev):
                    qr_data = f"SPOTLIGHT|{ev_qr}|{conv['nome']}|{conv['email']}"
                    import hashlib
                    h = hashlib.md5(qr_data.encode()).hexdigest()
                    # Gera padrão visual baseado no hash
                    cells = ""
                    for row in range(10):
                        for col2 in range(10):
                            idx = (row * 10 + col2) % len(h)
                            filled = int(h[idx], 16) > 7
                            if filled:
                                cells += f'<rect x="{col2*20}" y="{row*20}" width="18" height="18" fill="#222"/>'
                    svg_qr = f'<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200" style="background:#fff;border-radius:8px;padding:4px"><rect width="200" height="200" fill="#fff"/>{cells}<rect x="0" y="0" width="40" height="40" fill="#222"/><rect x="4" y="4" width="32" height="32" fill="#fff"/><rect x="8" y="8" width="24" height="24" fill="#222"/><rect x="160" y="0" width="40" height="40" fill="#222"/><rect x="164" y="4" width="32" height="32" fill="#fff"/><rect x="168" y="8" width="24" height="24" fill="#222"/><rect x="0" y="160" width="40" height="40" fill="#222"/><rect x="4" y="164" width="32" height="32" fill="#fff"/><rect x="8" y="168" width="24" height="24" fill="#222"/></svg>'

                    with cols_qr[i % 3]:
                        st.components.v1.html(svg_qr, height=210)
                        st.caption(f"**{conv['nome']}**")
                        st.caption(f"+{conv['acomp']} acomp.")

        else:
            st.info(f"Nenhum convidado confirmado para '{ev_qr}' ainda. Registre RSVPs na aba Confirmações.")

        st.divider()

        # Geração em lote — HTML de todos os ingressos
        if rsvp_ev and st.button("📄 Gerar ingressos HTML para impressão", use_container_width=True, key="btn_ingressos_html"):
            cards = ""
            for conv in rsvp_ev:
                import hashlib
                h = hashlib.md5((ev_qr+conv["email"]).encode()).hexdigest()
                token = h[:12].upper()
                cards += f"""
<div style="width:340px;border:2px solid #534AB7;border-radius:12px;padding:20px;margin:12px;display:inline-block;font-family:Arial,sans-serif;page-break-inside:avoid">
  <div style="background:#534AB7;color:#fff;padding:10px;border-radius:8px;text-align:center;margin-bottom:12px">
    <div style="font-size:18px;font-weight:700">🎉 {ev_qr}</div>
  </div>
  <div style="font-size:15px;font-weight:600">{conv['nome']}</div>
  <div style="color:#888;font-size:13px">+ {conv['acomp']} acompanhante(s)</div>
  <div style="color:#888;font-size:12px;margin-top:4px">📧 {conv['email']}</div>
  <div style="background:#f5f5f5;border-radius:8px;padding:10px;margin-top:12px;text-align:center">
    <div style="font-size:11px;color:#888;margin-bottom:4px">Código de acesso</div>
    <div style="font-size:22px;font-weight:700;letter-spacing:3px;color:#534AB7">{token}</div>
  </div>
  <div style="font-size:10px;color:#ccc;text-align:center;margin-top:8px">Spotlight Eventos · Apresente na entrada</div>
</div>"""

            html_ing = f"<!DOCTYPE html><html><head><meta charset='UTF-8'><title>Ingressos — {ev_qr}</title></head><body style='background:#f0f0f0;padding:20px'><h2 style='font-family:Arial;color:#534AB7'>🎟️ Ingressos — {ev_qr}</h2>{cards}</body></html>"
            st.download_button("⬇️ Baixar ingressos HTML", html_ing, file_name=f"ingressos_{ev_qr[:20]}.html", mime="text/html", use_container_width=True)

    else:
        # Modo validação
        st.markdown("#### 📷 Validar Entrada")
        st.info("Para escanear QR Codes use um app de leitura no celular ou integre com a câmera do dispositivo.")

        st.markdown("**Ou valide manualmente pelo código:**")
        codigo_val = st.text_input("Digite o código do ingresso", placeholder="Ex: A3F9C12B4D01", key="val_codigo").upper().strip()

        if "entradas_validadas" not in st.session_state:
            st.session_state.entradas_validadas = {}

        if st.button("✅ Validar entrada", use_container_width=True, key="btn_validar"):
            if codigo_val:
                rsvp_todos = [r for r in st.session_state.get("lista_rsvp",[]) if r["evento"]==ev_qr and r["status"]=="Confirmado"]
                import hashlib
                encontrado = None
                for r in rsvp_todos:
                    h = hashlib.md5((ev_qr+r["email"]).encode()).hexdigest()
                    token_r = h[:12].upper()
                    if token_r == codigo_val:
                        encontrado = r
                        break
                if encontrado:
                    chave_val = f"{ev_qr}_{codigo_val}"
                    if chave_val in st.session_state.entradas_validadas:
                        st.warning(f"⚠️ Entrada JÁ VALIDADA para **{encontrado['nome']}**!")
                    else:
                        st.session_state.entradas_validadas[chave_val] = encontrado["nome"]
                        st.success(f"✅ Entrada confirmada! **{encontrado['nome']}** + {encontrado['acomp']} acompanhante(s)")
                        st.balloons()
                else:
                    st.error("❌ Código não encontrado. Verifique o ingresso.")
            else:
                st.warning("Digite o código do ingresso.")

        # Resumo de entradas
        st.divider()
        st.markdown("**📊 Entradas validadas neste evento:**")
        entradas_ev = {k:v for k,v in st.session_state.entradas_validadas.items() if k.startswith(ev_qr)}
        rsvp_total_ev = len([r for r in st.session_state.get("lista_rsvp",[]) if r["evento"]==ev_qr and r["status"]=="Confirmado"])

        col_v1, col_v2, col_v3 = st.columns(3)
        col_v1.metric("✅ Entradas validadas", len(entradas_ev))
        col_v2.metric("🎟️ Total confirmados", rsvp_total_ev)
        col_v3.metric("⏳ Aguardando", max(rsvp_total_ev - len(entradas_ev), 0))

        if entradas_ev:
            for k, nome in entradas_ev.items():
                st.markdown(f"✅ {nome}")

# ── TAB: FUNIL KANBAN ─────────────────────────────────────────────────────────
with tab_kanban:

    st.markdown("### 🔁 Funil de Vendas")
    st.caption("Pipeline visual de oportunidades — do primeiro contato ao evento concluído")

    COLUNAS_KANBAN = ["Prospect","Proposta enviada","Negociação","Fechado","Em execução","Concluído"]
    CORES_KANBAN   = {"Prospect":"#6B7280","Proposta enviada":"#1A56DB","Negociação":"#B8860B","Fechado":"#2D6A4F","Em execução":"#534AB7","Concluído":"#C2185B"}

    # KPIs do funil
    total_oport  = sum(len(v) for v in st.session_state.kanban.values())
    valor_pipe   = sum(c["valor"] for col in st.session_state.kanban.values() for c in col)
    valor_fech   = sum(c["valor"] for c in st.session_state.kanban.get("Fechado",[]) + st.session_state.kanban.get("Concluído",[]))
    tx_conv      = round(len(st.session_state.kanban.get("Fechado",[])) / total_oport * 100) if total_oport else 0

    k1,k2,k3,k4 = st.columns(4)
    k1.metric("🎯 Oportunidades", total_oport)
    k2.metric("💰 Pipeline total", f"R$ {valor_pipe:,.0f}".replace(",","."))
    k3.metric("✅ Valor fechado", f"R$ {valor_fech:,.0f}".replace(",","."))
    k4.metric("📈 Taxa conversão", f"{tx_conv}%")

    st.divider()

    # Board Kanban
    st.markdown("#### 📋 Board")
    cols_kb = st.columns(len(COLUNAS_KANBAN))

    for i, coluna in enumerate(COLUNAS_KANBAN):
        cor = CORES_KANBAN[coluna]
        cards = st.session_state.kanban.get(coluna, [])
        valor_col = sum(c["valor"] for c in cards)

        with cols_kb[i]:
            st.markdown(f"""<div style="background:{cor};color:#fff;padding:8px 10px;border-radius:8px;text-align:center;margin-bottom:8px">
<div style="font-size:12px;font-weight:600">{coluna}</div>
<div style="font-size:11px;opacity:.8">{len(cards)} · R$ {valor_col:,.0f}".replace(",",".")</div>
</div>""".replace('R$ {valor_col:,.0f}".replace(",",".")', f'R$ {valor_col:,}'.replace(',','.')), unsafe_allow_html=True)

            for card in cards:
                tipo_emoji = {"Casamento":"💍","Corporativo":"💼","VIP":"⭐","Aniversário":"🎂","Hackathon":"💻","Palestra":"🎤"}.get(card["tipo"],"🎉")
                st.markdown(f"""<div style="background:#fff;border:1px solid #e5e7eb;border-radius:8px;padding:10px;margin-bottom:8px;font-size:12px">
<div style="font-weight:600;color:#222">{tipo_emoji} {card['cliente']}</div>
<div style="color:#666;margin:2px 0">{card['evento']}</div>
<div style="color:{cor};font-weight:600">R$ {card['valor']:,}".replace(",",".")</div>
<div style="color:#999;font-size:11px;margin-top:4px">{card['nota'][:40]}...</div>
</div>""".replace('R$ {card[\'valor\']:,}".replace(",",".")', f"R$ {card['valor']:,}".replace(',','.')), unsafe_allow_html=True)

                # Mover para próxima etapa
                idx_col = COLUNAS_KANBAN.index(coluna)
                if idx_col < len(COLUNAS_KANBAN) - 1:
                    prox = COLUNAS_KANBAN[idx_col + 1]
                    if st.button(f"→ {prox[:10]}", key=f"mv_{card['id']}_{coluna}", use_container_width=True):
                        st.session_state.kanban[coluna].remove(card)
                        st.session_state.kanban[prox].append(card)
                        st.rerun()

    st.divider()

    # Adicionar oportunidade
    st.markdown("#### ➕ Nova Oportunidade")
    with st.form("form_kanban", clear_on_submit=True):
        col_k1, col_k2, col_k3 = st.columns(3)
        k_cli    = col_k1.text_input("Cliente *")
        k_ev     = col_k1.text_input("Evento *")
        k_val    = col_k2.number_input("Valor estimado (R$)", min_value=0, value=15000, step=1000)
        k_tipo   = col_k2.selectbox("Tipo", ["Casamento","Corporativo","VIP","Aniversário","Hackathon","Palestra"])
        k_cont   = col_k3.text_input("Contato (e-mail/tel)")
        k_nota   = col_k3.text_input("Nota inicial")
        k_etapa  = col_k3.selectbox("Etapa inicial", COLUNAS_KANBAN)
        sub_k    = st.form_submit_button("➕ Adicionar ao funil", use_container_width=True)
        if sub_k:
            if k_cli and k_ev:
                novo_id_k = max([c["id"] for col in st.session_state.kanban.values() for c in col], default=0) + 1
                st.session_state.kanban[k_etapa].append({"id":novo_id_k,"cliente":k_cli,"evento":k_ev,"valor":k_val,"tipo":k_tipo,"contato":k_cont,"nota":k_nota})
                st.success(f"✅ {k_cli} adicionado em '{k_etapa}'!")
                st.rerun()
            else:
                st.warning("Preencha cliente e evento.")

    st.divider()

    # Análise do funil com IA
    if st.button("💬 Analisar funil com o agente", use_container_width=True, key="btn_kanban_ia"):
        resumo_k = " | ".join([f"{col}: {len(cards)} deals (R$ {sum(c['valor'] for c in cards):,})".replace(",",".") for col, cards in st.session_state.kanban.items()])
        msg = f"Analise meu funil de vendas: {resumo_k}. Quais oportunidades priorizar? Onde estou perdendo mais negócios? Sugira ações para aumentar a taxa de conversão."
        st.session_state.messages.append({"role":"user","content":msg})
        st.rerun()


# ── TAB: ROTEIRO DO MC ────────────────────────────────────────────────────────
with tab_mc:
    st.markdown("### 🎙️ Roteiro do Mestre de Cerimônias")
    st.caption("Gere roteiros completos com falas, horários e transições para o dia do evento")

    col_mc1, col_mc2 = st.columns(2)
    with col_mc1:
        ev_mc      = st.selectbox("Evento", [e["nome"] for e in st.session_state.eventos_cadastrados], key="mc_ev")
        nome_mc    = st.text_input("Nome do mestre de cerimônias", placeholder="Ex: Roberto Silva", key="mc_nome")
        estilo_mc  = st.selectbox("Estilo do roteiro", ["Formal e elegante","Descontraído e animado","Corporativo e objetivo","Romântico e emocional"], key="mc_estilo")
    with col_mc2:
        anfitrioes = st.text_input("Nome dos anfitriões / homenageados", placeholder="Ex: João e Maria", key="mc_anf")
        destaques  = st.text_area("Momentos especiais (um por linha)", placeholder="Entrada dos noivos\nCorte do bolo\nJogo de perguntas\nApresentação da banda", key="mc_dest", height=100)
        obs_mc     = st.text_input("Observações especiais", placeholder="Ex: Surpresa no final, não mencionar antes", key="mc_obs")

    ev_info_mc = next((e for e in st.session_state.eventos_cadastrados if e["nome"] == ev_mc), {})

    # Usa cronograma cadastrado se existir
    crono_mc_key = f"crono_{ev_mc}"
    crono_existente = st.session_state.get(crono_mc_key, [])

    if st.button("🎙️ Gerar roteiro com IA", use_container_width=True, key="btn_gerar_mc"):
        if not api_key:
            st.error("⚠️ Configure a API Key na barra lateral primeiro.")
        else:
            crono_str = "\n".join([f"{c['hora']} - {c['atividade']}" for c in crono_existente]) if crono_existente else "Cronograma não cadastrado"
            prompt_mc = f"""Gere um roteiro completo para o mestre de cerimônias do evento abaixo.

EVENTO: {ev_mc}
DATA: {ev_info_mc.get('data','—')}
LOCAL: {ev_info_mc.get('local','—')}
CONVIDADOS: {ev_info_mc.get('convidados','—')}
MC: {nome_mc or 'A definir'}
ANFITRIÕES/HOMENAGEADOS: {anfitrioes or 'A definir'}
ESTILO: {estilo_mc}
MOMENTOS ESPECIAIS:
{destaques or 'Não informado'}
OBSERVAÇÕES: {obs_mc or 'Nenhuma'}
CRONOGRAMA DO EVENTO:
{crono_str}

Gere um roteiro detalhado com:
1. Abertura (boas-vindas, apresentação)
2. Cada momento do cronograma com fala sugerida
3. Transições entre atividades
4. Encerramento
Use o estilo solicitado. Inclua dicas entre colchetes [dica para o MC]."""

            with st.spinner("Gerando roteiro..."):
                try:
                    provedor = st.session_state.get("provedor_ia","⚡ Groq (Llama 3.3)")
                    roteiro_texto = ""

                    if provedor == "⚡ Groq (Llama 3.3)":
                        client_mc = Groq(api_key=api_key)
                        resp_mc = client_mc.chat.completions.create(
                            model="llama-3.3-70b-versatile",
                            messages=[{"role":"user","content":prompt_mc}],
                            max_tokens=2048,
                        )
                        roteiro_texto = resp_mc.choices[0].message.content
                    elif provedor == "🌟 Google Gemini":
                        import google.generativeai as genai
                        genai.configure(api_key=api_key)
                        m_gem = genai.GenerativeModel("gemini-1.5-flash")
                        roteiro_texto = m_gem.generate_content(prompt_mc).text
                    else:
                        import requests as _rq_hf
                        r_hf = _rq_hf.post(
                            "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.3",
                            headers={"Authorization":f"Bearer {api_key}"},
                            json={"inputs": prompt_mc, "parameters":{"max_new_tokens":1500,"return_full_text":False}},
                            timeout=30,
                        )
                        roteiro_texto = r_hf.json()[0].get("generated_text","Erro ao gerar.")

                    st.session_state["roteiro_mc_gerado"] = roteiro_texto
                    st.success("✅ Roteiro gerado!")
                except Exception as e:
                    st.error(f"Erro: {e}")

    if "roteiro_mc_gerado" in st.session_state:
        st.divider()
        st.markdown("#### 📄 Roteiro Gerado")
        roteiro_edit = st.text_area("Edite o roteiro conforme necessário:", value=st.session_state["roteiro_mc_gerado"], height=500, key="roteiro_edit")

        col_dl_mc1, col_dl_mc2 = st.columns(2)
        with col_dl_mc1:
            # Gera HTML bonito para impressão
            roteiro_html = f"""<!DOCTYPE html><html lang="pt-BR"><head><meta charset="UTF-8">
<title>Roteiro MC — {ev_mc}</title>
<style>body{{font-family:Georgia,serif;max-width:700px;margin:40px auto;padding:0 24px;color:#222;line-height:1.8}}
h1{{color:#534AB7;border-bottom:2px solid #534AB7;padding-bottom:8px}}
p{{margin:12px 0}}.dica{{color:#888;font-style:italic}}
.footer{{color:#aaa;font-size:11px;text-align:center;margin-top:40px;border-top:1px solid #eee;padding-top:12px}}</style></head>
<body><h1>🎙️ Roteiro — {ev_mc}</h1>
<p><strong>MC:</strong> {nome_mc or '—'} · <strong>Estilo:</strong> {estilo_mc}</p>
<hr/>
{"<br>".join(roteiro_edit.replace("[","<span class='dica'>[").replace("]","]</span>").split(chr(10)))}
<div class="footer">Gerado pela SpotlightIA · Spotlight Eventos</div>
</body></html>"""
            st.download_button("⬇️ Baixar roteiro HTML", roteiro_html, file_name=f"roteiro_{ev_mc[:20]}.html", mime="text/html", use_container_width=True)
        with col_dl_mc2:
            st.download_button("⬇️ Baixar roteiro .txt", roteiro_edit, file_name=f"roteiro_{ev_mc[:20]}.txt", mime="text/plain", use_container_width=True)


# ── TAB: PÁGINA DE CAPTAÇÃO ───────────────────────────────────────────────────
with tab_landing:
    st.markdown("### 📣 Página de Captação de Leads")
    st.caption("Landing page pública para captar clientes e criar prospects automaticamente no CRM")

    aba_lp1, aba_lp2, aba_lp3 = st.tabs(["🎨 Personalizar", "👁️ Preview", "📋 Leads recebidos"])

    with aba_lp1:
        st.markdown("#### 🎨 Configurar Landing Page")
        col_lp1, col_lp2 = st.columns(2)
        with col_lp1:
            lp_titulo   = st.text_input("Título principal", value="Realize o Evento dos Seus Sonhos", key="lp_titulo")
            lp_subtitulo = st.text_input("Subtítulo", value="A Spotlight Eventos cuida de tudo para você", key="lp_sub")
            lp_cta      = st.text_input("Texto do botão", value="Solicitar orçamento gratuito", key="lp_cta")
            lp_cor      = st.color_picker("Cor principal", "#534AB7", key="lp_cor")
        with col_lp2:
            lp_tel      = st.text_input("Telefone de contato", placeholder="(11) 99999-9999", key="lp_tel")
            lp_email    = st.text_input("E-mail de contato", placeholder="contato@spotlight.com", key="lp_email")
            lp_servicos = st.multiselect("Serviços em destaque", ["Casamentos","Formaturas","Corporativos","VIP","Hackathons","Palestras","Aniversários"], default=["Casamentos","Corporativos","VIP"], key="lp_serv")
            lp_depo     = st.checkbox("Exibir depoimentos", value=True, key="lp_depo")

        st.session_state["lp_config"] = {"titulo":lp_titulo,"subtitulo":lp_subtitulo,"cta":lp_cta,"cor":lp_cor,"tel":lp_tel,"email":lp_email,"servicos":lp_servicos,"depoimentos":lp_depo}
        st.success("Configurações salvas! Veja o preview na aba ao lado.")

    with aba_lp2:
        cfg = st.session_state.get("lp_config",{"titulo":"Realize o Evento dos Seus Sonhos","subtitulo":"A Spotlight Eventos cuida de tudo","cta":"Solicitar orçamento","cor":"#534AB7","tel":"","email":"","servicos":["Casamentos","VIP"],"depoimentos":True})
        cor_lp = cfg.get("cor","#534AB7")
        servicos_icons = {"Casamentos":"💍","Formaturas":"🎓","Corporativos":"💼","VIP":"⭐","Hackathons":"💻","Palestras":"🎤","Aniversários":"🎂"}
        servicos_html = "".join([f'<div style="background:#fff;border-radius:10px;padding:16px;text-align:center;box-shadow:0 2px 8px rgba(0,0,0,.08)"><div style="font-size:28px">{servicos_icons.get(s,"🎉")}</div><div style="font-weight:600;margin-top:6px;color:#333">{s}</div></div>' for s in cfg.get("servicos",[])])
        depo_html = """<div style="background:#f9f9f9;border-radius:12px;padding:20px;margin:8px 0">
<div style="font-size:14px;color:#555;font-style:italic">"Evento impecável! A equipe cuidou de cada detalhe."</div>
<div style="font-size:12px;color:#888;margin-top:8px">— Ana Lima · Casamento 2025</div></div>
<div style="background:#f9f9f9;border-radius:12px;padding:20px;margin:8px 0">
<div style="font-size:14px;color:#555;font-style:italic">"Profissionalismo do início ao fim. Superou todas as expectativas."</div>
<div style="font-size:12px;color:#888;margin-top:8px">— Carlos Mendes · TechCorp 2025</div></div>""" if cfg.get("depoimentos") else ""

        landing_html = f"""<!DOCTYPE html><html lang="pt-BR"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Spotlight Eventos</title>
<style>*{{box-sizing:border-box;margin:0;padding:0}}body{{font-family:Arial,sans-serif;color:#333}}
.hero{{background:linear-gradient(135deg,{cor_lp},{cor_lp}99);color:#fff;padding:60px 24px;text-align:center}}
.hero h1{{font-size:32px;margin-bottom:12px}}.hero p{{font-size:16px;opacity:.9;max-width:500px;margin:0 auto 24px}}
.cta-btn{{background:#fff;color:{cor_lp};padding:14px 32px;border-radius:30px;font-size:16px;font-weight:700;border:none;cursor:pointer;text-decoration:none;display:inline-block}}
.section{{padding:40px 24px;max-width:900px;margin:0 auto}}.section h2{{color:{cor_lp};text-align:center;margin-bottom:24px;font-size:22px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:16px;margin-bottom:32px}}
.form-card{{background:#f9f9f9;border-radius:12px;padding:24px;max-width:500px;margin:0 auto}}
.form-card input,.form-card select,.form-card textarea{{width:100%;padding:10px;border:1px solid #ddd;border-radius:6px;font-size:14px;margin-bottom:12px;font-family:Arial}}
.submit-btn{{background:{cor_lp};color:#fff;padding:12px;border-radius:8px;border:none;width:100%;font-size:15px;font-weight:600;cursor:pointer}}
.footer{{background:#222;color:#aaa;text-align:center;padding:20px;font-size:12px}}</style></head>
<body>
<div class="hero">
  <div style="font-size:48px;margin-bottom:12px">🎉</div>
  <h1>{cfg['titulo']}</h1>
  <p>{cfg['subtitulo']}</p>
  <a href="#formulario" class="cta-btn">{cfg['cta']}</a>
</div>
<div class="section">
  <h2>✨ Nossos Serviços</h2>
  <div class="grid">{servicos_html}</div>
  {f'<h2>💬 O que nossos clientes dizem</h2>{depo_html}' if cfg.get("depoimentos") else ""}
  <h2 id="formulario">📋 Solicite seu Orçamento</h2>
  <div class="form-card">
    <input type="text" placeholder="Seu nome completo *"/>
    <input type="email" placeholder="Seu e-mail *"/>
    <input type="tel" placeholder="Telefone / WhatsApp"/>
    <select><option>Tipo de evento</option>{"".join([f"<option>{s}</option>" for s in cfg.get("servicos",[])])}</select>
    <input type="text" placeholder="Data aproximada do evento"/>
    <input type="number" placeholder="Número estimado de convidados"/>
    <textarea rows="3" placeholder="Conte um pouco sobre seu evento..."></textarea>
    <button class="submit-btn">{cfg['cta']} →</button>
  </div>
  {f'<div style="text-align:center;margin-top:24px;color:#888;font-size:14px">📞 {cfg["tel"]} &nbsp;|&nbsp; 📧 {cfg["email"]}</div>' if cfg.get("tel") or cfg.get("email") else ""}
</div>
<div class="footer">Spotlight Eventos · Powered by SpotlightIA</div>
</body></html>"""

        st.components.v1.html(landing_html, height=700, scrolling=True)
        st.download_button("⬇️ Baixar landing page HTML", landing_html, file_name="landing_spotlight.html", mime="text/html", use_container_width=True)

    with aba_lp3:
        st.markdown("#### 📋 Formulário de Captação Funcional")
        st.caption("Leads enviados aqui são criados automaticamente no CRM")

        with st.form("form_lead", clear_on_submit=True):
            col_ld1, col_ld2 = st.columns(2)
            ld_nome   = col_ld1.text_input("Nome completo *")
            ld_email  = col_ld1.text_input("E-mail *")
            ld_tel    = col_ld2.text_input("Telefone / WhatsApp")
            ld_tipo   = col_ld2.selectbox("Tipo de evento", ["Casamento","Corporativo","VIP","Aniversário","Hackathon","Palestra"])
            ld_data   = col_ld1.text_input("Data aproximada")
            ld_conv   = col_ld2.number_input("Nº estimado de convidados", min_value=1, value=100)
            ld_msg    = st.text_area("Conte sobre seu evento", height=80)
            sub_ld    = st.form_submit_button("📨 Enviar solicitação", use_container_width=True)

            if sub_ld:
                if ld_nome and ld_email:
                    # Adiciona ao CRM como Prospect
                    novo_id_crm = max([c["id"] for c in st.session_state.crm_clientes], default=0) + 1
                    st.session_state.crm_clientes.append({
                        "id":novo_id_crm,"nome":ld_nome,"empresa":"—","email":ld_email,
                        "tel":ld_tel or "—","tipo":ld_tipo,"eventos":0,"valor_total":0,
                        "status":"Prospect","aniversario":"—",
                        "notas":f"Lead via landing page. Data: {ld_data}. Convidados: {ld_conv}. Mensagem: {ld_msg}",
                        "ultima_interacao":"hoje",
                    })
                    # Adiciona ao kanban
                    novo_id_kb = max([c["id"] for col in st.session_state.kanban.values() for c in col], default=0) + 1
                    st.session_state.kanban["Prospect"].append({
                        "id":novo_id_kb,"cliente":ld_nome,"evento":f"{ld_tipo} — {ld_data}",
                        "valor":0,"tipo":ld_tipo,"contato":ld_email,
                        "nota":f"Lead via landing page. {ld_conv} convidados.",
                    })
                    # Salva lead
                    st.session_state.leads_landing.append({"nome":ld_nome,"email":ld_email,"tel":ld_tel,"tipo":ld_tipo,"data":ld_data,"convidados":ld_conv,"mensagem":ld_msg})
                    st.success(f"🎉 Obrigado, {ld_nome}! Sua solicitação foi recebida. Entraremos em contato em breve.")
                    st.balloons()
                else:
                    st.warning("Preencha nome e e-mail.")

        # Lista de leads
        st.divider()
        st.markdown(f"**📊 Leads recebidos: {len(st.session_state.leads_landing)}**")
        if st.session_state.leads_landing:
            df_leads = pd.DataFrame(st.session_state.leads_landing)
            df_leads.columns = ["Nome","E-mail","Telefone","Tipo","Data","Convidados","Mensagem"]
            st.dataframe(df_leads, use_container_width=True, hide_index=True)

            if st.button("💬 Analisar leads com o agente", use_container_width=True, key="btn_leads_ia"):
                tipos_leads = {}
                for l in st.session_state.leads_landing:
                    tipos_leads[l["tipo"]] = tipos_leads.get(l["tipo"],0) + 1
                msg = f"Recebi {len(st.session_state.leads_landing)} leads. Distribuição por tipo: {tipos_leads}. Quais abordar primeiro e qual estratégia de vendas usar para cada tipo?"
                st.session_state.messages.append({"role":"user","content":msg})
                st.rerun()
        else:
            st.info("Nenhum lead recebido ainda. Compartilhe o link da landing page!")


# ── TAB: PIX & PAGAMENTO ──────────────────────────────────────────────────────
with tab_pix:
    st.markdown("### 💳 PIX & Pagamento")
    st.caption("Gere cobranças, QR Codes PIX e acompanhe pagamentos dos contratos")

    aba_pix1, aba_pix2, aba_pix3 = st.tabs(["💰 Gerar cobrança", "📊 Pagamentos", "⚙️ Configurar"])

    with aba_pix1:
        st.markdown("#### 💰 Gerar Cobrança PIX")

        col_p1, col_p2 = st.columns(2)
        with col_p1:
            pix_ev      = st.selectbox("Evento", [e["nome"] for e in st.session_state.eventos_cadastrados], key="pix_ev")
            pix_desc    = st.text_input("Descrição", placeholder="Ex: Sinal 30% — Casamento Silva", key="pix_desc")
            pix_valor   = st.number_input("Valor (R$)", min_value=1.0, value=5000.0, step=100.0, key="pix_valor")
        with col_p2:
            pix_cliente = st.text_input("Nome do cliente", key="pix_cli")
            pix_chave   = st.text_input("Sua chave PIX", placeholder="CPF, CNPJ, e-mail ou telefone", key="pix_chave")
            pix_tipo    = st.selectbox("Tipo de cobrança", ["Sinal / entrada","Parcela","Saldo final","Avulso"], key="pix_tipo")

        if st.button("💳 Gerar cobrança PIX", use_container_width=True, key="btn_gerar_pix"):
            if pix_chave and pix_valor:
                # Gera payload PIX estático (BR Code)
                def gerar_pix_payload(chave: str, nome: str, valor: float, desc: str, cidade: str = "SAO PAULO") -> str:
                    def tlv(id_: str, val: str) -> str:
                        return f"{id_}{len(val):02d}{val}"
                    merchant_account = tlv("00","BR.GOV.BCB.PIX") + tlv("01", chave)
                    payload = (
                        tlv("00","01") +
                        tlv("26", merchant_account) +
                        tlv("52","0000") +
                        tlv("53","986") +
                        tlv("54", f"{valor:.2f}") +
                        tlv("58","BR") +
                        tlv("59", nome[:25].upper()) +
                        tlv("60", cidade[:15].upper()) +
                        tlv("62", tlv("05", desc[:20])) +
                        "6304"
                    )
                    # CRC16 CCITT
                    crc = 0xFFFF
                    for byte in payload.encode("utf-8"):
                        crc ^= byte << 8
                        for _ in range(8):
                            crc = (crc << 1) ^ 0x1021 if crc & 0x8000 else crc << 1
                        crc &= 0xFFFF
                    return payload + f"{crc:04X}"

                payload_pix = gerar_pix_payload(pix_chave, pix_cliente or "SPOTLIGHT EVENTOS", pix_valor, pix_desc or "Spotlight Eventos")
                st.session_state["pix_payload"] = payload_pix
                st.session_state["pix_info"] = {"evento":pix_ev,"valor":pix_valor,"cliente":pix_cliente,"desc":pix_desc,"tipo":pix_tipo}

                # Registra cobrança pendente
                if "pagamentos" not in st.session_state:
                    st.session_state.pagamentos = []
                import hashlib as _hs
                pix_id = _hs.md5(f"{pix_ev}{pix_cliente}{pix_valor}".encode()).hexdigest()[:8].upper()
                st.session_state.pagamentos.append({
                    "id": pix_id, "evento":pix_ev,"cliente":pix_cliente or "—",
                    "desc":pix_desc,"tipo":pix_tipo,"valor":pix_valor,"status":"⏳ Aguardando","data":datetime.today().strftime("%d/%m/%Y"),
                })
                st.success(f"✅ Cobrança gerada! ID: {pix_id}")
            else:
                st.warning("Preencha a chave PIX e o valor.")

        if "pix_payload" in st.session_state:
            st.divider()
            info = st.session_state["pix_info"]
            col_qp1, col_qp2 = st.columns(2)

            with col_qp1:
                st.markdown("**📋 Copia e cola PIX:**")
                st.code(st.session_state["pix_payload"], language=None)
                st.download_button("⬇️ Baixar payload .txt", st.session_state["pix_payload"], file_name="pix_payload.txt", use_container_width=True)

            with col_qp2:
                st.markdown("**📱 QR Code PIX:**")
                try:
                    import qrcode as _qr
                    import base64 as _b64
                    from io import BytesIO as _Bio
                    qr_pix = _qr.make(st.session_state["pix_payload"])
                    buf_pix = _Bio()
                    qr_pix.save(buf_pix, format="PNG")
                    buf_pix.seek(0)
                    b64_pix = _b64.b64encode(buf_pix.read()).decode()
                    st.image(f"data:image/png;base64,{b64_pix}", width=200)
                    st.download_button("⬇️ Baixar QR Code", _b64.b64decode(b64_pix), file_name="qr_pix.png", mime="image/png", use_container_width=True)
                except ImportError:
                    st.info("Instale `qrcode pillow` para gerar o QR Code visual.")
                    st.markdown(f"[Gerar QR Code online](https://qr.io/?url={st.session_state['pix_payload'][:50]}...)")

            # Gera mensagem WhatsApp da cobrança com Groq
            if st.button("📲 Gerar mensagem de cobrança para WhatsApp", use_container_width=True, key="btn_wpp_pix"):
                info = st.session_state.get("pix_info", {"tipo":"cobrança","valor":0,"evento":"—","cliente":"cliente"})
                prompt_pix_wpp = f"Gere uma mensagem de WhatsApp profissional e cordial para cobrar o {info.get('tipo','cobrança').lower()} de R$ {info.get('valor',0):,.2f} do evento '{info.get('evento','—')}' para o cliente {info.get('cliente','cliente')}. Inclua instrução para usar o PIX copia-e-cola. Tom: formal mas amigável. Máximo 4 parágrafos."
                with st.spinner("Gerando com Groq..."):
                    msg_pix = ia_call(prompt_pix_wpp, max_tokens=400)
                    st.session_state["wpp_msg_gerada"] = msg_pix
                st.success("Mensagem gerada! Veja na aba WhatsApp.")

    with aba_pix2:
        st.markdown("#### 📊 Histórico de Pagamentos")
        pagamentos = st.session_state.get("pagamentos", [])

        if pagamentos:
                    # KPIs
            total_cobrado  = sum(p["valor"] for p in pagamentos)
            total_recebido = sum(p["valor"] for p in pagamentos if p["status"]=="✅ Pago")
            total_aguard   = sum(p["valor"] for p in pagamentos if p["status"]=="⏳ Aguardando")

            pp1,pp2,pp3 = st.columns(3)
            pp1.metric("💰 Total cobrado",   f"R$ {total_cobrado:,.0f}".replace(",","."))
            pp2.metric("✅ Recebido",        f"R$ {total_recebido:,.0f}".replace(",","."))
            pp3.metric("⏳ Aguardando",      f"R$ {total_aguard:,.0f}".replace(",","."))

            st.divider()
            for i, pg in enumerate(pagamentos):
                col_pg1,col_pg2,col_pg3,col_pg4,col_pg5 = st.columns([1,2,2,1,1])
                col_pg1.markdown(f"`{pg['id']}`")
                col_pg2.markdown(f"**{pg['cliente']}** · {pg['evento'][:20]}")
                col_pg3.markdown(f"{pg['tipo']} · R$ {pg['valor']:,.0f}".replace(",","."))
                col_pg4.markdown(pg["status"])
                if pg["status"] != "✅ Pago":
                    if col_pg5.button("✅ Pago", key=f"pg_ok_{i}", use_container_width=True):
                        st.session_state.pagamentos[i]["status"] = "✅ Pago"
                        st.rerun()
                else:
                    col_pg5.markdown("✅")
        else:
            st.info("Nenhuma cobrança gerada ainda.")

    with aba_pix3:
        st.markdown("#### ⚙️ Configurar dados PIX")
        st.info("Configure sua chave PIX para gerar cobranças automaticamente.")
        pix_chave_conf = st.text_input("Chave PIX padrão", value=st.session_state.get("pix_chave_conf",""), placeholder="seu@email.com ou CPF/CNPJ", key="pix_chave_conf_in")
        pix_nome_conf  = st.text_input("Nome do recebedor (como aparece no PIX)", value=st.session_state.get("pix_nome_conf","SPOTLIGHT EVENTOS"), key="pix_nome_conf_in")
        pix_cidade_conf = st.text_input("Cidade", value=st.session_state.get("pix_cidade_conf","SAO PAULO"), key="pix_cidade_conf_in")
        if st.button("💾 Salvar dados PIX", use_container_width=True, key="btn_save_pix_conf"):
            st.session_state["pix_chave_conf"]  = pix_chave_conf
            st.session_state["pix_nome_conf"]   = pix_nome_conf
            st.session_state["pix_cidade_conf"] = pix_cidade_conf
            st.success("✅ Dados PIX salvos!")


# ── TAB: SCORING DE LEADS ─────────────────────────────────────────────────────
with tab_scoring:
    st.markdown("### 🎯 Scoring de Leads com IA")
    st.caption("O Groq analisa cada lead e cliente do CRM e atribui uma pontuação de 0 a 100")

    aba_sc1, aba_sc2 = st.tabs(["🤖 Análise automática", "📊 Ranking"])

    with aba_sc1:
        st.markdown("#### 🤖 Analisar leads com Groq")
        st.info("O Groq analisa cada prospect do CRM com base em: tipo de evento, orçamento estimado, histórico, comportamento e urgência.")

        # Mostra apenas prospects e leads
        prospects_crm = [c for c in st.session_state.crm_clientes if c["status"] in ["Prospect","Ativo"]]

        if not prospects_crm:
            st.warning("Nenhum cliente no CRM para analisar.")
        else:
            if "scores" not in st.session_state:
                st.session_state.scores = {}

            col_sc1, col_sc2 = st.columns(2)
            with col_sc1:
                cliente_sel = st.selectbox("Analisar cliente", [c["nome"] for c in prospects_crm], key="sc_cli")
            with col_sc2:
                st.markdown("&nbsp;")
                analisar_todos = st.button("🤖 Analisar TODOS com Groq", use_container_width=True, key="btn_score_all")

            cli_data = next((c for c in prospects_crm if c["nome"] == cliente_sel), {})

            if st.button(f"🎯 Analisar {cliente_sel}", use_container_width=True, key="btn_score_one") or analisar_todos:
                clientes_analisar = prospects_crm if analisar_todos else [cli_data]

                for cli in clientes_analisar:
                    # Busca kanban info
                    kanban_info = next((c for col in st.session_state.kanban.values() for c in col if c.get("contato","") == cli.get("email","")), {})

                    prompt_score = f"""Você é um especialista em vendas de eventos privados. Analise este prospect e retorne APENAS um JSON válido, sem texto extra:

DADOS DO PROSPECT:
- Nome: {cli['nome']}
- Empresa: {cli.get('empresa','—')}
- Tipo de evento: {cli['tipo']}
- Status: {cli['status']}
- Eventos realizados: {cli.get('eventos',0)}
- Valor histórico: R$ {cli.get('valor_total',0):,.0f}
- Última interação: {cli.get('ultima_interacao','—')}
- Notas: {cli.get('notas','—')}
- Etapa no funil: {kanban_info.get('coluna','Não está no funil')}
- Valor estimado no funil: R$ {kanban_info.get('valor',0):,.0f}

Retorne APENAS este JSON (sem markdown, sem explicação):
{{"score": 75, "classificacao": "Quente", "motivos": ["motivo 1", "motivo 2", "motivo 3"], "proxima_acao": "ação recomendada", "urgencia": "Alta"}}

Classificações possíveis: Frio (0-30), Morno (31-60), Quente (61-80), Muito Quente (81-100)"""

                    with st.spinner(f"Analisando {cli['nome']}..."):
                        resp_score = ia_call(prompt_score, max_tokens=300)
                        try:
                            import re as _re
                            json_match = _re.search(r'\{.*\}', resp_score, _re.DOTALL)
                            if json_match:
                                score_data = json.loads(json_match.group())
                                st.session_state.scores[cli["nome"]] = score_data
                        except Exception:
                            st.session_state.scores[cli["nome"]] = {
                                "score": 50, "classificacao": "Morno",
                                "motivos": ["Análise indisponível"], "proxima_acao": "Entrar em contato",
                                "urgencia": "Média"
                            }

                st.success("✅ Análise concluída!")
                st.rerun()

            # Mostra resultado do cliente selecionado
            if cliente_sel in st.session_state.get("scores", {}):
                sc = st.session_state.scores[cliente_sel]
                score_val = sc.get("score", 0)
                classif   = sc.get("classificacao","—")
                cor_score = {"Frio":"#6B7280","Morno":"#1A56DB","Quente":"#B8860B","Muito Quente":"#C2185B"}.get(classif,"#534AB7")

                st.divider()
                col_s1, col_s2, col_s3 = st.columns(3)
                col_s1.markdown(f"""<div style="text-align:center;background:{cor_score};color:#fff;border-radius:12px;padding:20px">
<div style="font-size:48px;font-weight:800">{score_val}</div>
<div style="font-size:14px;margin-top:4px">{classif}</div>
</div>""", unsafe_allow_html=True)
                col_s2.metric("⚡ Urgência", sc.get("urgencia","—"))
                col_s2.markdown("**🎯 Próxima ação:**")
                col_s2.info(sc.get("proxima_acao","—"))
                with col_s3:
                    st.markdown("**✅ Motivos do score:**")
                    for m in sc.get("motivos",[]):
                        st.markdown(f"• {m}")

                st.progress(score_val/100, text=f"Score: {score_val}/100")

                if st.button("💬 Pedir estratégia completa ao Groq", use_container_width=True, key="btn_estrategia"):
                    cli_data_strat = next((c for c in st.session_state.crm_clientes if c["nome"] == cliente_sel), {})
                    msg = f"Crie uma estratégia de vendas detalhada para o prospect {cliente_sel} (score {score_val}/100 — {classif}). Tipo de evento: {cli_data_strat.get('tipo','—')}. Inclua: abordagem inicial, argumentos de venda, objeções prováveis e como contorná-las, proposta ideal e timing."
                    st.session_state.messages.append({"role":"user","content":msg})
                    st.rerun()

    with aba_sc2:
        st.markdown("#### 📊 Ranking de Leads")
        scores = st.session_state.get("scores",{})

        if scores:
            ranking = sorted(scores.items(), key=lambda x: x[1].get("score",0), reverse=True)
            dados_rank = []
            for nome, sc in ranking:
                score_val = sc.get("score",0)
                classif   = sc.get("classificacao","—")
                cor_score = {"Frio":"🔵","Morno":"🟡","Quente":"🟠","Muito Quente":"🔴"}.get(classif,"⚪")
                dados_rank.append({
                    "Posição": f"#{len(dados_rank)+1}",
                    "Cliente": nome,
                    "Score": score_val,
                    "Classificação": f"{cor_score} {classif}",
                    "Urgência": sc.get("urgencia","—"),
                    "Próxima ação": sc.get("proxima_acao","—")[:50],
                })
            df_rank = pd.DataFrame(dados_rank)
            st.dataframe(df_rank, use_container_width=True, hide_index=True)

            # Gráfico de barras
            df_chart = pd.DataFrame({"Score": {r["Cliente"]: r["Score"] for r in dados_rank}})
            st.bar_chart(df_chart, height=250)

            if st.button("💬 Pedir plano de ação para os top 3 leads", use_container_width=True, key="btn_top3"):
                top3 = [r["Cliente"] for r in dados_rank[:3]]
                msg = f"Crie um plano de ação semanal para converter os 3 leads mais quentes: {', '.join(top3)}. Para cada um, sugira a abordagem ideal, canal de contato (WhatsApp, e-mail, reunião) e argumentos personalizados."
                st.session_state.messages.append({"role":"user","content":msg})
                st.rerun()
        else:
            st.info("Nenhum lead analisado ainda. Use a aba 'Análise automática' para pontuar seus prospects.")

            # Preview do que vai aparecer
            st.markdown("**📋 Como funciona:**")
            st.markdown("""
1. Vá na aba **Análise automática**
2. Clique em **Analisar TODOS com Groq**
3. O Groq analisa cada prospect e atribui uma pontuação de 0-100
4. Aqui aparece o ranking com os leads mais quentes no topo
5. Use o plano de ação para saber exatamente o que fazer com cada um
""")
