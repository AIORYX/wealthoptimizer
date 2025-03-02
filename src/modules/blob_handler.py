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

def upload_file_to_blob(account_name, container_name, sas_key, blob_name, data):
    try:
        connection_string = f"DefaultEndpointsProtocol=https;AccountName={account_name};SharedAccessSignature={sas_key}"
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        container_client = blob_service_client.get_container_client(container_name)

        # Create container if not exists
        try:
            container_client.create_container()
            st.info(f"Container '{container_name}' created.")
        except Exception as e:
            if "ContainerAlreadyExists" not in str(e):
                st.error(f"Error creating container: {e}")
        
        blob_client = container_client.get_blob_client(blob_name)
        try:
            blob_client.upload_blob(data,overwrite=True)
            st.success("File Uploaded Successfully!")
        except Exception as e:
            st.error(f"Error uploading the file: {e}")
        
        return True

    except Exception as e:
        st.error(f"An error occurred while uploading: {e}")
        return False
