import os
import sqlite3
import streamlit as st
import pandas as pd
from datetime import datetime

# Paths and constants
DB_DIR = "./data"
DB_FILENAME = os.path.join(DB_DIR, "cash_custody.db")
UPLOAD_FOLDER = "./uploads/"
APP_TITLE = "Cash Custody Management System"
CREDITS = "Created by Ibrahim Elnagar, Operation Manager | NATGAS"

# Ensure required directories exist
os.makedirs(DB_DIR, exist_ok=True)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Initialize the database
def init_database():
    conn = sqlite3.connect(DB_FILENAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            balance REAL DEFAULT 0
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            type TEXT NOT NULL,
            description TEXT,
            amount REAL NOT NULL,
            from_account_id INTEGER,
            to_account_id INTEGER,
            file_path TEXT,
            FOREIGN KEY (from_account_id) REFERENCES accounts (id),
            FOREIGN KEY (to_account_id) REFERENCES accounts (id)
        )
    ''')
    conn.commit()
    conn.close()

# Fetch all accounts
def get_accounts():
    conn = sqlite3.connect(DB_FILENAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, balance FROM accounts")
    accounts = cursor.fetchall()
    conn.close()
    return [{"id": row[0], "name": row[1], "balance": row[2]} for row in accounts]

# Fetch all transactions
def get_transactions():
    conn = sqlite3.connect(DB_FILENAME)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT t.id, t.date, t.type, t.description, t.amount,
               a1.name AS from_account, a2.name AS to_account, t.file_path
        FROM transactions t
        LEFT JOIN accounts a1 ON t.from_account_id = a1.id
        LEFT JOIN accounts a2 ON t.to_account_id = a2.id
    ''')
    transactions = cursor.fetchall()
    conn.close()
    return transactions

# Add a new account
def add_account(name, balance):
    conn = sqlite3.connect(DB_FILENAME)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO accounts (name, balance) VALUES (?, ?)", (name, balance))
    conn.commit()
    conn.close()

# Add a new transaction
def add_transaction(transaction_data):
    """Add a new transaction and update account balances."""
    conn = sqlite3.connect(DB_FILENAME)
    cursor = conn.cursor()

    # Insert the transaction into the database
    cursor.execute('''
        INSERT INTO transactions (date, type, description, amount, from_account_id, to_account_id, file_path)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', transaction_data)

    # Update account balances for transfers and deposits
    transaction_type = transaction_data[1]
    amount = transaction_data[3]
    from_account_id = transaction_data[4]
    to_account_id = transaction_data[5]

    if transaction_type == "DEPOSIT":
        if to_account_id:
            cursor.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (amount, to_account_id))
        if from_account_id:
            cursor.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?", (amount, from_account_id))
    elif transaction_type == "TRANSFER":
        if from_account_id:
            cursor.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?", (amount, from_account_id))
        if to_account_id:
            cursor.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (amount, to_account_id))
    elif transaction_type == "EXPENSE":
        if from_account_id:
            cursor.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?", (amount, from_account_id))
        if to_account_id:
            cursor.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (amount, to_account_id))

    conn.commit()
    conn.close()

# Export transactions to Excel
def export_transactions():
    conn = sqlite3.connect(DB_FILENAME)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT t.date, t.type, t.description, t.amount,
               a1.name AS from_account, a2.name AS to_account, t.file_path
        FROM transactions t
        LEFT JOIN accounts a1 ON t.from_account_id = a1.id
        LEFT JOIN accounts a2 ON t.to_account_id = a2.id
    ''')
    transactions = cursor.fetchall()
    conn.close()
    df = pd.DataFrame(transactions, columns=[
        "Date", "Type", "Description", "Amount", "From Account", "To Account", "File Path"
    ])
    excel_path = os.path.join(UPLOAD_FOLDER, "transactions.xlsx")
    df.to_excel(excel_path, index=False)
    return excel_path

# Reset the application
def reset_application():
    if st.session_state.get("confirm_reset", False):
        conn = sqlite3.connect(DB_FILENAME)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM accounts")
        cursor.execute("DELETE FROM transactions")
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='accounts'")
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='transactions'")
        conn.commit()
        conn.close()
        st.success("Application reset successfully!")
        st.session_state["confirm_reset"] = False
        # Refresh accounts and transactions dynamically
        with accounts_placeholder.container():
            accounts = get_accounts()
            st.dataframe(pd.DataFrame(accounts))
        with transactions_placeholder.container():
            transactions = get_transactions()
            if transactions:
                df_transactions = pd.DataFrame(transactions, columns=[
                    "ID", "Date", "Type", "Description", "Amount", "From Account", "To Account", "File Path"
                ])
                df_transactions["File Link"] = df_transactions["File Path"].apply(
                    lambda x: f'<a href="file:///{os.path.abspath(x)}" target="_blank">📂 Open File</a>' if x else "No File"
                )
                st.dataframe(df_transactions)
            else:
                st.write("No transactions available.")
    else:
        st.session_state["confirm_reset"] = st.sidebar.button("Confirm Reset")
        if st.session_state["confirm_reset"]:
            st.warning("Are you sure you want to reset the application? This action cannot be undone.")

