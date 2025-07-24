
# app_streamlit.py
import streamlit as st
import sqlite3
from werkzeug.security import check_password_hash
import pandas as pd # Will be needed for data display
import plotly.express as px # Will be needed for graphs
import os # Needed for file path checks
import time # Needed for time.strftime if pandas is not available

# Define the database path relative to the app's directory in the deployment environment
# This will create/look for database.db in the root of the deployed app's filesystem.
# WARNING: Data will NOT be persistent across deployments/restarts on ephemeral filesystems like Streamlit Cloud.
db_path = 'database.db' # Changed from '/content/database.db'

# Function to get database connection
def get_db_connection():
    conn = sqlite3.connect(db_path)
    return conn

# Ensure the database and default admin user exist and has the correct schema
# This function should be called every time the app starts to ensure the DB exists
# and create it if necessary.
def setup_database():
    try:
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

        # --- Add 'observacao' column if it doesn't exist ---
        # Check if the column exists
        c.execute("PRAGMA table_info(ordens_servico);")
        cols = [column[1] for column in c.fetchall()]
        if 'observacao' not in cols:
            c.execute('ALTER TABLE ordens_servico ADD COLUMN observacao TEXT')
            conn.commit()
            st.sidebar.info("Coluna 'observacao' adicionada à tabela 'ordens_servico'.") # Use sidebar for setup messages
        # --- End Add 'observacao' column ---


        # Add default admin user if not exists
        # Check if admin exists before inserting
        c.execute('SELECT COUNT(*) FROM users WHERE username = "admin"')
        if c.fetchone()[0] == 0:
            # Generate password hash for 'ilumina2025'
            from werkzeug.security import generate_password_hash
            admin_password_hash = generate_password_hash('ilumina2025')
            # Use time.strftime for date format consistency, less dependency on pandas
            created_at = time.strftime('%d/%m/%Y')

            c.execute('''INSERT INTO users (username, password, role, created_at) VALUES (?, ?, ?, ?)''',
                      ('admin', admin_password_hash, 'Administrador', created_at))
            conn.commit()
            st.sidebar.success("Default admin user created (user: admin, pass: ilumina2025)") # Use Streamlit sidebar for messages
        conn.close()
        # st.sidebar.info("Database setup complete.") # Optional info message
    except Exception as e:
        st.sidebar.error(f"Error during database setup: {e}")


