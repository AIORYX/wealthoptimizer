import os
from datetime import datetime
import time
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from st_aggrid import AgGrid, GridOptionsBuilder, DataReturnMode, GridUpdateMode, AgGridTheme
from dotenv import load_dotenv
import calendar

# Local modules
from src.components import side_bars as sb, charts
import src.modules.sql_handler as sq
import src.modules.initialte_app as init 
import src.modules.login as lo
import src.modules.upload as upload


# Load environment variables
load_dotenv()

# =============================================================================
# Page Configuration & Global CSS
# =============================================================================
st.set_page_config(page_title="Home", layout="wide", page_icon=":material/home:")

GLOBAL_CSS = """
<style>
.shadow-container {
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
    padding: 20px;
    border-radius: 10px;
    background-color: white;
}
.title {
    font-size: 48px;
    font-weight: bold;
    color: black;
    text-align: center;
    margin-top: -60px;
    margin-bottom: 10px;
}
.divider {
    border-top: 1px solid #D5D8DC;
    margin-top: 15px;
    margin-bottom: 30px;
}
</style>
"""
st.markdown(GLOBAL_CSS, unsafe_allow_html=True)
st.markdown('<h1 class="title">Wealth Optimizer</h1>', unsafe_allow_html=True)
st.markdown('<hr class="divider">', unsafe_allow_html=True)

# =============================================================================
# Utility Functions
# =============================================================================
def build_grid_options(dataframe: pd.DataFrame, selection_mode: str = 'multiple') -> dict:
    """
    Build AgGrid options for a given DataFrame.
    """
    gb = GridOptionsBuilder.from_dataframe(dataframe)
    gb.configure_pagination(paginationAutoPageSize=True)
    gb.configure_default_column(editable=True, filter=True, sortable=True, autoSizeColumns=True)
    gb.configure_selection(selection_mode=selection_mode)
    gb.configure_grid_options(domLayout='normal')
    return gb.build()

def reset_session() -> None:
    """
    Reset the session state.
    """
    st.session_state["reset_session"] = True
    st.warning("All updates were discarded!")

def add_shadow_style() -> None:
    """
    Inject additional CSS for shadow effect on containers.
    """
    shadow_style = """
    <style>
    div[data-testid='stVerticalBlock']:has(div#chat_inner):not(:has(div#chat_outer)) {
        padding-left: 5%;
        background: rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(10px);
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
        border-radius: 15px;
        border: 1px solid rgba(255, 255, 255, 0.3);
        overflow: hidden;
    }
    #chat_inner {
        max-width: 100%;
    }
    </style>
    """
    st.markdown(shadow_style, unsafe_allow_html=True)

# =============================================================================
# Charting Functions
# =============================================================================
def display_charts(df: pd.DataFrame) -> None:
    """
    Display a bar chart by category and a time series line chart for the given DataFrame.
    """
    df['Amount'] = df['Amount'].abs()
    col1, col2 = st.columns(2)
    with col1:
        category_chart = px.bar(
            df, x='Category', y='Amount', 
            title="Amount by Category", 
            labels={'Amount': 'Transaction Amount'}
        )
        st.plotly_chart(category_chart, use_container_width=True)

    with col2:
        df['Date'] = pd.to_datetime(df['Date'])
        time_chart = px.line(
            df.sort_values('Date'),
            x='Date',
            y='Amount',
            line_shape='linear',
            color='Category',
            title="Transaction Amount Over Time",
            markers=True,
            labels={'Amount': 'Transaction Amount'}
        )
        st.plotly_chart(time_chart, use_container_width=True)

