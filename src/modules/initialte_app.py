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
import plotly.graph_objects as go
import seaborn as sns
import src.modules.sql_handler as sq

# Function to initialize session state
def reset_session_state():
    init_session_state()
    initiate_dataset()
    st.rerun()

def init_session_state():
    if 'df' not in st.session_state:
        st.session_state["df"] = None
    if 'reset_session' not in st.session_state:
        st.session_state["reset_session"] = False
    if "edit_mode" not in st.session_state:
        st.session_state["edit_mode"] = False
    if "show_popup" not in st.session_state:
        st.session_state["show_popup"] = False
    if "uploader_key" not in st.session_state:
        st.session_state["uploader_key"]=0
    if "category" not in st.session_state:
        st.session_state["category"] = ''
        

def initiate_dataset():
    if st.session_state["df"] is None or st.session_state["reset_session"] or len(st.session_state["df"])==0:
        query = f"SELECT  * FROM [Transaction] where UserId={st.experimental_user.sub}"
        st.session_state["df"] = sq.get_data_from_sql(query)
        st.session_state["reset_session"] = False

    if st.session_state["df"] is not None:
        st.session_state["df"]['Date'] = pd.to_datetime(st.session_state["df"]['Date'])
        st.session_state["df"]['Year'] = st.session_state["df"]['Date'].dt.year.astype(int) 
