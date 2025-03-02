import azure.functions as func
import logging
import os
import pyodbc
from azure.identity import ClientSecretCredential
import msal
import pandas as pd
import sqlalchemy
import io
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder
import hashlib
from datetime import datetime


app = func.FunctionApp()

def connect_sql():
        # Retrieve environment variables for configuration
        server = os.environ.get('DB_SERVER')  # Example: yourserver.database.windows.net
        database = os.environ.get('DB_NAME')
        client_id = os.environ.get('DB_USERNAME')
        client_secret = os.environ.get('DB_PASSWORD')
        tenant_id = os.environ.get('TENANT_ID')

        authority = f'https://login.microsoftonline.com/{tenant_id}'

    # Initialize the Confidential Client Application with msal
        msal.ConfidentialClientApplication(
            client_id=client_id,
            client_credential=client_secret,
            authority=authority
        )

        constr = (
            f"driver=ODBC Driver 18 for SQL Server;"
            f"server={server};database={database};"
            f"UID={client_id};PWD={client_secret};"
            f"Authentication=ActiveDirectoryServicePrincipal;"
            f"Encrypt=yes;Timeout=60;"
        )

        return constr

def run_sql_query(query):
    try:
        
        constr = connect_sql()
        # Connect to the database and execute the update query
        with pyodbc.connect(constr) as conn:
            with conn.cursor() as cursor:
              
                cursor.execute(query)
                conn.commit()
                logging.info(f"{cursor.rowcount} records updated to 'IN PROGRESS'.")
       
        return True

    except pyodbc.Error as db_error:
        logging.error(f"Database error: {str(db_error)}")
        # Consider raising the exception if you need the function to retry
    except Exception as e:
        logging.error(f"An unexpected error occurred: {str(e)}")
        # Consider raising the exception if you need the function to retry

def get_data_from_sql(query):
    try:
        constr = connect_sql()
        con = pyodbc.connect(constr)
        data = pd.read_sql(query, con)
        con.close()
        
        return data

    except Exception as e:
        logging.error(f"Error connecting to SQL Data Warehouse: {e}")
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
        logging.error(f"Error writing data to SQL table: {e}")

def update_category(df):
    constr = connect_sql()
    with pyodbc.connect(constr) as conn:
        cursor = conn.cursor()

        # SQL update query
        update_query = """
        UPDATE [Transaction]
        SET [Category] = ?
        WHERE [transactionId] = ?
        """

        # Iterate through the DataFrame and execute the update for each row
        for index, row in df.iterrows():
            cursor.execute(update_query, row['Category'], row['transactionId'])

        # Commit the transaction
        conn.commit()
    return True

def read_blob(blob):
    blob_bytes = blob.read()
    blob_str = io.StringIO(blob_bytes.decode('utf-8'))
    try:
        df = pd.read_csv(blob_str)
        return df
    except Exception as e: 
        return None

def get_account_details(file_name):
    query = f"""
        SELECT TOP 1 [AccountName],[UserId]
        FROM [dbo].[UploadedFile] 
        WHERE ProcessingStatus = 'SCHEDULED' AND FileName = '{file_name}'  
        ORDER BY LastUpdatedDateTime DESC
    """
    account_name_result = get_data_from_sql(query)

    if not account_name_result.empty:
        account_name = account_name_result.iloc[0, 0]
        user_id = account_name_result.iloc[0, 1]
    else:
        account_name = None
        user_id = None
    
    return account_name, user_id

def update_processing_status(file_name,status):
    update_query = f"""
        UPDATE [UploadedFile]
        SET ProcessingStatus = '{status}'
        WHERE FileName = '{file_name}'
    """
    return run_sql_query(update_query)

def get_training_data(user_id):
    query = f"SELECT Description, CAST(Amount AS Float) AS Amount, Category FROM [Transaction] where UserId={user_id}"
    df = get_data_from_sql(query)
    if len(df)<100:
        query = "SELECT Description, CAST(Amount AS Float) AS Amount, Category FROM [TrainingData]"
        df = get_data_from_sql(query)

    return df

def train_model(training_df):
    # Encode labels
    le = LabelEncoder()
    training_df['CategoryIndex'] = le.fit_transform(training_df['Category'])

    # Build and train the pipeline
    pipeline = Pipeline([
        ('tfidf', TfidfVectorizer(stop_words='english', max_features=10000)),
        ('clf', LogisticRegression())
    ])

    X_train = training_df['Description']
    y_train = training_df['CategoryIndex']
    pipeline.fit(X_train, y_train)

    return pipeline, le

def categorize_transactions(new_df, model, label_encoder, account_name, user_id):
    # Predict categories for new transactions
    new_df['CategoryIndex'] = model.predict(new_df['Description'])
    new_df['Category'] = label_encoder.inverse_transform(new_df['CategoryIndex'])
    new_df['AccountName'] = account_name
    new_df['UserId'] = user_id

    # Create transaction ID using hashing
    new_df['transactionId'] = new_df.apply(
        lambda row: hashlib.sha256(
            f"{row['AccountName']}||{row['Date']}||{row['Description']}||{row['Amount']}||{row['Category']}".encode()
        ).hexdigest(), axis=1
    )

    # Drop the CategoryIndex column
    new_df.drop('CategoryIndex', axis=1, inplace=True)

    # Convert the date format from 'DD/MM/YYYY' to 'YYYY-MM-DD'
    new_df['Date'] = pd.to_datetime(new_df['Date'], format='%d/%m/%Y').dt.strftime('%Y-%m-%d')

    return new_df

@app.blob_trigger(arg_name="myblob", path="landing", connection="wealthoptimizerfabric_STORAGE")
def wealthoptimizertransactionprocessing(myblob: func.InputStream):
   
    file_name = os.path.basename(myblob.name)
    logging.info(f"Processing blob: Name: {file_name}, Size: {myblob.length} bytes")

    # Retrieve the account name associated with the blob
    account_name,user_id = get_account_details(file_name)
    logging.info(f"Account name retrieved: {account_name}")

    # Read the blob data into a DataFrame
    new_df = read_blob(myblob)

    # Update the processing status of the file
    if update_processing_status(file_name,'IN PROGRESS'):
        logging.info(f"Processing status updated for file: {file_name}")
    else:
        logging.error(f"Failed to update processing status for file: {file_name}")
        return

    # Fetch and prepare the training data
    training_df = get_training_data(user_id)

    # Train the model
    model, label_encoder = train_model(training_df)

    # Make predictions and update the DataFrame
    new_df = categorize_transactions(new_df, model, label_encoder, account_name, user_id)

    # Write the processed data to SQL
    if write_data_to_sql(new_df, 'Transaction'):
        logging.info("Function execution completed successfully.")
        update_processing_status(file_name,'COMPLETED')
    else:
        update_processing_status(file_name,'FAILED')
        logging.error("Error writing data to SQL.") 