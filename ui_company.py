# ui_company.py
import streamlit as st
import pandas as pd
from data_utils import safe_str

def company_tab(company_df):
    st.header("🏢 Company Details")
    
    with st.form("company_form"):
        name = st.text_input("Company Name", value=safe_str(company_df.loc[0, 'name']))
        gstin = st.text_input("GSTIN", value=safe_str(company_df.loc[0, 'gstin']))
        
        col1, col2 = st.columns(2)
        with col1:
            msme = st.text_input("MSME Registration", value=safe_str(company_df.loc[0, 'msme']))
        with col2:
            fssai = st.text_input("FSSAI License", value=safe_str(company_df.loc[0, 'fssai']))
        
        phone = st.text_input("Phone Number", value=safe_str(company_df.loc[0, 'phone']))
        address = st.text_area("Address", value=safe_str(company_df.loc[0, 'address']))
        
        if st.form_submit_button("💾 Save Company Details", type="primary"):
            company_df.loc[0, 'name'] = name
            company_df.loc[0, 'gstin'] = gstin
            company_df.loc[0, 'msme'] = msme
            company_df.loc[0, 'fssai'] = fssai
            company_df.loc[0, 'phone'] = phone
            company_df.loc[0, 'address'] = address
            
            st.success("✅ Company details saved!")
            st.rerun()
    
    return company_df