def plot_financial_summary(final_df: pd.DataFrame) -> go.Figure:
    """
    Create a combined bar and line chart to display monthly Income, Expense, Investment,
    Savings, and Cumulative Savings.
    """
    
    fig = go.Figure()

    # Bar traces for Income, Expense, and Investment
    fig.add_trace(go.Bar(
        x=final_df['Month'], y=final_df['Income'],
        name='Income', marker_color='lightblue',
        offsetgroup=0, width=0.1,
        marker_line=dict(width=1, color='darkblue')
    ))
    fig.add_trace(go.Bar(
        x=final_df['Month'], y=final_df['Expense'].abs(),
        name='Expense', marker_color='deepskyblue',
        offsetgroup=1, width=0.1,
        marker_line=dict(width=1, color='darkblue')
    ))
    fig.add_trace(go.Bar(
        x=final_df['Month'], y=final_df['Investment'].abs(),
        name='Investment', marker_color='dodgerblue',
        offsetgroup=2, width=0.1,
        marker_line=dict(width=1, color='darkblue')
    ))

    # First, aggregate by MonthNum (and Month) to sum up the Savings per month.
    monthly_totals = final_df.groupby(['MonthNum']).agg({'Savings': 'sum', 'Month': 'max'}).reset_index()

    # Sort the data by MonthNum to ensure correct order.
    monthly_totals = monthly_totals.sort_values('MonthNum')

    # Compute the cumulative savings over the months.
    monthly_totals['CumulativeSavings'] = monthly_totals['Savings'].cumsum()
    # Update the traces to use the aggregated monthly totals
    fig.add_trace(go.Scatter(
        x=monthly_totals['Month'], 
        y=monthly_totals['Savings'],
        mode='lines+markers', 
        name='Savings',
        line=dict(color='navy', width=2),
        marker=dict(color='navy', size=6)
    ))

    fig.add_trace(go.Scatter(
        x=monthly_totals['Month'], 
        y=monthly_totals['CumulativeSavings'],
        mode='lines+markers', 
        name='Cumulative Savings',
        line=dict(color='steelblue', width=2, dash='dash'),
        marker=dict(color='steelblue', size=6)
    ))
    fig.update_layout(
        barmode='group',
        title="Monthly Financial Summary per Account",
        yaxis_title="Amount",
        legend=dict(
            orientation="h",
            x=0.5,
            y=1.1,
            xanchor='center',
            yanchor='bottom'
        ),
        hovermode="x unified",
        bargap=0.6,
        uniformtext_minsize=8
    )
    fig.update_traces(marker_line_width=0)
    return fig

def prepare_pivot_table(final_df: pd.DataFrame) -> pd.DataFrame:
    """
    Pivot the summary DataFrame so that months become rows and key financial metrics become columns.
    """
    grouped_df = final_df.groupby('Month').agg({
        'Income': 'sum',
        'Expense': 'sum',
        'Investment': 'sum',
        'Savings': 'sum',
        'CumulativeSavings': 'sum'
    }).reset_index()
    transposed_df = grouped_df.set_index('Month').T
    return transposed_df

# =============================================================================
# Financial Metrics Functions
# =============================================================================
def calculate_financial_metrics(df: pd.DataFrame) -> dict:
    """
    Calculate various financial metrics from the DataFrame.
    """
    df['Date'] = pd.to_datetime(df['Date'])
    today = pd.to_datetime('today')
    current_month, current_year = today.month, today.year

    current_month_data = df[(df['Date'].dt.month == current_month) & (df['Date'].dt.year == current_year)]
    current_month_total = current_month_data['Amount'].sum()

    last_month_data = df[(df['Date'].dt.month == current_month - 1) & (df['Date'].dt.year == current_year)]
    last_month_total = last_month_data['Amount'].sum() if not last_month_data.empty else None
    delta_last_month = current_month_total - last_month_total if last_month_total is not None else None

    last_12_months_data = df[df['Date'] >= today - pd.DateOffset(months=12)]
    monthly_totals = last_12_months_data.groupby([df['Date'].dt.year, df['Date'].dt.month])['Amount'].sum()
    # Note: Ensure that min()/idxmin() is intended (if amounts are negative, it could represent the biggest cost)
    biggest_month_total = monthly_totals.min()
    biggest_month = monthly_totals.idxmin()
    avg_12_month_total = monthly_totals.mean()
    delta_12_month_avg = biggest_month_total - avg_12_month_total

    current_year_data = df[df['Date'].dt.year == current_year]
    current_year_total = current_year_data['Amount'].sum()
    last_year_data = df[df['Date'].dt.year == current_year - 1]
    delta_year_to_date = (current_year_total - last_year_data['Amount'].sum()) if not last_year_data.empty else None

    return {
        'Current Month Total to Date': current_month_total,
        'Delta compared to Last Month': delta_last_month,
        'Biggest Month Total in Last 12 Months': biggest_month_total,
        'Biggest Month (Year, Month)': biggest_month,
        'Delta compared to 12 Month Average': delta_12_month_avg,
        'Current Year to Date Cost': current_year_total,
        'Delta compared to Last Year to Date': delta_year_to_date,
        'Average for last 12 Months': avg_12_month_total
    }

