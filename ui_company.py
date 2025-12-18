# ui_company.py
import streamlit as st
import pandas as pd
from data_utils import save_csv, COMPANY_FILE, safe_str

def company_tab(company_df):
    st.header("🏢 Company Details")
    c = company_df.loc[0]
    
    col1, col2 = st.columns(2)
    with col1:
        name = st.text_input("Company Name", safe_str(c['name']), key="company_name")
        gstin = st.text_input("GSTIN", safe_str(c['gstin']), key="company_gstin")
        phone = st.text_input("Phone Number", safe_str(c.get('phone', '')), key="company_phone")
    
    with col2:
        msme = st.text_input("MSME Number (Optional)", safe_str(c.get('msme', '')), key="company_msme")
        fssai = st.text_input("FSSAI Lic No. (Optional)", safe_str(c.get('fssai', '')), key="company_fssai")
        address = st.text_area("Address", safe_str(c['address']), key="company_address")
    
    if st.button("💾 Save Company Details", key="save_company"):
        company_df.loc[0] = [name, gstin, msme, fssai, phone, address]
        save_csv(company_df, COMPANY_FILE)
        st.success("✅ Company details saved successfully!")
        st.rerun()
    
    return company_df
