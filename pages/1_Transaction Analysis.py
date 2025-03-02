import streamlit as st
import pandas as pd
import pyodbc
import msal  # Microsoft Authentication Library
import plotly.express as px
from st_aggrid import AgGrid, GridOptionsBuilder, DataReturnMode, GridUpdateMode, AgGridTheme
from datetime import datetime 
from src.components import side_bars as sb
import src.modules.sql_handler as sq
import src.modules.initialte_app as init 
import src.modules.login as lo
import calendar


# Full-page layout
st.set_page_config(layout="wide")
st.title("Transaction Details")


st.markdown("""
    <style>
    /* Apply custom styles to the grid wrapper */
    .ag-root-wrapper {
        border-radius: 15px !important;
        box-shadow: 0px 4px 12px rgba(0, 0, 0, 0.1) !important;
        border: none !important;
        overflow: hidden;
    }
    
    /* Header rounded corners */
    .ag-header {
        border-top-left-radius: 15px !important;
        border-top-right-radius: 15px !important;
        overflow: hidden;
    }
    
    /* Body rounded corners */
    .ag-body-viewport {
        border-bottom-left-radius: 15px !important;
        border-bottom-right-radius: 15px !important;
        overflow: hidden;
    }
    
    /* Ensure scrollbars do not mess up the borders */
    .ag-root-wrapper-body {
        overflow: hidden !important;
    }
    </style>
    """, unsafe_allow_html=True)



def update_sql_table_transaction(df):
    try:
       
        # Connect to SQL
        constr = sq.connect_sql()
        con = pyodbc.connect(constr)
        cursor = con.cursor()

        # Loop through the changed rows and update each one
        for index, row in df.iterrows():
            update_query = """
                UPDATE [Transaction]
                SET Date = ?, Description = ?, Amount = ?, Category = ?, LastUpdatedDateTime= ?
                WHERE transactionId = ?
            """
            cursor.execute(update_query, row['Date'], row['Description'], row['Amount'], row['Category'],row['LastUpdatedDateTime'], row['transactionId'])

        # Commit the transaction after all updates
        con.commit()
        st.spinner("In Progress")
        st.success("Transaction table updated successfully!")
        st.session_state["reset_session"] = True
    
    except Exception as e:
        st.error(f"Error updating SQL table: {e}")
    
    finally:
        # Ensure connection is closed
        cursor.close()
        con.close()






# Function to build AgGrid options for the tables
def build_grid_options(dataframe, selection_mode='multiple'):
    gb = GridOptionsBuilder.from_dataframe(dataframe)
    gb.configure_pagination(paginationAutoPageSize=True)
    gb.configure_default_column(editable=True , filter=True , sortable=True)
    gb.configure_selection(selection_mode=selection_mode)
    gb.configure_default_column(autoSizeColumns=True)
    gb.configure_grid_options(domLayout='normal')
    return gb.build()



# Function to filter dataframe
def filter_dataframe(df, start_date, end_date, category_filter, amount_range, selected_years,selected_months):
    return df[
        (df['Date'] >= pd.to_datetime(start_date)) & (df['Date'] <= pd.to_datetime(end_date)) &
        (df['Date'].dt.month_name().isin(selected_months) & df['Date'].dt.year.isin(selected_years)) &
        (df['Category'].isin(category_filter)) &
        (df['Amount'].between(amount_range[0], amount_range[1])) &
        (st.session_state["df"]['AccountName'].isin(st.session_state["account_filter"])) 
    ]

# Function to display the charts
def display_charts(df):
    df['Amount'] = df['Amount'].abs()
    col1, col2 = st.columns(2)
    with col1:
        category_chart = px.bar(df, x='Category', y='Amount', title="Amount by Category", labels={'Amount': 'Transaction Amount'})
        st.plotly_chart(category_chart)

    with col2:
        df['Date'] = pd.to_datetime(df['Date'])  # Ensure date format
        time_chart = px.line(df.sort_values('Date'), x='Date', y='Amount', title="Transaction Amount Over Time", markers=True, labels={'Amount': 'Transaction Amount'})
        st.plotly_chart(time_chart)
def reset_session():
    st.session_state["reset_session"] = True
    st.warning("All updates were discarded!")

def transaction_update_popover(df,columns):
    with st.popover(label="Apply Changes",use_container_width=True):
        st.write("### changes detected")
        st.write("the following changes were made:")
        st.dataframe(df[columns])
         # confirm or cancel buttons
        col1, col2 = st.columns(2)
        with col1:
            st.button("Confirm", on_click=update_sql_table_transaction, args=(df,))
        with col2:
            st.button("Cancel",on_click=reset_session)

                 
