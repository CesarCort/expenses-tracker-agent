import gspread
import os
import toml
from google.oauth2.service_account import Credentials
from datetime import datetime
from collections import defaultdict

def get_client():
    """
    Get the client for the Google Sheet "home_expenses".
    """
    SCOPES = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    base_path = os.path.dirname(__file__)
    creds_path = os.path.join(base_path, "../secrets/creds.json")
    creds = Credentials.from_service_account_file(
        creds_path,
        scopes=SCOPES,
    )
    client = gspread.authorize(creds)
    return client

def get_wallets():
    """
    Get the wallets from the Google Sheet "home_expenses" in the sheet "data".
    """
    client = get_client()
    sheet = client.open("home_expenses").worksheet("wallets") #specidig sheetname wallets
    rows = sheet.get_all_values()[1:]
    wallets = [row[0] for row in rows]
    return wallets

def get_refund_to():
    """
    Get the names of the people to refund the expense from the Google Sheet "home_expenses" in the sheet "refunds_to".
    """
    
    client = get_client()
    sheet = client.open("home_expenses").worksheet("refunds_to") #specidig sheetname wallets
    rows = sheet.get_all_values()[1:]
    wallets = [row[0] for row in rows]
    return wallets


def get_current_date():
    """
    Get the current date in format: YYYY-MM-DD
    """
    return datetime.now().strftime('%Y-%m-%d')
    
def save_expense_data(description: str, amount: float, date: str, currency: str, category: str = '', wallet: str = '', refund_to: str = ''):
    """
    Save expense data in a text file. If dont have all fields, request the user to provide the missing fields.
    Args:
        description (str): The description of the expense.
        amount (float): The amount of the expense.
        date (str): The date of the expense. Convert to format: YYYY-MM-DD
        currency (str): The currency of the expense. Select between USD, PEN.
        category (str): The category infered by the agent from the description or the user.
        wallet (str): The wallet of the expense. If not provided, request the user to provide the wallet from the list of wallets using the tool get_wallets. If the user provides the wallet, check with get_wallets if the wallet is valid and select the wallet from the list of wallets.
        refund_to (str): The name of the person to refund the expense. If not provided, request the user to provide the name of the person to refund the expense from the list of names using the tool get_refund_to. If the user provides the name, check with get_refund_to if the name is valid and select the name from the list of names.
    """
    if currency not in ['USD', 'PEN']:
        return "Invalid currency. Select between USD, PEN."
    # date = datetime.strptime(date, '%d %b %Y').strftime('%Y-%m-%d')
    # all args to lowercase
    description = description.lower()
    category = category.lower() if category else None
    refund_to = refund_to.lower() if refund_to else None

    write_to_google_sheet(description, amount, date, currency, category, wallet, refund_to)
    return f"Expense data saved: description: {description}, amount: {amount}, date: {date}, currency: {currency}, category: {category}, wallet: {wallet}, refund_to: {refund_to}"

def write_to_google_sheet(description: str, amount: float, date: str, currency: str, category: str = '', wallet: str = '', refund_to: str = ''):
    """
    Write expense data to a Google Sheet.
    Args:
        description (str): The description of the expense.
        amount (float): The amount of the expense.
        date (str): The date of the expense. format: YYYY-MM-DD
        currency (str): The currency of the expense.
        category (str): The category infered by the agent from the description or the user.
        wallet (str): The wallet of the expense. 
        refund_to (str): The name of the person to refund the expense.
    """
    client = get_client()
    sheet = client.open("home_expenses").worksheet("data") #specidig sheetname data
    date = datetime.strptime(date, "%Y-%m-%d").strftime("%d/%m/%Y")
    # date	description	amount	currency	category
    data = [date, description, amount, currency, category, wallet, refund_to]

    sheet.append_row(data)
    return f"Expense data saved: description: {description}, amount: {amount}, date: {date}, currency: {currency}, category: {category}, wallet: {wallet}, refund_to: {refund_to}"


def get_summary_between_dates(start_date: str, end_date: str):
    """
    Get the summary of the expenses between start and end date from the Google Sheet "home_expenses" in the sheet "data".
    Args:
        start_date (str): The start date of the summary. format: YYYY-MM-DD
        end_date (str): The end date of the summary. format: YYYY-MM-DD
    """
    try:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    except ValueError:
        return "Invalid date format. Please use YYYY-MM-DD."

    if start_dt > end_dt:
        return "Start date must be before end date."

    client = get_client()
    sheet = client.open("home_expenses").worksheet("data")
    rows = sheet.get_all_values()

    if not rows:
        return "No data found."

    # Skip header
    data_rows = rows[1:]
    
    # Aggregators
    totals = defaultdict(float)
    cat_totals = defaultdict(lambda: defaultdict(float))
    dow_totals = defaultdict(lambda: defaultdict(float))
    date_totals = defaultdict(lambda: defaultdict(float))
    
    valid_count = 0

    for row in data_rows:
        if len(row) < 5:
            continue
            
        row_date_str = row[0]
        try:
            row_dt = datetime.strptime(row_date_str, "%d/%m/%Y")
        except ValueError:
            continue

        if start_dt <= row_dt <= end_dt:
            try:
                amount = float(row[2])
            except ValueError:
                continue
                
            currency = row[3].strip().upper() if row[3] else "UNKNOWN"
            category = row[4].strip() if row[4] else "Uncategorized"
            
            # Aggregate
            totals[currency] += amount
            cat_totals[currency][category] += amount
            
            day_name = row_dt.strftime("%A")
            dow_totals[currency][day_name] += amount
            date_totals[currency][row_date_str] += amount
            valid_count += 1

    if valid_count == 0:
        return f"No expenses found between {start_date} and {end_date}."

    output = [f"Resumen de gastos del {start_date} al {end_date}\n"]
    
    days_es = {
        "Monday": "Lunes", "Tuesday": "Martes", "Wednesday": "Miércoles", 
        "Thursday": "Jueves", "Friday": "Viernes", "Saturday": "Sábado", "Sunday": "Domingo"
    }

    for currency in sorted(totals.keys()):
        output.append(f"--- Moneda: {currency} ---")
        output.append(f"Gasto Total: {totals[currency]:.2f}")
        
        output.append("\nTop 3 Categorías:")
        sorted_cats = sorted(cat_totals[currency].items(), key=lambda x: x[1], reverse=True)[:3]
        for cat, amt in sorted_cats:
            output.append(f"  - {cat}: {amt:.2f}")
            
        output.append("\nPor Día de la Semana:")
        day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        sorted_days = sorted(dow_totals[currency].items(), key=lambda x: day_order.index(x[0]) if x[0] in day_order else 99)
        
        for day, amt in sorted_days:
            output.append(f"  - {days_es.get(day, day)}: {amt:.2f}")

        output.append("\nPor Fecha:")
        sorted_dates = sorted(date_totals[currency].items(), key=lambda x: datetime.strptime(x[0], "%d/%m/%Y"))
        for d, amt in sorted_dates:
             output.append(f"  - {d}: {amt:.2f}")
             
        output.append("") 

    return "\n".join(output)

def get_categories():
    """
    Get the valids categories from the Google Sheet "home_expenses" in the sheet "categories".
    """
    client = get_client()
    sheet = client.open("home_expenses").worksheet("categories") #specidig sheetname categories
    rows = sheet.get_all_values()[1:]
    format = "json"
    # in toml format  
    if format == "toml":
        categories = {row[0]: row[1] for row in rows}
        return toml.dumps(categories)
    elif format == "json":
        categories = [ {"category": row[0], "description": row[1]} for row in rows]
        return categories
    else:
        return categories