def display_financial_metrics_summary(results: dict) -> None:
    """
    Display calculated financial metrics in a four-column layout.
    """
    col1, col2, col3, col4 = st.columns(4)
    current_month_total = results.get('Current Month Total to Date', 0)
    delta_last_month = results.get('Delta compared to Last Month')
    col1.metric("Current Month Total", f"${current_month_total:,.2f}",
                f"{delta_last_month:+,.2f}" if delta_last_month is not None else "N/A")

    biggest_month_total = results.get('Biggest Month Total in Last 12 Months', 0)
    delta_12_month_avg = results.get('Delta compared to 12 Month Average')
    col2.metric("Biggest Month (12 Mo)", f"${biggest_month_total:,.2f}",
                f"{delta_12_month_avg:+,.2f}" if delta_12_month_avg is not None else "N/A")

    current_year_total = results.get('Current Year to Date Cost', 0)
    delta_year_to_date = results.get('Delta compared to Last Year to Date')
    col3.metric("Year to Date Total", f"${current_year_total:,.2f}",
                f"{delta_year_to_date:+,.2f}" if delta_year_to_date is not None else "N/A")

    monthly_average = results.get('Average for last 12 Months', 0)
    col4.metric("Average over (12 Mo)", f"${monthly_average:,.2f}", "0")

def display_income_expense_metrics(header: str, income_amount: float, expense_amount: float) -> None:
    """
    Display income and expense metrics within a styled container.
    """
    add_shadow_style()
    container = st.container()
    st.markdown("<div id='chat_outer'></div>", unsafe_allow_html=True)
    with container:
        st.markdown("<div id='chat_inner'></div>", unsafe_allow_html=True)
        st.markdown(f"##### {header}")
        col1, col2 = st.columns(2)
        with col1:
            st.metric(label='Income ($)', value=f"$ {income_amount:,.2f}",
                      delta=f"{(income_amount - expense_amount):,.2f}", delta_color="normal")
        with col2:
            delta_pct = ((expense_amount / income_amount) * 100) if income_amount else 0
            st.metric(label='Expense ($)', value=f"$ {expense_amount:,.2f}",
                      delta=f"{delta_pct:.2f} %", delta_color="off")

# =============================================================================
# Financial Summary Functions
# =============================================================================
def calculate_financial_summary(income_df: pd.DataFrame, expense_df: pd.DataFrame, months_order: list) -> pd.DataFrame:
    """
    Combine income and expense data, calculate sums, and compute savings.
    """
    income_df['Date'] = pd.to_datetime(income_df['Date'])
    expense_df['Date'] = pd.to_datetime(expense_df['Date'])

    income_df['Type'] = 'Income'
    expense_df['Type'] = 'Expense'

    combined_df = pd.concat([income_df, expense_df], ignore_index=True)
    combined_df['Year'] = combined_df['Date'].dt.year
    
    combined_df['MonthNum'] = combined_df['Date'].dt.month

    income_sum = combined_df[combined_df['Type'] == 'Income'].groupby(['Year', 'MonthNum', 'AccountName']).agg(
        Income=('Amount', 'sum')).reset_index()

    expense_sum = combined_df[(combined_df['Type'] == 'Expense') & (combined_df['Category'] != 'Investment')].groupby(
        ['Year', 'MonthNum', 'AccountName']).agg(Expense=('Amount', 'sum')).reset_index()

    investment_sum = combined_df[combined_df['Category'] == 'Investment'].groupby(
        ['Year', 'MonthNum', 'AccountName']).agg(Investment=('Amount', 'sum')).reset_index()

    final_df = pd.merge(income_sum, expense_sum, on=['Year', 'MonthNum', 'AccountName'], how='outer')
    final_df = pd.merge(final_df, investment_sum, on=['Year', 'MonthNum', 'AccountName'], how='outer')

    final_df[['Income', 'Expense', 'Investment']] = final_df[['Income', 'Expense', 'Investment']].fillna(0)
    final_df['Savings'] = final_df['Income'] + final_df['Expense'] - final_df['Investment']
    
        # Sort by Year, MonthNum, and AccountName (if needed)
    final_df = final_df.sort_values(by=['Year', 'MonthNum', 'AccountName'])

    # If you want a global cumulative sum across all data:
    #final_df['CumulativeSavings'] = final_df['Savings'].cumsum()

    # OR, if you need cumulative savings per account:
    final_df['CumulativeSavings'] = final_df.groupby('AccountName')['Savings'].cumsum()

    final_df['Month'] = final_df['MonthNum'].apply(lambda x: calendar.month_name[x])
    final_df['Month'] = pd.Categorical(final_df['Month'], categories=months_order, ordered=True)
    final_df = final_df.sort_values(by=['Month'])
    return final_df

