import streamlit as st
import pandas as pd
import pyodbc
import msal  # Microsoft Authentication Library
import plotly.express as px
from st_aggrid import AgGrid, GridOptionsBuilder, DataReturnMode, GridUpdateMode, AgGridTheme
import datetime 
from src.components import transaction_form

import pandas as pd
import plotly.express as px
import datetime

import pandas as pd
import datetime
import plotly.express as px

def prepare_data(filtered_df):
    """
    Prepare the data by ensuring date formatting, filtering expenses, 
    and extracting necessary year and month columns.
    """
    # Ensure 'Date' is in datetime format
    filtered_df['Date'] = pd.to_datetime(filtered_df['Date'])

    # Filter only for negative amounts (expenses)
    filtered_df = filtered_df[filtered_df['Amount'] < 0]

    # Make the Amount column positive for charting
    filtered_df['Amount'] = filtered_df['Amount'].abs()

    # Extract Year and Month separately
    filtered_df['Year'] = filtered_df['Date'].dt.year.astype(int)
    filtered_df['Month'] = filtered_df['Date'].dt.month_name()
    filtered_df['Month_num'] = filtered_df['Date'].dt.month

    return filtered_df


def check_full_previous_year_data(filtered_df, previous_year):
    """
    Check if the full previous year's data (all 12 months) is available.
    """
    previous_year_data = filtered_df[filtered_df['Year'] == previous_year]
    return len(previous_year_data['Month'].unique()) == 12


def calculate_average_expenses(filtered_df, previous_years_data):
    """
    Calculate the average expense per month across all previous years.
    """
    number_of_years = len(previous_years_data['Year'].unique())
    return previous_years_data.groupby('Month')['Amount'].sum() / number_of_years


def generate_predictions(current_year_data, remaining_months, average_expense_per_month, current_year):
    """
    Generate predictions for the remaining months in the current year.
    """
    predicted_df = pd.DataFrame({
        'Month': remaining_months,
        'Year': current_year,
        'Amount': average_expense_per_month.loc[remaining_months].values
    })
    predicted_df['Predicted'] = 'Predicted'
    current_year_data['Predicted'] = 'Actual'
    
    return pd.concat([current_year_data, predicted_df])


def create_combined_df(filtered_df, previous_years_data, current_year, previous_year):
    """
    Create the combined DataFrame for all years, including current year's data with predictions if applicable.
    """
    current_year_data = filtered_df[filtered_df['Year'] == current_year]

    # Check if full previous year's data is available for predictions
    if check_full_previous_year_data(filtered_df, previous_year):
        # Calculate average expenses for predictions
        average_expense_per_month = calculate_average_expenses(filtered_df, previous_years_data)

        # Identify the remaining months for prediction
        all_months = pd.Series(['January', 'February', 'March', 'April', 'May', 'June', 
                                'July', 'August', 'September', 'October', 'November', 'December'])
        current_year_months = current_year_data['Month'].unique()
        remaining_months = all_months[~all_months.isin(current_year_months)]

        # Generate predicted data
        combined_current_year_df = generate_predictions(current_year_data, remaining_months, average_expense_per_month, current_year)
    else:
        # No predictions, only actual data
        combined_current_year_df = current_year_data
        combined_current_year_df['Predicted'] = 'Actual'

    # Mark previous years' data as actual
    previous_years_data['Predicted'] = 'Actual'

    # Combine all data into a single DataFrame
    return pd.concat([previous_years_data, combined_current_year_df])


def plot_expenses_chart(combined_df, current_year):
    """
    Create a bar chart for expenses including actual and predicted data.
    """
    # Define the correct order of months
    month_order = ['January', 'February', 'March', 'April', 'May', 'June', 
                   'July', 'August', 'September', 'October', 'November', 'December']

    # Convert 'Month' to categorical with the correct order
    combined_df['Month'] = pd.Categorical(combined_df['Month'], categories=month_order, ordered=True)

    # Group by Year, Month, and Predicted columns and sum the Amount column
    amount_by_year_month = combined_df.groupby(['Month', 'Year', 'Predicted'])['Amount'].sum().reset_index()

    # Convert 'Year' to string for proper grouping in the plot
    amount_by_year_month['Year'] = amount_by_year_month['Year'].astype(str)

    # Create a bar chart using Plotly
    fig = px.bar(amount_by_year_month, 
                x='Month', 
                y='Amount', 
                color='Year',  
                pattern_shape='Predicted',  
                barmode='group', 
                title=f"Total Expenses by Month for All Years (Including Predictions for {current_year})")

    # Customize the legend to only show 'Actual' and 'Predicted'
    fig.for_each_trace(lambda t: t.update(name=t.name.split(",")[1], showlegend=False))

    # Update the pattern shape to make 'Predicted' values grayed-out
    fig.update_traces(
        selector=dict(pattern_shape="Predicted"), 
        marker_color="gray"
    )

    return fig


def plot_expenses_with_predictions(filtered_df):
    """
    Main function to plot expenses with or without predictions based on available data.
    """
    # Prepare data
    filtered_df = prepare_data(filtered_df)

    # Get current and previous year
    current_year = datetime.datetime.now().year
    previous_year = current_year - 1

    # Filter data for all years except the current year
    previous_years_data = filtered_df[filtered_df['Year'] != current_year]

    # Create combined DataFrame
    combined_df = create_combined_df(filtered_df, previous_years_data, current_year, previous_year)

    # Plot the expenses chart
    return plot_expenses_chart(combined_df, current_year)



def home_page_charts(df):
    col1, col2, col3 = st.columns([1,2,1])
    df['Amount'] = df['Amount'].abs()
    # Total Spending by Category
    #st.markdown("## Total Spending by Category")
    category_spending = df.groupby('Category')['Amount'].sum().reset_index()

    fig1 = px.scatter(
        category_spending,
        x='Category',
        y='Amount', color='Category',
        title='Total Spending by Category', 
        template='plotly_white'
    )
    #fig1.update_traces(texttemplate='%{label}: $%{value:.2s}', textposition='outside')
    #fig1.update_layout(uniformtext_minsize=8, uniformtext_mode='hide')

    with col1:
        st.plotly_chart(fig1)

    # Transactions Over Time (by Week)
    #st.markdown("## Transactions Over Time (By Week)")
    week_transactions = df.groupby('Week')['Amount'].sum().reset_index()

    fig2 = px.line(
        week_transactions, 
        x='Week', 
        y='Amount', 
        markers=True, 
        title='Total Transactions Over Time (By Week)',
        labels={'Amount': 'Total Amount (in $)', 'Week': 'Week Number'},
        template='plotly_white'
    )
    with col2:
        st.plotly_chart(fig2)

    # Transaction Frequency by Category
    #st.markdown("## Transaction Frequency by Category")
    category_count = df['Category'].value_counts().reset_index()
    category_count.columns = ['Category', 'Count']

    fig3 = px.funnel(
        df,
        x='Category',
        y='Amount',
        title='Total Transactions Funnel (By Category)',
   
    )
    with col3:
        st.plotly_chart(fig3)

    # # Display latest transactions
    # st.markdown("## Latest Transactions")
    # latest_transactions = df.sort_values(by='Date', ascending=False).head(5)
    # st.dataframe(latest_transactions)

