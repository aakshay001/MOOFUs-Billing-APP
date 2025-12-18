# ui_products.py
import streamlit as st
import pandas as pd

def products_tab(products):
    st.header("📦 Manage Products")
    
    tab1, tab2 = st.tabs(["Add Product", "View Products"])
    
    with tab1:
        with st.form("add_product"):
            st.subheader("Add New Product")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                name = st.text_input("Product Name *", key="prod_name")
                hsn = st.text_input("HSN Code", key="prod_hsn")
                price = st.number_input("Price", min_value=0.0, step=0.01, key="prod_price")
            
            with col2:
                gst = st.number_input("GST %", min_value=0.0, max_value=100.0, step=0.5, key="prod_gst")
                stock = st.number_input("Initial Stock", min_value=0, value=0, key="prod_stock")
                mfg = st.text_input("Manufacturing Date", key="prod_mfg", placeholder="DD/MM/YYYY")
            
            with col3:
                exp = st.text_input("Expiry Date", key="prod_exp", placeholder="DD/MM/YYYY")
                free = st.number_input("Free Quantity", min_value=0, value=0, key="prod_free")
                discount = st.number_input("Discount %", min_value=0.0, max_value=100.0, step=0.5, key="prod_discount")
            
            if st.form_submit_button("Add Product", type="primary"):
                if name:
                    new_id = 1 if products.empty else int(products['id'].max()) + 1
                    
                    new_product = {
                        'id': new_id,
                        'name': name,
                        'hsn': hsn,
                        'price': price,
                        'gst': gst,
                        'stock': stock,
                        'mfg': mfg,
                        'exp': exp,
                        'free': free,
                        'discount': discount
                    }
                    
                    products = pd.concat([products, pd.DataFrame([new_product])], ignore_index=True)
                    st.success(f"✅ Product '{name}' added successfully!")
                    st.rerun()
                else:
                    st.error("Please enter product name")
    
    with tab2:
        st.subheader("All Products")
        
        if products.empty:
            st.info("No products added yet.")
        else:
            st.dataframe(products, width='stretch')
            
            with st.expander("Delete Product"):
                del_id = st.selectbox("Select product to delete", products['id'].tolist(),
                                     format_func=lambda x: products[products.id==x].iloc[0]['name'])
                
                if st.button("🗑️ Delete Product", type="secondary"):
                    products = products[products.id != del_id]
                    st.success("Product deleted!")
                    st.rerun()
    
    return products
