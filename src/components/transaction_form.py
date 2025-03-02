import streamlit as st
import pandas as pd
import pyodbc
import msal  # Microsoft Authentication Library
import plotly.express as px
from st_aggrid import AgGrid, GridOptionsBuilder, DataReturnMode, GridUpdateMode, AgGridTheme
from datetime import datetime 


# Function to add a new transaction
def add_transaction_form():
    with st.form("New_Transaction"):
        new_date = st.date_input("Date")
        new_description = st.text_input("Description")
        new_amount = st.number_input("Amount", min_value=0.0, step=0.01)
        new_category = st.selectbox("Category", ['Income', 'Expense'])
        submitted = st.form_submit_button("Add Transaction")

        if submitted:
            new_data = {'Date': [new_date], 'Description': [new_description], 'Amount': [new_amount], 'Category': [new_category]}
            new_df = pd.DataFrame(new_data)
            st.session_state["df"] = pd.concat([st.session_state["df"], new_df], ignore_index=True)
            st.success("Transaction added!")