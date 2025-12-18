# ui_customers.py
import streamlit as st
import pandas as pd

def customers_tab(customers):
    st.header("👥 Manage Customers")
    
    tab1, tab2 = st.tabs(["Add Customer", "View Customers"])
    
    with tab1:
        with st.form("add_customer"):
            st.subheader("Add New Customer")
            
            col1, col2 = st.columns(2)
            
            with col1:
                name = st.text_input("Customer Name *", key="cust_name")
                phone = st.text_input("Phone", key="cust_phone")
                gstin = st.text_input("GSTIN", key="cust_gstin")
                address = st.text_area("Billing Address", key="cust_address")
                place = st.text_input("Place of Supply", key="cust_place")
            
            with col2:
                ship_name = st.text_input("Shipping Name", key="ship_name")
                ship_phone = st.text_input("Shipping Phone", key="ship_phone")
                ship_gstin = st.text_input("Shipping GSTIN", key="ship_gstin")
                ship_address = st.text_area("Shipping Address", key="ship_address")
            
            if st.form_submit_button("Add Customer", type="primary"):
                if name:
                    new_id = 1 if customers.empty else int(customers['id'].max()) + 1
                    
                    new_customer = {
                        'id': new_id,
                        'name': name,
                        'phone': phone,
                        'gstin': gstin,
                        'address': address,
                        'place': place,
                        'ship_name': ship_name,
                        'ship_address': ship_address,
                        'ship_phone': ship_phone,
                        'ship_gstin': ship_gstin
                    }
                    
                    customers = pd.concat([customers, pd.DataFrame([new_customer])], ignore_index=True)
                    st.success(f"✅ Customer '{name}' added successfully!")
                    st.rerun()
                else:
                    st.error("Please enter customer name")
    
    with tab2:
        st.subheader("All Customers")
        
        if customers.empty:
            st.info("No customers added yet.")
        else:
            st.dataframe(customers, width='stretch')
            
            with st.expander("Delete Customer"):
                del_id = st.selectbox("Select customer to delete", customers['id'].tolist(),
                                     format_func=lambda x: customers[customers.id==x].iloc[0]['name'])
                
                if st.button("🗑️ Delete Customer", type="secondary"):
                    customers = customers[customers.id != del_id]
                    st.success("Customer deleted!")
                    st.rerun()
    
    return customers
