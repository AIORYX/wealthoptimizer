import os
import time
from hashlib import sha256
from io import StringIO
from datetime import datetime, timedelta

import streamlit as st
import pandas as pd
import pyodbc
import msal  # Microsoft Authentication Library
from azure.storage.blob import BlobServiceClient
from st_aggrid import AgGrid, GridOptionsBuilder
import src.modules.sql_handler as sq
import src.components.side_bars as sb
import src.modules.blob_handler as bh
import src.modules.initialte_app as init 
import streamlit.components.v1 as components
from difflib import SequenceMatcher
import os
from dotenv import load_dotenv
load_dotenv()
import src.modules.login as lo

# Azure storage configurations
account_name = "wealthoptimizerfabric"
container_name = "landing"
sas_key = os.getenv('sas_key')


# Display the first row as key-value pairs
def display_first_row_as_key_value(df):
    st.markdown("### File Details")
    first_row = df.iloc[0]
    for col, value in first_row.items():
        st.markdown(f"**{col}:** <span style='color:green'>{value}</span>", unsafe_allow_html=True)

# Function to select specific columns from the DataFrame
def pick_columns(df, date_column, amount_column, description_column, has_header=True):
    if has_header:
        df = df.iloc[1:].reset_index(drop=True)
    df.columns = [f'column {i+1}' for i in range(df.shape[1])]
    selected_columns = df[[date_column, amount_column, description_column]]
    selected_columns.columns = ['Date', 'Amount', 'Description']
    return selected_columns


def file_uploder():
    st.file_uploader("Choose a file", key=f"uploaded_file_{st.session_state['uploader_key']}")
    upload_status=False
    if st.session_state[f"uploaded_file_{st.session_state['uploader_key']}"] is not None:
        df = pd.read_csv(st.session_state[f"uploaded_file_{st.session_state['uploader_key']}"])
        orginal_filename = st.session_state[f"uploaded_file_{st.session_state['uploader_key']}"].name
        has_header = st.checkbox("File has a Header", value=True)
        col1, col2 = st.columns(2)
        
        with col1:
            with st.form("file_upload_form"):
                list_of_columns = [f"column {i}" for i in range(1, len(df.columns)+1)]
                date_column = st.selectbox("Select Date Column", list_of_columns, key='date')
                description_column = st.selectbox("Select Description Column", list_of_columns)
                amount_column = st.selectbox("Select Amount Column", list_of_columns)
                transaction_account_name = st.selectbox(
                    "Select Account", options=("Ultimate Credit Card", "Home Loan", "Savings Account", "Business Account","Bendigo Offset")
                )
                file_description = st.text_area("Description", value="Enter description", max_chars=200)

                submit_button = st.form_submit_button(label="Upload", icon=":material/upload:")
            if submit_button:
                if not all([date_column, description_column, amount_column]):
                    st.warning("Ensure Date, Description, and Amount columns are identified before submission.")
                else:
                    df = pick_columns(df, date_column, amount_column, description_column, has_header)
                    csv_buffer = StringIO()
                    df.to_csv(csv_buffer, index=False)
                    bytes_data = csv_buffer.getvalue().encode('utf-8')
                    file_hash = sha256(bytes_data).hexdigest()
                    current_timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
                    file_name = f"{st.experimental_user.sub}_{file_hash}_{current_timestamp}.csv"
                    processing_status = "SCHEDULED"
                meta_df = pd.DataFrame({
                        "FileHash": [file_hash],
                        "AccountName": [transaction_account_name],
                        "FileName": [file_name],
                        "Description": [file_description],
                        "LastUpdatedDateTime": [datetime.now()],
                        "ProcessingStatus": processing_status,
                        "OriginalFileName": orginal_filename,
                        "UserId": st.experimental_user.sub
                    })
                with st.spinner("Uploading..."):
                        metadata_uploaded = sq.write_data_to_sql(meta_df, "UploadedFile")
                        if metadata_uploaded:
                            file_uploaded=bh.upload_file_to_blob(account_name, container_name, sas_key, file_name, bytes_data)
                            if file_uploaded:
                                 upload_status=True
        
                        else:
                            st.error("Error during upload")
        
        with col2:
                display_first_row_as_key_value(df)
    return upload_status