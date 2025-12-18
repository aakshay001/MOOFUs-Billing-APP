# ui_products.py
import streamlit as st
import pandas as pd
from data_utils import save_csv, PRODUCTS_FILE

def products_tab(products):
    st.header("📦 Product Management")
    
    with st.expander("➕ Add New Product", expanded=False):
        pname = st.text_input("Product/Service Name", key="prod_name")
        hsn = st.text_input("HSN/SAC Code", key="prod_hsn")
        price = st.number_input("Price (Rs.)", min_value=0.0, step=0.01, key="prod_price")
        gst = st.number_input("GST%", min_value=0.0, max_value=100.0, value=0.0, step=0.5, key="prod_gst")
        stock = st.number_input("Stock", min_value=0, value=0, key="prod_stock")
        
        col_a, col_b, col_c, col_d = st.columns(4)
        with col_a:
            mfg = st.text_input("MFG", key="prod_mfg")
        with col_b:
            exp = st.text_input("EXP", key="prod_exp")
        with col_c:
            free = st.number_input("Free", min_value=0, value=0, key="prod_free")
        with col_d:
            discount = st.number_input("Disc%", min_value=0.0, value=0.0, step=0.5, key="prod_discount")
        
        if st.button("Add Product", key="add_product_btn"):
            if pname:
                new_id = 1 if products.empty else int(products.id.max()) + 1
                new_row = pd.DataFrame([[new_id, pname, hsn, price, gst, stock, mfg, exp, free, discount]], 
                                     columns=['id','name','hsn','price','gst','stock','mfg','exp','free','discount'])
                products = pd.concat([products, new_row], ignore_index=True)
                save_csv(products, PRODUCTS_FILE)
                st.success(f"✅ Product '{pname}' added!")
                st.rerun()
            else:
                st.error("Please enter product name")
    
    st.subheader("Product List")
    if not products.empty:
        st.dataframe(products, width='stretch')
    else:
        st.info("No products added yet.")
    
    return products
