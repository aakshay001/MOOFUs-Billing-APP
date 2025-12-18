# app.py
import streamlit as st
import os
from data_utils import load_all_data, save_all_data, load_settings, save_settings
from ui_company import company_tab
from ui_customers import customers_tab
from ui_products import products_tab
from ui_stock import stock_management_tab
from ui_billing import create_bill_tab, view_bill_tab, edit_bill_tab
from ui_reports import reports_tab


# Create directories if they don't exist (cloud compatible)
for folder in ['data', 'bills', 'assets']:
    os.makedirs(folder, exist_ok=True)


st.set_page_config(page_title="MOOFU's Billing APP", page_icon= "🌿", layout="wide")

# Load data including batches and stock movements
customers, products, bills, items_df, company_df, settings_df, batches_df, stock_movements_df = load_all_data()

# Load saved logo and UPI
saved_logo_path = settings_df.loc[0, 'logo_path'] if not settings_df.empty else ''
saved_upi_id = settings_df.loc[0, 'upi_id'] if not settings_df.empty else ''

# Sidebar settings
st.sidebar.header("⚙️ Invoice Settings")

if saved_logo_path and os.path.exists(saved_logo_path):
    st.sidebar.image(saved_logo_path, caption="Current Logo", width=150)
    st.sidebar.caption(f"📁 {saved_logo_path}")

logo_file = st.sidebar.file_uploader(
    "Upload/Update Company Logo", 
    type=["png","jpg","jpeg"],
    help="Upload once - will be used for all invoices"
)

if saved_upi_id:
    st.sidebar.info(f"💳 Current UPI: {saved_upi_id}")

upi_id_input = st.sidebar.text_input(
    "UPI ID (for QR Code)", 
    value=saved_upi_id,
    placeholder="yourupi@bank",
    key="sidebar_upi",
    help="Enter once - will be used for all invoices"
)

logo_path = saved_logo_path
upi_id = upi_id_input

if logo_file:
    ext = logo_file.name.split(".")[-1].lower()
    logo_path = f"assets/logo.{ext}"
    with open(logo_path, "wb") as f: 
        f.write(logo_file.getbuffer())
    st.sidebar.success("✅ Logo uploaded!")

if st.sidebar.button("💾 Save Settings", key="save_settings_btn"):
    save_settings(logo_path, upi_id)
    st.sidebar.success("✅ Settings saved! Logo and UPI will be used for all invoices.")
    st.rerun()

if upi_id != saved_upi_id and not logo_file:
    save_settings(logo_path, upi_id)

# Tabs - Added Stock Management
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
    "🏢 Company","👥 Customers","📦 Products","📊 Stock & Batches",
    "🧾 Create Bill","👁️ View Bill","✏️ Edit Bill","📈 Reports"
])

with tab1:
    company_df = company_tab(company_df)

with tab2:
    customers = customers_tab(customers)

with tab3:
    products = products_tab(products)

with tab4:
    products, batches_df, stock_movements_df = stock_management_tab(products, batches_df, stock_movements_df)

with tab5:
    # FIXED: Pass all required arguments including batches_df, stock_movements_df, logo_path, upi_id
    customers, products, bills, items_df, company_df, batches_df, stock_movements_df = create_bill_tab(
        customers, products, bills, items_df, company_df, batches_df, stock_movements_df, logo_path, upi_id
    )

with tab6:
    view_bill_tab(bills, items_df, customers)

with tab7:
    # FIXED: Pass all required arguments
    bills, items_df, products, batches_df, stock_movements_df = edit_bill_tab(
        bills, items_df, customers, products, company_df, batches_df, stock_movements_df, logo_path, upi_id
    )

with tab8:
    reports_tab(bills, items_df, customers)

# Save all data including batches and stock movements
save_all_data(customers, products, bills, items_df, company_df, batches_df, stock_movements_df)

# Footer
st.divider()
st.markdown(
    """
    <div style='text-align: center; color: gray; padding: 20px;'>
        <p>🌿 MOOFU's Billbook - Complete Inventory & GST Invoice Management</p>
        <p style='font-size: 12px;'>Made with ❤️ using Streamlit</p>
    </div>
    """,
    unsafe_allow_html=True
)