def display_drilldown_table(df: pd.DataFrame):
    """
    Displays an interactive drill-down table using st-aggrid.
    
    The input DataFrame must include the following columns:
    - 'Date' (in a format convertible to datetime)
    - 'Description'
    - 'Amount'
    - 'Category'
    
    This function adds 'Year' and 'Month' columns to facilitate grouping.
    
    Args:
        df (pd.DataFrame): DataFrame containing transaction data.
    """
    # Ensure the Date column is in datetime format and extract Year and Month
    # Build the grid options for grouping: Category > Year > Month
    df = df[["transactionId","Date","Description","Amount","Category","Year"]]
    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_default_column(groupable=True)
    df['MonthNum'] = df['Date'].dt.month
    df['Month'] = df['MonthNum'].apply(lambda x: calendar.month_name[x])
    df['Amount'] = df['Amount'].round(2)
    # Configure grouping columns and hide them from the main view
    gb.configure_column("Category", rowGroup=True, hide=True)
    gb.configure_column("Year", rowGroup=True, hide=True)
    gb.configure_column("Month", rowGroup=True, hide=True)
    gb.configure_column("transactionId",  hide=True)
    gb.configure_pagination(paginationAutoPageSize=True)
    gb.configure_default_column(editable=True , filter=True , sortable=True)
    gb.configure_default_column(autoSizeColumns=True)
    gb.configure_grid_options(domLayout='normal')
    
    
    # Configure Amount column to display the summed total for groups
    gb.configure_column(
        "Amount", 
        headerName=("TotalAmount"), 
        aggFunc="sum",
        type=["numericColumn","numberColumnFilter","customNumericFormat"], 
        precision=2
    )
    
    gridOptions = gb.build()
    

    
    AgGrid(df,      
           gridOptions=gridOptions, 
           enable_enterprise_modules=True, 
           it_columns_on_grid_load=True,  # Automatically adjusts column width
           height=400,  # Set a custom height, adjust as needed
           theme='streamlit')  # Use a modern theme (options: 'light', 'dark', 'material')
           
               

# Main function to run the Streamlit app
def main():
    init.init_session_state()

    lo.login()

    if st.experimental_user.is_logged_in:             
        
        init.initiate_dataset()

    
        if st.session_state["df"] is None or st.session_state["reset_session"]:
            query = f"SELECT  * FROM [Transaction] where UserId={st.experimental_user.sub}"
            st.session_state["df"] = sq.get_data_from_sql(query)
            st.session_state["reset_session"] = False
        
        if len(st.session_state["df"]) == 0:
            st.warning("Please Upload Data")
        

        if st.session_state["df"] is not None and  len(st.session_state["df"] ) > 0:
            st.session_state["df"]['Date'] = pd.to_datetime(st.session_state["df"]['Date'])

            # Sidebar filters
            selected_start_date,selected_end_date,amount_range,selected_years,selected_months,description_filter = sb.transaction_analysis_sidebar()

            
            filtered_df = filter_dataframe(st.session_state["df"], selected_start_date, selected_end_date, st.session_state["category_filter"], amount_range, selected_years, selected_months)
            if len(description_filter):
                filtered_df = filtered_df[filtered_df['Description'].str.contains(description_filter, case=False, na=False)]

            # Aggregate table
            aggregated_df = filtered_df.groupby('Category', as_index=False).agg(Total_Amount=('Amount', 'sum'), Average_Amount=('Amount', 'mean'))
            aggregated_df['Average_Amount'] = aggregated_df['Average_Amount'].round(2)

            # Display grids and charts
            col1, col2 = st.columns([7,5])
            with col1:
                transaction_grid_options = build_grid_options(filtered_df[['Date', 'Description', 'Amount', 'Category']])
                grid_response = AgGrid(filtered_df, 
                    gridOptions=transaction_grid_options, 
                    update_mode=GridUpdateMode.MODEL_CHANGED, 
                    editable=True, 
                    enable_enterprise_modules=True, 
                    fit_columns_on_grid_load=True,  # Automatically adjusts column width
                    height=400,  # Set a custom height, adjust as needed
                    theme='streamlit')  # Use a modern theme (options: 'light', 'dark', 'material')
                
            #st.session_state["edit_mode"] = st.checkbox("Enable Edit Mode", value=False)     
                
            # Specify the columns to compare (Date, Description, Amount, Category)
            columns_to_compare = ['Date', 'Description', 'Amount', 'Category']

            # Compare only the specified columns row-wise
            original_df = filtered_df.copy()
            updated_df = grid_response['data']
            updated_df = updated_df.set_index('transactionId').sort_values('transactionId')
            original_df = original_df.set_index('transactionId').sort_values('transactionId')
            changed_rows = updated_df[~(original_df[columns_to_compare] == updated_df[columns_to_compare]).all(axis=1)]
            

            with col2:
                display_drilldown_table(filtered_df)

            
            if len(changed_rows)>0:
                #if st.button("Apply Changes"):
                changed_rows_with_id = changed_rows.reset_index()
                changed_rows_with_id['LastUpdatedDateTime']= datetime.now()   
                transaction_update_popover(changed_rows_with_id,columns_to_compare)
            
            if grid_response['selected_rows'] is not None:
                with st.popover(label="Change Category",icon=":material/upgrade:",use_container_width=True):
                    st.write("### Bulk Update Category ")
                    col1, col2 = st.columns([1,5])
                    with col1:
                        new_category = st.text_input("Category", value=st.session_state["category"], key="category")
                    with col2:
                        if len(new_category)==0:
                            st.dataframe(grid_response['selected_rows'][['Date', 'Description', 'Amount', 'Category']])
                        else:
                            df = grid_response['selected_rows'].reset_index()
                            df['LastUpdatedDateTime'] = datetime.now()
                            df['Category'] = new_category
                            st.dataframe(df[['Date', 'Description', 'Amount', 'Category']])
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if len(new_category)>0:
                            st.button("Update", on_click=update_sql_table_transaction, args=(df,), key="update_button")
                    with col2:
                        st.button("Cancel",on_click=reset_session , key="cancel_button")

            display_charts(filtered_df)

# Run the app
if __name__ == "__main__":
    main()
