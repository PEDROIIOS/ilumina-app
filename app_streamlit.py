# app_streamlit.py
import streamlit as st
import sqlite3
from werkzeug.security import check_password_hash, generate_password_hash
import pandas as pd
import plotly.express as px
import os
import time

# Define the database path
db_path = 'database.db'

# Database connection

def get_db_connection():
    return sqlite3.connect(db_path)

# Setup database
def setup_database():
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE NOT NULL,
                        password TEXT NOT NULL,
                        role TEXT NOT NULL,
                        created_at TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS ordens_servico (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        protocolo TEXT UNIQUE NOT NULL,
                        nome TEXT,
                        endereco TEXT,
                        zona TEXT,
                        status TEXT,
                        responsavel TEXT,
                        observacao TEXT)''')
        c.execute('SELECT COUNT(*) FROM users WHERE username = "admin"')
        if c.fetchone()[0] == 0:
            admin_hash = generate_password_hash('ilumina2025')
            created_at = time.strftime('%d/%m/%Y')
            c.execute('INSERT INTO users (username, password, role, created_at) VALUES (?, ?, ?, ?)',
                      ('admin', admin_hash, 'Administrador', created_at))
            st.sidebar.success("Usuário admin criado (senha: ilumina2025)")
        conn.commit()
        conn.close()
        st.sidebar.info("Setup do banco de dados executado.")
    except Exception as e:
        st.sidebar.error(f"Erro no setup do banco: {e}")

# Executar setup do banco
setup_database()

# Configurar Streamlit
st.set_page_config(page_title="Ilumina Pedro II Dashboard", layout="wide")

# Login page
def login_page():
    st.title("Acesso Restrito")
    username = st.text_input("Usuário")
    password = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        if not os.path.exists(db_path):
            setup_database()
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('SELECT * FROM users WHERE username = ?', (username,))
        user = c.fetchone()
        conn.close()
        if user and check_password_hash(user[2], password):
            st.session_state['logged_in'] = True
            st.session_state['username'] = user[1]
            st.session_state['role'] = user[3]
            st.rerun()
        else:
            st.error("Credenciais inválidas")

# Dashboard
def main_dashboard():
    st.sidebar.title(f"Bem-vindo, {st.session_state['username']}")
    st.sidebar.write(f"Função: {st.session_state['role']}")
    if st.sidebar.button("Sair"):
        for k in ['logged_in', 'username', 'role']:
            st.session_state.pop(k, None)
        st.rerun()

    st.title("Dashboard")

    if not os.path.exists(db_path):
        st.error("Banco de dados não encontrado.")
        st.stop()

    conn = get_db_connection()
    df_os = pd.read_sql_query('SELECT * FROM ordens_servico', conn)
    conn.close()

    # Métricas
    st.subheader("Métricas")
    total = len(df_os)
    pend = len(df_os[df_os.get('status') == 'pendente'])
    andamento = len(df_os[df_os.get('status') == 'em-andamento'])
    concl = len(df_os[df_os.get('status') == 'concluida'])
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total", total)
    col2.metric("Pendentes", pend)
    col3.metric("Em Andamento", andamento)
    col4.metric("Concluídas", concl)

    # Filtros
    st.subheader("Filtros")
    zona = st.selectbox("Zona", ['Todas'] + df_os['zona'].dropna().unique().tolist() if 'zona' in df_os else ['Todas'])
    status = st.selectbox("Status", ['Todos'] + df_os['status'].dropna().unique().tolist() if 'status' in df_os else ['Todos'])
    termo = st.text_input("Buscar por protocolo ou nome")
    filtrado = df_os.copy()
    if zona != 'Todas': filtrado = filtrado[filtrado['zona'] == zona]
    if status != 'Todos': filtrado = filtrado[filtrado['status'] == status]
    if termo:
        filtrado = filtrado[filtrado['protocolo'].str.contains(termo, case=False, na=False) |
                            filtrado['nome'].str.contains(termo, case=False, na=False)]

    st.subheader("Ordens de Serviço")
    st.dataframe(filtrado)

    # Upload CSV
    st.subheader("Importar CSV")
    uploaded_file = st.file_uploader("Selecionar CSV", type="csv")
    if uploaded_file:
        try:
            df_csv = pd.read_csv(uploaded_file)
            st.write("Prévia:", df_csv.head())
            if st.button("Substituir Dados"):
                conn = get_db_connection()
                c = conn.cursor()
                c.execute('DELETE FROM ordens_servico')
                conn.commit()
                df_csv.columns = df_csv.columns.str.lower()
                if 'zona' not in df_csv.columns:
                    df_csv['zona'] = 'Não especificada'
                df_csv.to_sql('ordens_servico', conn, if_exists='append', index=False)
                conn.close()
                st.success("Importação realizada com sucesso.")
                st.rerun()
        except Exception as e:
            st.error(f"Erro no upload: {e}")

# Navegação
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if st.session_state['logged_in']:
    main_dashboard()
else:
    login_page()
