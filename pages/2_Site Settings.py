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
from difflib import SequenceMatcher
import os
from dotenv import load_dotenv
load_dotenv()
import src.modules.login as lo
import src.modules.upload as upload



# Streamlit app configurations
st.set_page_config(page_title="File Manager", layout="wide", page_icon=":material/settings:")

st.title("Site Settings")
st.divider()


# Azure storage configurations
account_name = "wealthoptimizerfabric"
container_name = "landing"
sas_key = os.getenv('sas_key')

#st.info(f"sas {sas_key}")




# Function to manage duplicate transactions
def duplicate_manager(df):
    duplicate_df = df[df.duplicated(['transactionId', 'AccountName'], keep=False)].copy()
    if len(duplicate_df)>0:
        duplicate_summary = duplicate_df.groupby(['transactionId', 'AccountName']).agg(
            Date=('Date', "max"),
            Description=('Description', "max"),
            Amount=('Amount', "max"),
            Category=('Category', "max"),
            Count=('transactionId', 'size'),
        ).reset_index() 
        duplicate_df['select'] = False

        st.markdown("## Duplicated Transactions")
        gb = GridOptionsBuilder.from_dataframe(duplicate_summary[['Date', 'Description', 'Amount', 'Category', 'Count']])
        gb.configure_selection(selection_mode='multiple', use_checkbox=True, groupSelectsChildren=True, header_checkbox=True)
        grid_response = AgGrid(duplicate_summary, gridOptions=gb.build(), update_mode='MODEL_CHANGED', enable_enterprise_modules=False)
        selected_rows = grid_response['selected_rows']
        #st.dataframe(selected_rows)

        if st.button("Delete Marked Duplicates"):
            if len(selected_rows)>0:
                transaction_ids = selected_rows['transactionId'].tolist()
                sq.delete_duplicates_from_sql(transaction_ids)
            else:
                st.warning("No duplicates marked for deletion")
    else:
        st.info("No duplicates found!")

def descriptions_are_similar(desc1, desc2, threshold=0.1):
    """
    Check if two descriptions are similar using SequenceMatcher.
    """
    return SequenceMatcher(None, desc1, desc2).ratio() > threshold

def find_possible_transfers(df):

    # Create an empty list to store potential transfers
    potential_transfers = []

    # Iterate over each row in the dataframe
    for i, row in df.iterrows():
        # Find rows with the same date and opposite amount with different accounts
        matches = df[(df['Date'] == row['Date']) &
                    (df['Amount'] == -row['Amount']) &
                    (df['Category'] != 'Transfer') &
                    (df['AccountName'] != row['AccountName'])]

        
        for _, match in matches.iterrows():
            # Check if descriptions are similar
            if descriptions_are_similar(row['Description'], match['Description']):
                potential_transfers.append({
                    'From_TransactionId': row['transactionId'],
                    'From_Account': row['AccountName'],
                    'To_TransactionId': match['transactionId'],
                    'To_Account': match['AccountName'],
                    'Date': row['Date'],
                    'Amount': row['Amount'],
                    'Description_From': row['Description'],
                    'Description_To': match['Description']
                })

    # Convert the list of potential transfers into a DataFrame
    transfer_df = pd.DataFrame(potential_transfers)
    return transfer_df

def transfer_manager(df):
    filtered_df=df[df["Amount"]>0]
    st.markdown("## Transfer Between Accounts")
    gb = GridOptionsBuilder.from_dataframe(filtered_df[['Date', 'Amount', 'From_Account', 'Description_From', 'To_Account','Description_To']])
    gb.configure_selection(selection_mode='multiple', use_checkbox=True, groupSelectsChildren=True, header_checkbox=True)
    grid_response = AgGrid(filtered_df, gridOptions=gb.build(), update_mode='MODEL_CHANGED', enable_enterprise_modules=False)
    selected_rows = grid_response['selected_rows']

    if st.button("Mark as Transfers"):
        if len(selected_rows)>0:
            
            transaction_ids = selected_rows['From_TransactionId'].tolist() + selected_rows['To_TransactionId'].tolist()
            #st.write(transaction_ids)
            sq.update_sql_transfers(transaction_ids)
        else:
            st.warning("No duplicates marked for deletion")

# Streamlit main function
def main():
    init.init_session_state()
    lo.login()

    if st.experimental_user.is_logged_in:             
            
        init.initiate_dataset()

        file_upload_toggele_value,show_history, duplicate_analyzer,transfer_analyzer,clean_toggle_value = sb.file_handler_sidebar()

        if file_upload_toggele_value:
            # File upload handler
            upload.file_uploder()

        # Display history
        if show_history:
            query = f"SELECT * FROM [dbo].[UploadedFile] WHERE ProcessingStatus IS NOT NULL AND UserId={st.experimental_user.sub}"
            df = sq.get_data_from_sql(query)
            df_select = df[["AccountName", "OriginalFileName", "Description", "LastUpdatedDateTime", "ProcessingStatus"]]
            df_select.columns = ["Account Name", "File Name", "Description", "Uploaded Time", "Status"]
            st.markdown("## File Processing Status")
            st.dataframe(df_select, use_container_width=True, hide_index=True)

        # Duplicate analysis
        if duplicate_analyzer:
            st.markdown("## Resolve Duplicates")
            duplicate_manager(st.session_state["df"])
        
        if transfer_analyzer:
            transfer_df=find_possible_transfers(st.session_state["df"])
            if len(transfer_df)>0:
                transfer_manager(transfer_df)
            else:
                st.markdown("## Transfer Between Accounts")
                st.info("No Transfers Found!")
        if clean_toggle_value:
            st.markdown("## Delete All Data!")
            st.markdown("You are about to delete all your data from the system, this include all the transaction categorisations")
            if st.button(label="Reset All"):
                reset_status = sq.reset_all(st.experimental_user.sub)
                if reset_status:
                    st.toast("Reset successfully completed!")
                    st.session_state["reset_session"] = True
                    time.sleep(1)
                    st.rerun()

# Run the Streamlit app
if __name__ == "__main__":
    main()
