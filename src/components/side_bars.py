import streamlit as st
import pandas as pd
import pyodbc
import msal  # Microsoft Authentication Library
import plotly.express as px
from st_aggrid import AgGrid, GridOptionsBuilder, DataReturnMode, GridUpdateMode, AgGridTheme
from datetime import datetime 
from src.components import transaction_form

def pages():
    st.page_link("Home.py", label="Home", icon=":material/home:")
    if len(st.session_state["df"])>0:
        st.page_link("pages/1_Transaction Analysis.py", label="Transaction Analysis", icon=":material/sync:")
    else:
        st.page_link("pages/1_Transaction Analysis.py", label="Transaction Analysis", icon=":material/sync:", disabled=True)
    st.page_link("pages/2_Site Settings.py", label="Site Settings", icon=":material/settings:")     
     

def transaction_analysis_sidebar():
    with st.sidebar:
            pages()
            st.header("Filters")
            if st.button("Reset Filters"):
                 pass
            
            
            months_order = ['January', 'February', 'March', 'April', 'May', 'June', 
                    'July', 'August', 'September', 'October', 'November', 'December']
            
            st.multiselect("Select Account", 
                            options=st.session_state["df"]['AccountName'].unique(), 
                            key="account_filter",
                            default=list(st.session_state["df"]['AccountName'].unique()))
            
            min_date = st.session_state["df"]['Date'].min().date()
            max_date = st.session_state["df"]['Date'].max().date()

            col1, col2 = st.columns(2)
            with col1:
                selected_start_date = st.date_input("Start Date", min_date)
            with col2:
                selected_end_date = st.date_input("End Date", max_date)

            min_amount = st.session_state["df"]['Amount'].min()
            max_amount = st.session_state["df"]['Amount'].max()
            # amount_range = st.slider("Select Amount Range", 
            #                          min_value=float(min_amount), 
            #                          max_value=float(max_amount), 
            #                          value=(float(min_amount), float(max_amount)),
            #                          key="amount_slider")
            col1, col2 = st.columns(2)
            with col1:
                min_amount = st.number_input("Min Amount",value=min_amount, min_value=min_amount, max_value=max_amount)
            with col2:
                max_amount = st.number_input("Max Amount",value=max_amount, min_value=min_amount, max_value=max_amount)
            amount_range = (min_amount,max_amount)

            description_filter = st.text_input("Description")

            unique_years = sorted(st.session_state["df"]['Year'].unique())

            selected_years = st.multiselect("Select Year", unique_years, default=max(unique_years))

            unique_months = st.session_state["df"]["Date"].dt.month_name()

            unique_months = unique_months.unique()

            sorted_months = sorted(unique_months, key=lambda x: months_order.index(x))

            selected_months = st.multiselect("Select Month", sorted_months, default=sorted_months)
            

            #slider_start_date, slider_end_date = st.slider("Select Date Range (Slider)", 
            #                                               min_value=min_date, 
            #                                               max_value=max_date, 
            #                                               value=(min_date, max_date), 
            #                                               format="YYYY-MM-DD", key="date_slider")
            
            
 

            categories = st.session_state["df"]['Category'].unique()
            default_categories = [category for category in categories if category not in ["Exclude", "Transfer"]]

            st.multiselect("Select Categories", 
                            options=st.session_state["df"]['Category'].unique(), 
                            key="category_filter",
                            default=default_categories)
            
            
            #transaction_form.add_transaction_form()

            return selected_start_date,selected_end_date,amount_range,selected_years,selected_months,description_filter

def home_sidebar():
    with st.sidebar:
            pages()
            st.header("Filters")
            unique_years = sorted(st.session_state["df"]['Year'].unique())


            st.multiselect("Select Account", 
                            options=st.session_state["df"]['AccountName'].unique(), 
                            key="account_filter",
                            default=list(st.session_state["df"]['AccountName'].unique()))
            
            selected_years = [st.selectbox("Select Year", unique_years,  index=unique_years.index(max(unique_years)))]

            categories = st.session_state["df"]['Category'].unique()
            default_categories = [category for category in categories if category not in ["Exclude", "Transfer"]]

            st.multiselect("Select Categories", 
                            options=st.session_state["df"]['Category'].unique(), 
                            key="category_filter",
                            default=default_categories)
            

            return selected_years

            # min_date = st.session_state["df"]['Date'].min().date()
            # max_date = st.session_state["df"]['Date'].max().date()

            # selected_start_date = st.date_input("Start Date", min_date)
            # selected_end_date = st.date_input("End Date", max_date)

            # slider_start_date, slider_end_date = st.slider("Select Date Range (Slider)", 
            #                                                min_value=min_date, 
            #                                                max_value=max_date, 
            #                                                value=(min_date, max_date), 
            #                                                format="YYYY-MM-DD", key="date_slider")
            

            # return selected_start_date,selected_end_date,slider_start_date, slider_end_date

def file_handler_sidebar():
    with  st.sidebar:
        pages()
        st.markdown("### Upload Files")
        file_upload_toggele_value = st.toggle("Show Details",help="File Uploader", value=False)
        st.markdown("### File Processing Status")
        file_processing_status = st.toggle("Show Details",help="Show File processing details for uploaded files", value=False)
        st.markdown("### Find Duplicates")
        duplicate_toggle_value = st.toggle("Show Details",help="Identify duplicates mark them", value=False)        
        st.markdown("### Detect Transfers")
        transfer_toggle_value = st.toggle("Show Details",help="Identify possible transfers between accounts", value=False)
        st.markdown("### Reset All")
        clean_toggle_value = st.toggle("Show Details",help="Clean All Data", value=False)

        return file_upload_toggele_value,file_processing_status,duplicate_toggle_value,transfer_toggle_value,clean_toggle_value