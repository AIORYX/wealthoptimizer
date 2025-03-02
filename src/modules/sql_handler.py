import streamlit as st
import pandas as pd
import pyodbc
import msal  # Microsoft Authentication Library
import plotly.express as px
import plotly.graph_objects as go
from st_aggrid import AgGrid, GridOptionsBuilder, DataReturnMode, GridUpdateMode, AgGridTheme
from datetime import datetime 
from src.components import side_bars as sb
from src.components import charts
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
import os
from hashlib import sha256
import sqlalchemy


# SQL connection settings
def connect_sql():
    #server = '4rnsydkpbj5ebnfr7gu3qzcu6e-vbaynrxejvlu7kr3lblu7oogru.datawarehouse.fabric.microsoft.com'
    #database = 'WealthOptimizerWarehouse'
    server = 'wlsqlserver.database.windows.net'
    database = 'wosqldb01'
    
    #client_id = sc.client_id
    #client_secret = sc.client_secret
    #tenant_id = sc.tenant_id
    client_id = os.getenv('client_id')
    client_secret = os.getenv('client_secret')
    tenant_id = os.getenv('tenant_id')
    authority = f'https://login.microsoftonline.com/{tenant_id}'
    msal.ConfidentialClientApplication(client_id=client_id, client_credential=client_secret, authority=authority)
    constr = (
        f"driver=ODBC Driver 18 for SQL Server;"
        f"server={server};database={database};"
        f"UID={client_id};PWD={client_secret};"
        f"Authentication=ActiveDirectoryServicePrincipal;"
        f"Encrypt=yes;Timeout=60;"
    )
    return constr


# Function to get data from SQL
def get_data_from_sql(query):
    try:
        constr = connect_sql()
        con = pyodbc.connect(constr)
        data = pd.read_sql(query, con)
        con.close()
        
        return data

    except Exception as e:
        st.error(f"Error connecting to SQL Data Warehouse: {e}")
        return None

def write_data_to_sql(df, table_name):
    try:
        # Establish SQL connection
        constr = connect_sql()  # Assuming connect_sql is a function that returns the connection string
        con = pyodbc.connect(constr)

        # Create SQLAlchemy engine for efficient writes
        engine = sqlalchemy.create_engine(f"mssql+pyodbc:///?odbc_connect={constr}")
        
        # Write DataFrame to SQL table
        df.to_sql(table_name, con=engine, if_exists='append', index=False)
        
        con.close()
        #st.success(f"Data successfully written to {table_name}")
        return True
        
    except Exception as e:
        st.error(f"Error writing data to SQL table: {e}")

# Delete duplicates based on transaction IDs
def delete_duplicates_from_sql(transaction_ids):
    try:
        constr = connect_sql()
        with pyodbc.connect(constr) as con:
            cursor = con.cursor()
            query_template = "EXEC DeleteDuplicateTransaction @TransactionId='{txn_id}'"
           
            total_transactions = len(transaction_ids)
            progress_bar = st.progress(0)

            for index, txn_id in enumerate(transaction_ids):
                cursor.execute(query_template.format(txn_id=txn_id))
                progress_percent = int((index + 1) / total_transactions * 100)
                progress_bar.progress(progress_percent)

            con.commit()
            st.success("Transaction duplicates removed successfully!")
            st.session_state["reset_session"] = True

    except Exception as e:
        st.error(f"Error updating SQL table: {e}")

def update_sql_transfers(transaction_ids):
    try:
        # Convert transaction IDs to a comma-separated string
        ids = ','.join('?' for _ in transaction_ids)  # Use placeholders for parameterized query
        constr = connect_sql()
        
        with pyodbc.connect(constr) as con:
            cursor = con.cursor()
            query_template = f"UPDATE [Transaction] SET Category='Transfer' WHERE transactionId IN ({ids})"
            
            progress_bar = st.progress(0)
            cursor.execute(query_template, transaction_ids)  # Use parameterized query to avoid SQL injection
            progress_bar.progress(100)
            con.commit()
            
            st.success("Transfers updated successfully!")
            st.session_state["reset_session"] = True

    except Exception as e:
        st.error(f"Error updating SQL table: {e}")


def reset_all(user_id):
    try:
        # Convert transaction IDs to a comma-separated string
        constr = connect_sql()
        
        with pyodbc.connect(constr) as con:
            cursor = con.cursor()
            query_transaction = f"DELETE FROM [Transaction] WHERE UserId={user_id}"
            query_uploadedfile = f"DELETE FROM [UploadedFile] WHERE UserId={user_id}"
            
            progress_bar = st.progress(0)
            cursor.execute(query_transaction)  # Use parameterized query to avoid SQL injection
            cursor.execute(query_uploadedfile)  # Use parameterized query to avoid SQL injection
            progress_bar.progress(100)
            con.commit()
            
        return True

    except Exception as e:
        st.error(f"Error updating SQL table: {e}")
