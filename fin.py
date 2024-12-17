import yfinance as yf
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Function to fetch stock data with error handling
def get_stock_data(ticker, start_date, end_date):
    try:
        stock_data = yf.download(ticker, start=start_date, end=end_date)
        if stock_data.empty:
            raise ValueError(f"No data found for ticker: {ticker}")
        return stock_data
    except Exception as e:
        st.error(f"Failed to fetch data for {ticker}: {e}")
        return None

# Function to find breakout days
def find_breakouts(data, volume_threshold, price_threshold):
    breakout_days = []
    for i in range(20, len(data)):
        avg_volume = data['Volume'][i-20:i].mean()
        current_volume = data['Volume'].iloc[i]
        price_change = (data['Close'].iloc[i] - data['Close'].iloc[i-1]) / data['Close'].iloc[i-1] * 100

        if (current_volume >= avg_volume * (volume_threshold / 100)) and (price_change >= price_threshold):
            buy_date = data.index[i]
            breakout_days.append({
                "Buy Date": buy_date,
                "Buy Price": round(data['Close'].iloc[i], 2),
            })

    return breakout_days

# Function to calculate returns based on holding period
def calculate_returns(data, breakout_days, holding_period):
    results = []
    for breakout in breakout_days:
        buy_date = breakout["Buy Date"]
        if buy_date + timedelta(days=holding_period) in data.index:
            sell_price = data['Close'].loc[buy_date + timedelta(days=holding_period)]
            buy_price = breakout["Buy Price"]
            return_pct = ((sell_price - buy_price) / buy_price) * 100
            
            results.append({
                "Buy Date": buy_date,
                "Buy Price": round(buy_price, 2),
                "Sell Price": round(sell_price, 2),
                "Return (%)": round(return_pct, 2)
            })
    
    return results

# Function to save results to Google Sheets
def save_to_google_sheets(df):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("path_to_your_service_account_json_file.json", scope)
    client = gspread.authorize(creds)

    spreadsheet = client.create("Stock Breakout Results")
    sheet = spreadsheet.get_worksheet(0)

    sheet.insert_row(df.columns.tolist(), 1)
    for i, row in df.iterrows():
        sheet.insert_row(row.tolist(), i + 2)

# Streamlit App
st.title("Stock Breakout Strategy Analysis")
st.markdown("Test stock breakout strategies based on volume and price thresholds.")

# User Inputs
ticker = st.text_input("Enter Stock Ticker (e.g., AAPL):")
start_date = st.date_input("Start Date", datetime.today() - timedelta(days=365))
end_date = st.date_input("End Date", datetime.today())
volume_threshold = st.number_input("Volume Breakout Threshold (%)", min_value=100, value=200, step=10)
price_threshold = st.number_input("Daily Price Change Threshold (%)", min_value=1.0, value=2.0, step=0.5)
holding_period = st.number_input("Holding Period (Days)", min_value=1, value=10, step=1)

# Generate Report Button
if st.button("Generate Report"):
    try:
        # Fetch Stock Data
        data = get_stock_data(ticker, start_date, end_date)
        
        if data is not None:
            st.success("Stock Data Fetched Successfully!")

            # Display the fetched stock data
            st.write(f"### Fetched Data for {ticker}")
            st.dataframe(data)

            # Find Breakouts
            breakout_days = find_breakouts(data, volume_threshold, price_threshold)
            
            # Calculate Returns for each breakout day
            if breakout_days:
                return_results = calculate_returns(data, breakout_days, holding_period)
                df = pd.DataFrame(return_results)

                st.write("### Breakout Results:")
                st.dataframe(df)

                # Export to Google Sheets
                save_to_google_sheets(df)
                st.success("Results saved to Google Sheets!")

                # Export CSV
                csv_file_name = "breakout_results.csv"
                csv_data = df.to_csv(index=False).encode('utf-8')
                
                # Use Streamlit's download button for CSV download
                st.download_button(
                    label="Download CSV",
                    data=csv_data,
                    file_name=csv_file_name,
                    mime='text/csv'
                )

                # Save the CSV to a file locally (optional)
                df.to_csv(csv_file_name, index=False)
                st.write(f"Results saved as '{csv_file_name}'.")
            else:
                st.warning("No breakout days found with the given criteria.")
        else:
            st.warning("No valid stock data available.")

    except Exception as e:
        st.error(f"Error: {e}")
