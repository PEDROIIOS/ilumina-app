
# app_streamlit.py
import streamlit as st
import sqlite3
from werkzeug.security import check_password_hash
import pandas as pd # Will be needed for data display
import plotly.express as px # Will be needed for graphs
import os # Needed for file path checks

# Define the database path (adjust if necessary for deployment environment)
# For Colab, it's /content/database.db
# For Streamlit Cloud, you might need to handle this differently (e.g., using secrets, or a persistent storage method)
db_path = '/content/database.db' # Keep this for Colab testing

# Function to get database connection
def get_db_connection():
    conn = sqlite3.connect(db_path)
    return conn

# Ensure the database and default admin user exist
# This part should ideally be run once during setup, not every time the app loads
# In Streamlit, this might go into a setup script or be handled on first run logic
def setup_database():
    conn = get_db_connection()
    c = conn.cursor()
    # Create users table if it doesn't exist
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL,
            created_at TEXT
        )
    ''')
    # Create ordens_servico table if it doesn't exist
    c.execute('''
        CREATE TABLE IF NOT EXISTS ordens_servico (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            protocolo TEXT UNIQUE NOT NULL,
            nome TEXT,
            endereco TEXT,
            zona TEXT,
            status TEXT,
            responsavel TEXT
        )
    ''')
    # Add default admin user if not exists
    # Check if admin exists before inserting
    c.execute('SELECT COUNT(*) FROM users WHERE username = "admin"')
    if c.fetchone()[0] == 0:
        # Generate password hash for 'ilumina2025'
        # Requires werkzeug.security.generate_password_hash
        from werkzeug.security import generate_password_hash
        admin_password_hash = generate_password_hash('ilumina2025')
        # Check if pandas is available for Timestamp, otherwise use simple time
        try:
            created_at = pd.Timestamp.now().strftime('%d/%m/%Y')
        except:
            import time
            created_at = time.strftime('%d/%m/%Y')

        c.execute('''INSERT INTO users (username, password, role, created_at) VALUES (?, ?, ?, ?)''',
                  ('admin', admin_password_hash, 'Administrador', created_at))
        conn.commit()
        print("Default admin user created.")
    conn.close()

# Run database setup on first load (or in a separate setup step)
# Check if db_path exists before trying to set up the database
if os.path.exists(db_path):
    setup_database()
else:
    st.error(f"Database file not found at {db_path}. Please run the initial setup cells.")


# --- Streamlit App ---

st.set_page_config(page_title="Ilumina Pedro II Dashboard", layout="wide")

# Custom CSS for styling (optional but helps with branding)
st.markdown("""
<style>
.css-18e3th9 { # Main content container
    padding-top: 0rem;
    padding-bottom: 10rem;
    padding-left: 5rem;
    padding-right: 5rem;
}
.css-1d3z3hw { # Header container
    padding-top: 3.5rem;
    padding-right: 1rem;
    padding-bottom: 3.5rem;
    padding-left: 1rem;
}
.stButton>button {
    background-color: #1E3A8A; /* primary_color */
    color: white;
}
.stTextInput>div>div>input {
    border-color: #1E3A8A;
}
/* Add more styling as needed */
</style>
""", unsafe_allow_html=True)


# --- Login Page ---
def login_page():
    st.title("Acesso Restrito - Ilumina Pedro II")

    username = st.text_input("Usuário:")
    password = st.text_input("Senha:", type="password")

    if st.button("Entrar"):
        if not os.path.exists(db_path):
            st.error(f"Database file not found at {db_path}. Please run the initial setup cells.")
            return

        conn = get_db_connection()
        c = conn.cursor()
        c.execute('SELECT * FROM users WHERE username = ?', (username,))
        user_row = c.fetchone()
        conn.close()

        if user_row and check_password_hash(user_row[2], password):
            st.session_state['logged_in'] = True
            st.session_state['username'] = user_row[1]
            st.session_state['role'] = user_row[3]
            st.success(f"Bem-vindo, {st.session_state['username']} ({st.session_state['role']})!")
            st.experimental_rerun() # Rerun the app to go to the main page
        else:
            st.error("Credenciais inválidas")

# --- Main Dashboard Page ---
def main_dashboard():
    st.sidebar.title(f"Bem-vindo, {st.session_state['username']}")
    st.sidebar.write(f"Função: {st.session_state['role']}")
    if st.sidebar.button("Sair"):
        st.session_state['logged_in'] = False
        del st.session_state['username']
        del st.session_state['role']
        st.experimental_rerun()

    st.title("Dashboard")

    if not os.path.exists(db_path):
        st.error(f"Database file not found at {db_path}. Please run the initial setup cells.")
        return

    conn = get_db_connection()
    df_os = pd.read_sql_query('SELECT * FROM ordens_servico', conn)
    conn.close()

    # --- Metrics ---
    st.subheader("Métricas")
    total_os = len(df_os)
    pendentes = len(df_os[df_os['status'] == 'pendente'])
    em_andamento = len(df_os[df_os['status'] == 'em-andamento'])
    concluidas = len(df_os[df_os['status'] == 'concluida'])

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(label="Total de OS", value=total_os)
    with col2:
        st.metric(label="Pendentes", value=pendentes)
    with col3:
        st.metric(label="Em Andamento", value=em_andamento)
    with col4:
        st.metric(label="Concluídas", value=concluidas)


    # --- Filters ---
    st.subheader("Filtros")
    col_filter1, col_filter2, col_filter3 = st.columns(3)
    with col_filter1:
        all_zones = ['Todas as Zonas'] + list(df_os['zona'].unique()) if 'zona' in df_os.columns else ['Todas as Zonas']
        zona_filter = st.selectbox('Zona:', all_zones)
    with col_filter2:
        all_statuses = ['Todos'] + list(df_os['status'].unique()) if 'status' in df_os.columns else ['Todos']
        status_filter = st.selectbox('Status:', all_statuses)
    with col_filter3:
        search_term = st.text_input('Buscar por Protocolo ou Nome:')

    filtered_df = df_os.copy()
    if zona_filter != 'Todas as Zonas':
        filtered_df = filtered_df[filtered_df['zona'] == zona_filter]
    if status_filter != 'Todos':
        filtered_df = filtered_df[filtered_df['status'] == status_filter]
    if search_term:
        filtered_df = filtered_df[
            filtered_df['protocolo'].astype(str).str.contains(search_term, case=False, na=False) |
            filtered_df['nome'].astype(str).str.contains(search_term, case=False, na=False)
        ]


    # --- Display Filtered Data ---
    st.subheader("Ordens de Serviço (Filtradas)")
    st.dataframe(filtered_df)


    # --- Action Buttons (Simplified for Streamlit) ---
    # For a full Streamlit app, actions like "Iniciar Tratamento" and "Excluir"
    # would require more complex state management and potentially separate pages or modals.
    # Here, we'll just demonstrate the Admin section and report generation.

    # --- Upload CSV ---
    st.subheader("Upload de Ordens de Serviço (CSV)")
    uploaded_file = st.file_uploader("Escolha um arquivo CSV", type="csv")
    if uploaded_file is not None:
        try:
            df_upload = pd.read_csv(uploaded_file)
            st.write("Prévia do CSV uploaded:")
            st.dataframe(df_upload.head())

            if st.button("Processar e Substituir Dados Existentes"):
                 if not os.path.exists(db_path):
                    st.error(f"Database file not found at {db_path}. Cannot upload.")
                    return

                 conn = get_db_connection()
                 # Convert column names to lowercase for case-insensitive matching
                 df_upload.columns = df_upload.columns.str.lower()
                 # Add 'zona' column if missing, with a default value
                 if 'zona' not in df_upload.columns:
                    df_upload['zona'] = 'Não Especificada' # Default value for missing zona

                 # Ensure only relevant columns are kept if there are extra columns in CSV
                 required_columns = ['protocolo', 'nome', 'endereco', 'zona', 'status', 'responsavel']
                 # Check if essential columns are present after lowercasing
                 essential_columns_present = all(col in df_upload.columns for col in ['protocolo', 'nome', 'endereco', 'status', 'responsavel'])

                 if not essential_columns_present:
                     missing_essential = [col for col in ['protocolo', 'nome', 'endereco', 'status', 'responsavel'] if col not in df_upload.columns]
                     st.error(f"Erro: Colunas essenciais faltando no CSV: {missing_essential}")
                     conn.close()
                     st.experimental_rerun()
                     return

                 df_to_insert = df_upload[required_columns]

                 try:
                    df_to_insert.to_sql('ordens_servico', conn, if_exists='replace', index=False)
                    conn.commit()
                    st.success(f"{len(df_to_insert)} registros importados com sucesso!")
                    st.experimental_rerun() # Rerun to refresh data display
                 except Exception as e:
                    st.error(f"Erro ao inserir dados no banco de dados: {e}")
                 finally:
                    conn.close()

        except Exception as e:
            st.error(f"Erro ao ler o arquivo CSV: {e}")


    # --- Graphs ---
    st.subheader("Gráficos")
    if not df_os.empty:
        # Distribution by Status
        status_counts = df_os['status'].value_counts().reset_index()
        status_counts.columns = ['status', 'count']
        fig_status = px.pie(status_counts, names='status', values='count', title='Distribuição por Status',
                            color_discrete_sequence=['#FF6384', '#36A2EB', '#FFCE56'])
        st.plotly_chart(fig_status, use_container_width=True)

        # OS by Zone
        if 'zona' in df_os.columns:
            zona_counts = df_os['zona'].value_counts().reset_index()
            zona_counts.columns = ['zona', 'count']
            fig_zona = px.bar(zona_counts, x='zona', y='count', title='OS por Zona',
                              color_discrete_sequence=['#36A2EB'])
            st.plotly_chart(fig_zona, use_container_width=True)
        else:
            st.warning("Coluna 'zona' não encontrada nos dados para gerar o gráfico por zona.")

        # Placeholder for Activity and Trend graphs (requires date/time columns)
        # You would need to add date/time columns to your ordens_servico table
        # and parse them correctly to create these graphs.
        st.info("Gráficos de Atividade Semanal e Tendência Mensal requerem colunas de data/hora nos dados.")

    else:
        st.info("Sem dados de Ordens de Serviço para exibir gráficos.")


    # --- Admin Section ---
    if st.session_state['role'] == 'Administrador':
        st.subheader("Administração de Usuários")
        # Placeholder for user management UI
        st.write("Funcionalidades para criar/gerenciar usuários aqui.")

        # Example: Display existing users (excluding password)
        if not os.path.exists(db_path):
            st.error(f"Database file not found at {db_path}. Cannot display users.")
        else:
            conn = get_db_connection()
            df_users = pd.read_sql_query('SELECT username, role, created_at FROM users', conn)
            conn.close()
            st.dataframe(df_users)

        # Placeholder for Create User form
        st.subheader("Criar Novo Usuário")
        new_username = st.text_input("Nome de Usuário (Novo):")
        new_password = st.text_input("Senha (Novo Usuário):", type="password")
        new_role = st.selectbox("Função (Novo Usuário):", ['Operador', 'Administrador'])

        if st.button("Criar Usuário"):
            if not new_username or not new_password:
                st.error("Nome de usuário e senha são obrigatórios.")
            elif not os.path.exists(db_path):
                 st.error(f"Database file not found at {db_path}. Cannot create user.")
            else:
                conn = get_db_connection()
                c = conn.cursor()
                # Check if username already exists
                c.execute('SELECT COUNT(*) FROM users WHERE username = ?', (new_username,))
                if c.fetchone()[0] > 0:
                    st.error("Nome de usuário já existe.")
                    conn.close()
                else:
                    hashed_password = generate_password_hash(new_password)
                    try:
                        created_at = pd.Timestamp.now().strftime('%d/%m/%Y')
                    except:
                         import time
                         created_at = time.strftime('%d/%m/%Y')

                    c.execute('''INSERT INTO users (username, password, role, created_at) VALUES (?, ?, ?, ?)''',
                              (new_username, hashed_password, new_role, created_at))
                    conn.commit()
                    st.success(f"Usuário '{new_username}' criado com sucesso!")
                    conn.close()
                    st.experimental_rerun() # Refresh user list


        # Placeholder for Change Password form
        st.subheader("Alterar Senha de Usuário")
        target_username_change = st.text_input("Nome de Usuário para Alterar Senha:")
        new_password_change = st.text_input("Nova Senha:", type="password")

        if st.button("Alterar Senha"):
             if not target_username_change or not new_password_change:
                 st.error("Nome de usuário e nova senha são obrigatórios.")
             elif not os.path.exists(db_path):
                 st.error(f"Database file not found at {db_path}. Cannot change password.")
             else:
                 conn = get_db_connection()
                 c = conn.cursor()
                 # Verify target user exists
                 c.execute('SELECT COUNT(*) FROM users WHERE username = ?', (target_username_change,))
                 if c.fetchone()[0] == 0:
                     st.error(f"Usuário '{target_username_change}' não encontrado.")
                     conn.close()
                 else:
                     hashed_password = generate_password_hash(new_password_change)
                     c.execute('UPDATE users SET password = ? WHERE username = ?', (hashed_password, target_username_change))
                     conn.commit()
                     st.success(f"Senha do usuário '{target_username_change}' alterada com sucesso!")
                     conn.close()
                     st.experimental_rerun() # Refresh

        # Placeholder for Delete OS button (Admin only) - requires more careful implementation
        # st.subheader("Excluir Ordem de Serviço")
        # os_to_delete = st.text_input("Protocolo da OS a Excluir:")
        # if st.button("Excluir OS"):
        #     # Implement deletion logic and confirmation
        #     pass # Placeholder


    # --- Report Generation ---
    st.subheader("Relatórios")
    if st.button("Gerar Relatório CSV"):
         if not os.path.exists(db_path):
             st.error(f"Database file not found at {db_path}. Cannot generate report.")
         else:
            conn = get_db_connection()
            df_report = pd.read_sql_query('SELECT * FROM ordens_servico', conn)
            conn.close()

            if not df_report.empty:
                # Convert DataFrame to CSV bytes
                csv_bytes = df_report.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="Download report.csv",
                    data=csv_bytes,
                    file_name='report.csv',
                    mime='text/csv'
                )
            else:
                st.info("Nenhum dado para gerar relatório.")


# --- Navigation Logic ---
# Initialize session state if not already present
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

# Check if required libraries are installed (basic check for Streamlit)
try:
    import streamlit as st
    import pandas as pd
    import sqlite3
    from werkzeug.security import check_password_hash
    import plotly.express as px
except ImportError:
    st.error("Parece que as bibliotecas necessárias não estão instaladas. Por favor, execute as células de instalação.")
    st.stop() # Stop the app if imports fail


if st.session_state['logged_in']:
    main_dashboard()
else:
    login_page()