def show_financial_dashboard(df: pd.DataFrame) -> None:
    """
    Display the financial dashboard with various charts.
    The DataFrame should include 'Date', 'Amount', and 'Category' columns.
    """
    # Determine TransactionType including Investment logic.
    df["TransactionType"] = df["Category"].apply(
        lambda x: "Income" if x.lower() == "income" 
        else ("Investment" if x.lower() == "investment" else "Expense")
    )
    template = "plotly_white"

    # Chart 1: Monthly Expense Trend
    df["Month"] = df["Date"].dt.to_period("M").dt.to_timestamp()
    monthly_expense = df[df["TransactionType"] == "Expense"].groupby("Month")["Amount"].sum().reset_index()
    fig_line = px.line(
        monthly_expense, x="Month", y="Amount",
        title="Monthly Expense Trend",
        labels={"Amount": "Expenses ($)"},
        template=template,
        markers=True
    )
    fig_line.update_layout(title_x=0.5, margin=dict(l=20, r=20, t=40, b=20))

    # Chart 2: Expense Distribution (Pie Chart)
    category_summary = (
    df[df["TransactionType"] == "Expense"]
    .groupby("Category", as_index=False)["Amount"]
    .sum()
    )
    # Convert expenses to positive values for proper pie chart representation
    category_summary["Amount"] = category_summary["Amount"].abs()

    fig_pie = px.pie(
        category_summary, 
        names="Category", 
        values="Amount",
        title="Expenses by Category",
        template=template, color_discrete_map="blue"
    )
    fig_pie.update_layout(title_x=0.5, margin=dict(l=20, r=20, t=40, b=20))

    # Chart 3: Expenses by Category (Bar Chart)
    fig_bar = px.bar(
        category_summary, x="Category", y="Amount",
        title="Expenses by Category (Bar Chart)",
        labels={"Amount": "Total Expenses ($)"},
        template=template
    )
    fig_bar.update_layout(title_x=0.5, margin=dict(l=20, r=20, t=40, b=20))

    # Chart 4: Distribution of Transaction Amounts (Histogram)
    fig_hist = px.histogram(
        df, x="Amount", nbins=30,
        title="Distribution of Transaction Amounts",
        labels={"Amount": "Transaction Amount ($)"},
        template=template
    )
    fig_hist.update_layout(title_x=0.5, margin=dict(l=20, r=20, t=40, b=20))

    col1, col2, col3 = st.columns(3)
    with col1:
        st.plotly_chart(fig_line, use_container_width=True)
    with col2:
        st.plotly_chart(fig_pie, use_container_width=True)
    with col3:
        st.plotly_chart(fig_bar, use_container_width=True)
    st.plotly_chart(fig_hist, use_container_width=True)

    # Ensure 'Date' is in datetime format
    df["Date"] = pd.to_datetime(df["Date"])

    # Filter for expenses and extract day-of-month
    daily_expense_df = df[df["TransactionType"] == "Expense"].copy()
    daily_expense_df["Day"] = daily_expense_df["Date"].dt.day

    # Group data by Day only, summing expenses and converting to positive values
    daily_summary = (
    daily_expense_df.groupby(["Month", "Day"], as_index=False)["Amount"]
    .sum()
    )
    daily_summary["Amount"] = daily_summary["Amount"].abs()  # convert to positive values if needed

    # Create the line chart: x-axis is Day, with separate lines for each Month
    fig_daily = px.area(
        daily_summary,
        x="Day",
        y="Amount",
        color="Month",
        title="Daily Expense by Month",
        labels={"Amount": "Daily Expense ($)", "Day": "Day of Month"},
        template=template,
        markers=True
    )
    fig_daily.update_layout(title_x=0.5, margin=dict(l=20, r=20, t=40, b=20))

    st.plotly_chart(fig_daily, use_container_width=True)

