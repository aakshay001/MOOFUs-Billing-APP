# data_utils.py - Google Drive version
import os
import pandas as pd
from datetime import date, datetime
from gdrive_storage import upload_csv_to_drive, download_csv_from_drive

DATA_DIR = "data"
BILL_DIR = "bills"

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(BILL_DIR, exist_ok=True)
os.makedirs("assets", exist_ok=True)

def financial_year():
    y = date.today().year
    return f"{y}-{y+1}" if date.today().month > 3 else f"{y-1}-{y}"

def next_invoice_no(bills):
    fy = financial_year()
    if bills.empty:
        count = 1
    else:
        count = len(bills[bills.fy == fy]) + 1
    return f"INV/{fy}/{count}"

def get_month_year_folder(bill_date, customer_name):
    """Create folder path based on customer and month/year"""
    dt = datetime.strptime(str(bill_date), '%Y-%m-%d')
    clean_name = "".join(c for c in customer_name if c.isalnum() or c in (' ', '-', '_')).strip()
    month_year = dt.strftime('%Y-%m')
    folder_path = f"{BILL_DIR}/{month_year}/{clean_name}"
    return folder_path

def safe_str(val, default=''):
    """Safely convert value to string"""
    if pd.isna(val) or val is None or val == '':
        return default
    return str(val)

def load_csv_from_drive(filename, default_cols):
    """Load CSV from Google Drive"""
    df = download_csv_from_drive(filename)
    if df.empty:
        df = pd.DataFrame(columns=default_cols)
    return df

def save_csv_to_drive(df, filename):
    """Save DataFrame to Google Drive"""
    upload_csv_to_drive(df, filename)

def load_settings():
    """Load persistent settings"""
    settings = load_csv_from_drive('settings.csv', ['logo_path', 'upi_id'])
    if settings.empty:
        settings.loc[0] = ['', '']
    return settings

def save_settings(logo_path, upi_id):
    """Save persistent settings"""
    settings = pd.DataFrame([[logo_path, upi_id]], columns=['logo_path', 'upi_id'])
    save_csv_to_drive(settings, 'settings.csv')

def load_all_data():
    """Load all data from Google Drive"""
    customers = load_csv_from_drive('customers.csv', ['id','name','phone','gstin','address','place','ship_name','ship_address','ship_phone','ship_gstin'])
    products = load_csv_from_drive('products.csv', ['id','name','hsn','price','gst','stock','mfg','exp','free','discount'])
    bills = load_csv_from_drive('bills.csv', ['id','bill_no','fy','customer_id','bill_date','subtotal','cgst','sgst','igst','grand_total','payment_status'])
    items_df = load_csv_from_drive('bill_items.csv', ['bill_no','product','qty','price','gst','mfg','exp','free','discount','batch_no'])
    company_df = load_csv_from_drive('company.csv', ['name','gstin','msme','fssai','phone','address'])
    settings_df = load_settings()
    batches_df = load_csv_from_drive('batches.csv', ['id','product_id','batch_no','mfg_date','exp_date','quantity','price'])
    stock_movements_df = load_csv_from_drive('stock_movements.csv', ['id','product_id','batch_no','movement_type','quantity','date','reference','notes'])
    
    # Initialize company if empty
    if company_df.empty:
        company_df.loc[0] = ['', '', '', '', '', '']
    
    # Ensure required columns exist
    for col in ['mfg','exp','free','discount','hsn']:
        if col not in products.columns:
            products[col] = '' if col in ['mfg','exp','hsn'] else 0
    
    for col in ['place','ship_name','ship_address','ship_phone','ship_gstin']:
        if col not in customers.columns:
            customers[col] = ''
    
    for col in ['msme', 'fssai', 'phone']:
        if col not in company_df.columns:
            company_df[col] = ''
    
    if 'batch_no' not in items_df.columns:
        items_df['batch_no'] = ''
    
    return customers, products, bills, items_df, company_df, settings_df, batches_df, stock_movements_df

def save_all_data(customers, products, bills, items_df, company_df, batches_df, stock_movements_df):
    """Save all dataframes to Google Drive"""
    save_csv_to_drive(company_df, 'company.csv')
    save_csv_to_drive(customers, 'customers.csv')
    save_csv_to_drive(products, 'products.csv')
    save_csv_to_drive(bills, 'bills.csv')
    save_csv_to_drive(items_df, 'bill_items.csv')
    save_csv_to_drive(batches_df, 'batches.csv')
    save_csv_to_drive(stock_movements_df, 'stock_movements.csv')

def record_stock_movement(stock_movements_df, product_id, batch_no, movement_type, quantity, reference, notes=""):
    """Record stock movement"""
    new_id = 1 if stock_movements_df.empty else int(stock_movements_df['id'].max()) + 1
    new_movement = pd.DataFrame([[
        new_id, product_id, batch_no, movement_type, quantity, 
        str(date.today()), reference, notes
    ]], columns=['id','product_id','batch_no','movement_type','quantity','date','reference','notes'])
    
    return pd.concat([stock_movements_df, new_movement], ignore_index=True)