# Initialize the database before starting the app
init_database()

# Streamlit UI
st.title(APP_TITLE)
st.sidebar.header("Actions")
st.markdown(f"### {CREDITS}")

# Add custom CSS for headers and sidebar sections
st.markdown(
    """
    <style>
    .header {
        background-color: #4CAF50;
        color: white;
        padding: 10px;
        border-radius: 5px;
    }
    .sidebar-section {
        background-color: #f0f0f0;
        padding: 10px;
        border-radius: 5px;
        margin-bottom: 10px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Enhanced UI Example
st.markdown('<div class="header"><h2>Accounts</h2></div>', unsafe_allow_html=True)
accounts_placeholder = st.empty()
with accounts_placeholder.container():
    accounts = get_accounts()
    st.dataframe(pd.DataFrame(accounts))

st.divider()

st.markdown('<div class="header"><h2>Transactions</h2></div>', unsafe_allow_html=True)
transactions_placeholder = st.empty()
with transactions_placeholder.container():
    transactions = get_transactions()
    if transactions:
        df_transactions = pd.DataFrame(transactions, columns=[
            "ID", "Date", "Type", "Description", "Amount", "From Account", "To Account", "File Path"
        ])
        df_transactions["File Link"] = df_transactions["File Path"].apply(
            lambda x: f'<a href="file:///{os.path.abspath(x)}" target="_blank">📂 Open File</a>' if x else "No File"
        )
        st.dataframe(df_transactions)
    else:
        st.write("No transactions available.")

# Add account
st.sidebar.markdown('<div class="sidebar-section"><h3>Add Account</h3></div>', unsafe_allow_html=True)
account_name = st.sidebar.text_input("Account Name")
account_balance = st.sidebar.number_input("Initial Balance", min_value=0.0)
if st.sidebar.button("Add Account"):
    add_account(account_name, account_balance)
    st.success(f"Account '{account_name}' added successfully!")
    # Refresh accounts dynamically
    with accounts_placeholder.container():
        accounts = get_accounts()
        st.dataframe(pd.DataFrame(accounts))

# Add transaction
st.sidebar.markdown('<div class="sidebar-section"><h3>Add Transaction</h3></div>', unsafe_allow_html=True)
transaction_date = st.sidebar.date_input("Date")
transaction_type = st.sidebar.selectbox("Type", ["DEPOSIT", "EXPENSE", "TRANSFER"])
transaction_desc = st.sidebar.text_input("Description")
transaction_amount = st.sidebar.number_input("Amount", min_value=0.0)
from_account = st.sidebar.selectbox("From Account", [None] + [acc["name"] for acc in accounts])
to_account = st.sidebar.selectbox("To Account", [None] + [acc["name"] for acc in accounts])
uploaded_file = st.sidebar.file_uploader("Upload File")
if st.sidebar.button("Add Transaction"):
    file_path = None
    if uploaded_file:
        file_path = os.path.join(UPLOAD_FOLDER, uploaded_file.name)
        with open(file_path, "wb") as f:
            f.write(uploaded_file.read())
    from_account_id = next((acc["id"] for acc in accounts if acc["name"] == from_account), None)
    to_account_id = next((acc["id"] for acc in accounts if acc["name"] == to_account), None)
    add_transaction((transaction_date, transaction_type, transaction_desc, transaction_amount, from_account_id, to_account_id, file_path))
    st.success("Transaction added successfully!")
    # Refresh accounts and transactions dynamically
    with accounts_placeholder.container():
        accounts = get_accounts()
        st.dataframe(pd.DataFrame(accounts))
    with transactions_placeholder.container():
        transactions = get_transactions()
        df_transactions = pd.DataFrame(transactions, columns=[
            "ID", "Date", "Type", "Description", "Amount", "From Account", "To Account", "File Path"
        ])
        df_transactions["File Link"] = df_transactions["File Path"].apply(
            lambda x: f'<a href="file:///{os.path.abspath(x)}" target="_blank">📂 Open File</a>' if x else "No File"
        )
        st.dataframe(df_transactions)

# Reset button
st.sidebar.markdown('<div class="sidebar-section"><h3>Reset Application</h3></div>', unsafe_allow_html=True)
reset_application()

# Export transactions
st.sidebar.markdown('<div class="sidebar-section"><h3>Export Transactions</h3></div>', unsafe_allow_html=True)
if st.sidebar.button("Export Transactions to Excel"):
    excel_path = export_transactions()
    st.sidebar.download_button(
        label="Download Excel File",
        data=open(excel_path, "rb").read(),
        file_name="transactions.xlsx"
    )