# =============================================================================
# Main Application Logic
# =============================================================================
def main() -> None:
    """
    Main function to run the Streamlit application.
    """
    months_order = ['January', 'February', 'March', 'April', 'May', 'June', 
                    'July', 'August', 'September', 'October', 'November', 'December']
   
    init.init_session_state()

    # Login process
    lo.login()

    if st.experimental_user.is_logged_in:
        init.initiate_dataset()

        # Sidebar filters
        if len(st.session_state["df"])>0:
            selected_years = sb.home_sidebar()

            df = st.session_state["df"]
            filtered_df = df[
                (df['Year'].isin(selected_years)) &
                (df['Category'].isin(st.session_state["category_filter"])) &
                (df['AccountName'].isin(st.session_state["account_filter"]))
            ]
        
            if not filtered_df.empty:
                # Standardize category strings for comparison.
                filtered_df["Category_lower"] = filtered_df["Category"].str.lower()
                total_income = filtered_df[filtered_df["Category_lower"] == "income"]["Amount"].sum()
                total_expense = filtered_df[
                    (~filtered_df["Category_lower"].isin(["income", "investment"]))
                ]["Amount"].sum()
                total_investment = filtered_df[filtered_df["Category_lower"] == "investment"]["Amount"].sum() * -1
                net = total_income + total_expense + total_investment

                # Display summary metrics
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Total Income", f"${total_income:,.2f}", help="Total Income")
                col2.metric("Total Expenses", f"${total_expense:,.2f}", help="Total Expense")
                col3.metric("Net Balance", f"${net:,.2f}", help="Total Income - Expense + Investment")
                col4.metric("Total Investment", f"${total_investment:,.2f}", help="Total Investment")

                # Aggregate table
                aggregated_df = filtered_df.groupby('Category', as_index=False).agg(
                    Total_Amount=('Amount', 'sum'),
                    Average_Amount=('Amount', 'mean')
                )
                aggregated_df['Average_Amount'] = aggregated_df['Average_Amount'].round(2)
                
                # Split data by type
                expense_df = filtered_df[filtered_df['Amount'] < 0]
                income_df = filtered_df[(filtered_df['Amount'] > 0) & (filtered_df['Category'] == 'Income')]

                # Calculate and plot financial summary
                summary_df = calculate_financial_summary(income_df, expense_df, months_order)
                pivot_summary_df=prepare_pivot_table(summary_df)

                summary_fig = plot_financial_summary(summary_df)
                st.plotly_chart(summary_fig, use_container_width=True)
                st.dataframe(pivot_summary_df, use_container_width=True)
                st.divider()
                  
                show_financial_dashboard(filtered_df)
            else:
                if len(st.session_state["df"]) > 0:
                    st.warning("Please check the filters!")
                else:
                    st.warning("Please Upload Data")
        else:  
            st.header("Please Upload transactions..")
            file_upload_status=upload.file_uploder()
            if file_upload_status:
                with st.spinner("Reloading the size...", show_time=True):
                    st.snow()
                    time.sleep(5)
                    st.markdown(
                        """
                        <meta http-equiv="refresh" content="0">
                        """,
                        unsafe_allow_html=True,
                    )
                
                
                


if __name__ == "__main__":
    main()