# Run database setup on every app startup
setup_database()


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
        # Check if the database file exists before attempting connection
        # The setup_database function should create it if it doesn't exist,
        # but a quick check before login attempt is safer.
        if not os.path.exists(db_path):
             st.error(f"Database file not found at {db_path}. Attempting setup now...")
             setup_database() # Try setting up again just in case
             if not os.path.exists(db_path):
                 st.error("Database file still not found after setup attempt.")
                 return # Stop if DB still not created


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
            st.rerun() # Rerun the app to go to the main page
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
        st.rerun()

    st.title("Dashboard")

    # Check if the database file exists before attempting connection
    if not os.path.exists(db_path):
        st.error(f"Database file not found at {db_path}. Please ensure database setup runs correctly on startup.")
        st.stop() # Stop execution if DB is missing

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
        all_zones = ['Todas as Zonas'] + list(df_os['zona'].unique()) if 'zona' in df_os.columns and not df_os['zona'].empty else ['Todas as Zonas']
        zona_filter = st.selectbox('Zona:', all_zones)
    with col_filter2:
        all_statuses = ['Todos'] + list(df_os['status'].unique()) if 'status' in df_os.columns and not df_os['status'].empty else ['Todos']
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
    # Include 'observacao' in the displayed columns
    display_columns = ['protocolo', 'nome', 'endereco', 'zona', 'status', 'responsavel', 'observacao']
    # Ensure columns exist in the filtered_df before selecting
    display_columns = [col for col in display_columns if col in filtered_df.columns]

    # --- Action Buttons (Implementing status change and delete) ---
    # Since Streamlit re-runs the script on every interaction, managing state for
    # individual row buttons requires a different pattern than Flask/Colab.
    # We can add buttons/forms within the dataframe row using st.columns or iterate
    # over rows and create inputs/buttons. Iterating is more flexible for actions.

    st.write("---") # Separator
    st.subheader("Detalhes e Ações por Ordem de Serviço")

    # Re-fetch data to ensure we have the latest state after potential actions
    conn = get_db_connection()
    df_os_actions = pd.read_sql_query('SELECT * FROM ordens_servico', conn)
    conn.close()

    # Ensure 'observacao' is a string and handle potential None values for display/editing
    if 'observacao' in df_os_actions.columns:
         df_os_actions['observacao'] = df_os_actions['observacao'].fillna('').astype(str)
    else:
         # If 'observacao' column was just added and DB was empty, it might not appear in df_os_actions.columns
         # Add it with empty strings if missing.
         df_os_actions['observacao'] = ''


    # Iterate through filtered rows to display details and action buttons
    if not filtered_df.empty:
        for index, row in filtered_df.iterrows():
            st.write(f"**Protocolo:** {row['protocolo']}")
            st.write(f"**Nome:** {row['nome']}")
            st.write(f"**Endereço:** {row['endereco']}")
            st.write(f"**Zona:** {row['zona']}")
            st.write(f"**Status:** {row['status']}")
            st.write(f"**Responsável:** {row['responsavel']}")

            # Add Observation field (editable)
            # Use a unique key for each text_area based on the row index or protocol
            current_observation = row.get('observacao', '') # Get observation, default to empty string if column missing
            new_observation = st.text_area(f"Observação (Protocolo {row['protocolo']}):", value=current_observation, key=f"obs_{row['protocolo']}")

            # Action Buttons: Start, Complete, Revert, Delete
            col_actions1, col_actions2, col_actions3, col_actions4 = st.columns(4)
            action_taken = False # Flag to trigger rerun after an action

            # Update Observation Button (only if observation changed)
            if new_observation != current_observation:
                 if st.button("Salvar Observação", key=f"save_obs_{row['protocolo']}"):
                     conn = get_db_connection()
                     c = conn.cursor()
                     c.execute('UPDATE ordens_servico SET observacao = ? WHERE protocolo = ?', (new_observation, row['protocolo']))
                     conn.commit()
                     conn.close()
                     st.success(f"Observação para {row['protocolo']} salva.")
                     action_taken = True # Trigger rerun
            else:
                 # If observation didn't change, show a disabled or different button/message
                 st.write("Observação atualizada.") # Or a disabled button placeholder

            # Status Change Buttons
            if row['status'] == 'pendente':
                if col_actions1.button("Iniciar Tratamento", key=f"start_{row['protocolo']}"):
                    # Need a way to select responsible user in Streamlit - for now, use logged-in user
                    responsavel = st.session_state.get('username', 'Desconhecido') # Get logged-in username
                    conn = get_db_connection()
                    c = conn.cursor()
                    c.execute('UPDATE ordens_servico SET status = ?, responsavel = ? WHERE protocolo = ?', ('em-andamento', responsavel, row['protocolo']))
                    conn.commit()
                    conn.close()
                    st.success(f"OS {row['protocolo']} marcada como 'em-andamento'.")
                    action_taken = True # Trigger rerun

            elif row['status'] == 'em-andamento':
                if col_actions1.button("Marcar como Concluída", key=f"complete_{row['protocolo']}"):
                    conn = get_db_connection()
                    c = conn.cursor()
                    c.execute('UPDATE ordens_servico SET status = ? WHERE protocolo = ?', ('concluida', row['protocolo']))
                    conn.commit()
                    conn.close()
                    st.success(f"OS {row['protocolo']} marcada como 'concluída'.")
                    action_taken = True # Trigger rerun
                if col_actions2.button("Reverter para Pendente", key=f"revert_pending_{row['protocolo']}"):
                     conn = get_db_connection()
                     c = conn.cursor()
                     c.execute('UPDATE ordens_servico SET status = ?, responsavel = ? WHERE protocolo = ?', ('pendente', None, row['protocolo'])) # Clear responsible on revert
                     conn.commit()
                     conn.close()
                     st.success(f"OS {row['protocolo']} revertida para 'pendente'.")
                     action_taken = True # Trigger rerun


            elif row['status'] == 'concluida':
                 if col_actions1.button("Reverter para Em Andamento", key=f"revert_inprogress_{row['protocolo']}"):
                      # Need responsible user if reverting to 'em-andamento' - use logged-in user
                      responsavel = st.session_state.get('username', 'Desconhecido') # Get logged-in username
                      conn = get_db_connection()
                      c = conn.cursor()
                      c.execute('UPDATE ordens_servico SET status = ?, responsavel = ? WHERE protocolo = ?', ('em-andamento', responsavel, row['protocolo']))
                      conn.commit()
                      conn.close()
                      st.success(f"OS {row['protocolo']} revertida para 'em-andamento'.")
                      action_taken = True # Trigger rerun


            # Delete Button (Admin only)
            if st.session_state.get('role') == 'Administrador':
                if col_actions4.button("Excluir OS", key=f"delete_{row['protocolo']}"):
                    # Add confirmation logic
                    confirm_delete = st.sidebar.radio(f"Confirmar exclusão da OS {row['protocolo']}?", ('Não', 'Sim'), key=f"confirm_delete_{row['protocolo']}")
                    if confirm_delete == 'Sim':
                        conn = get_db_connection()
                        c = conn.cursor()
                        c.execute('DELETE FROM ordens_servico WHERE protocolo = ?', (row['protocolo'],))
                        conn.commit()
                        conn.close()
                        st.success(f"OS {row['protocolo']} excluída.")
                        action_taken = True # Trigger rerun
                    else:
                        st.sidebar.info("Exclusão cancelada.")


            st.write("---") # Separator between OS entries

        if action_taken:
            st.rerun() # Rerun the script to show updated data and buttons

    else:
        st.info("Nenhuma Ordem de Serviço encontrada com os filtros aplicados.")


    # --- Upload CSV ---
    st.subheader("Upload de Ordens de Serviço (CSV)")
    uploaded_file = st.file_uploader("Escolha um arquivo CSV", type="csv", key="csv_uploader") # Add key
    if uploaded_file is not None:
        try:
            df_upload = pd.read_csv(uploaded_file)
            st.write("Prévia do CSV uploaded:")
            st.dataframe(df_upload.head())

            if st.button("Processar e Substituir Dados Existentes", key="process_csv_button"): # Add key
                 # Check if the database file exists before attempting connection
                 if not os.path.exists(db_path):
                     st.error(f"Database file not found at {db_path}. Attempting setup now...")
                     setup_database() # Try setting up again just in case
                     if not os.path.exists(db_path):
                         st.error("Database file still not found after setup attempt.")
                         # st.experimental_rerun() # Might be stuck in a loop, better to stop or return
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
                     st.rerun() # Use st.rerun()
                     return

                 # If 'observacao' is in the uploaded CSV, include it. Otherwise, it will be None by default in the DB.
                 optional_columns = ['observacao']
                 for col in optional_columns:
                      if col in df_upload.columns:
                           required_columns.append(col)
                           # Ensure the column exists in df_upload before selecting it
                           if col not in df_upload.columns:
                                df_upload[col] = None # Add column with None if it was missing initially but added to required_columns

                 df_to_insert = df_upload[required_columns]


                 try:
                    df_to_insert.to_sql('ordens_servico', conn, if_exists='replace', index=False)
                    conn.commit()
                    st.success(f"{len(df_to_insert)} registros importados com sucesso!")
                    st.rerun() # Use st.rerun() to refresh data display
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
            st.info("Coluna 'zona' não encontrada nos dados para gerar o gráfico por zona.")

        # --- New Graph: OS by Date ---
        # This requires a date column in the 'ordens_servico' table.
        # Assuming a column named 'created_at' or similar exists and contains dates.
        # If your actual DB uses a different column name or format, adjust the query.
        # We will try to get data and plot it if a suitable date column is found.

        conn = get_db_connection()
        c = conn.cursor()
        c.execute('PRAGMA table_info(ordens_servico);')
        cols = [col[1] for col in c.fetchall()]
        date_column = None
        for potential_col in ['created_at', 'data_registro', 'data_criacao', 'data']: # Add other potential date column names
            if potential_col in cols:
                date_column = potential_col
                break
        conn.close() # Close connection after checking schema

        if date_column:
            conn = get_db_connection()
            # Read data specifically for the date graph
            try:
                # Ensure the date column is treated as datetime by pandas for plotting
                df_date_graph = pd.read_sql_query(f'SELECT {date_column} FROM ordens_servico WHERE {date_column} IS NOT NULL', conn)
                conn.close()

                if not df_date_graph.empty:
                    # Convert the date column to datetime objects
                    # Use errors='coerce' to turn invalid date formats into NaT (Not a Time)
                    df_date_graph['date'] = pd.to_datetime(df_date_graph[date_column], errors='coerce')
                    # Drop rows where date conversion failed
                    df_date_graph.dropna(subset=['date'], inplace=True)

                    if not df_date_graph.empty:
                        # Group by date and count
                        date_counts = df_date_graph['date'].dt.date.value_counts().reset_index()
                        date_counts.columns = ['date', 'count']
                        # Sort by date for proper time series plotting
                        date_counts['date'] = pd.to_datetime(date_counts['date'])
                        date_counts = date_counts.sort_values('date')

                        fig_date = px.line(date_counts, x='date', y='count', title='OS ao Longo do Tempo',
                                           color_discrete_sequence=['#FF6384'])
                        st.plotly_chart(fig_date, use_container_width=True)
                    else:
                         st.info(f"Nenhum dado válido na coluna '{date_column}' para exibir o gráfico por data após conversão para datetime.")

                else:
                    st.info(f"Nenhum dado com '{date_column}' encontrado na tabela para o gráfico por data.")

            except Exception as e:
                 st.error(f"Erro ao gerar gráfico por data usando a coluna '{date_column}': {e}")
                 if conn: conn.close() # Ensure connection is closed on error

        else:
            st.warning("Nenhuma coluna de data adequada ('created_at', 'data_registro', etc.) encontrada na tabela 'ordens_servico' para gerar o gráfico por data.")


        # Placeholder for Activity and Trend graphs (requires date/time columns and more complex logic)
        # st.info("Gráficos de Atividade Semanal e Tendência Mensal requerem colunas de data/hora nos dados e lógica de agregação por período.")


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
                        created_at = time.strftime('%d/%m/%Y')
                    except:
                         import time
                         created_at = time.strftime('%d/%m/%Y')

                    c.execute('''INSERT INTO users (username, password, role, created_at) VALUES (?, ?, ?, ?)''',
                              (new_username, hashed_password, new_role, created_at))
                    conn.commit()
                    st.success(f"Usuário '{new_username}' criado com sucesso!")
                    conn.close()
                    st.rerun() # Use st.rerun() # Refresh user list


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
                     st.rerun() # Use st.rerun() # Refresh

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
# Removed explicit sqlite3 check as it's built-in
try:
    import streamlit as st
    import pandas as pd
    import sqlite3
    from werkzeug.security import check_password_hash
    import plotly.express as px
    import os # Ensure os is imported for path checks
    import time # Ensure time is imported for date handling if needed
except ImportError as e:
    st.error(f"Parece que as bibliotecas necessárias não estão instaladas. Erro: {e}")
    st.stop() # Stop the app if imports fail


# Main application flow: Login or Dashboard
if st.session_state['logged_in']:
    main_dashboard()
else:
    login_page()

