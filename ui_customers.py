# ui_customers.py
import streamlit as st
import pandas as pd
from data_utils import save_csv, CUSTOMERS_FILE

def customers_tab(customers):
    st.header("👥 Customer Management")
    
    with st.expander("➕ Add New Customer", expanded=False):
        st.subheader("Billing Details")
        col1, col2 = st.columns(2)
        
        with col1:
            cname = st.text_input("Customer Name", key="cust_name")
            phone = st.text_input("Phone Number", key="cust_phone")
            gst = st.text_input("GSTIN (Optional)", key="cust_gstin")
            place = st.text_input("Place of Supply", key="cust_place")
        
        with col2:
            addr = st.text_area("Billing Address", key="cust_address")
        
        st.divider()
        st.subheader("Shipping Details")
        
        same_as_billing = st.checkbox("Same as Billing Address", value=True, key="same_billing")
        
        col3, col4 = st.columns(2)
        
        with col3:
            ship_name = st.text_input("Ship To Name", value=cname if same_as_billing else "", disabled=same_as_billing, key="cust_ship_name")
            ship_phone = st.text_input("Ship Phone", value=phone if same_as_billing else "", disabled=same_as_billing, key="cust_ship_phone")
            ship_gstin = st.text_input("Ship GSTIN", value=gst if same_as_billing else "", disabled=same_as_billing, key="cust_ship_gstin")
        
        with col4:
            ship_addr = st.text_area("Shipping Address", value=addr if same_as_billing else "", disabled=same_as_billing, key="cust_ship_address")
        
        if st.button("Add Customer", key="add_customer_btn"):
            if cname and phone:
                new_id = 1 if customers.empty else int(customers.id.max()) + 1
                
                if same_as_billing:
                    ship_name = cname
                    ship_phone = phone
                    ship_gstin = gst
                    ship_addr = addr
                
                new_row = pd.DataFrame([[new_id, cname, phone, gst, addr, place, ship_name, ship_addr, ship_phone, ship_gstin]], 
                                     columns=['id','name','phone','gstin','address','place','ship_name','ship_address','ship_phone','ship_gstin'])
                customers = pd.concat([customers, new_row], ignore_index=True)
                save_csv(customers, CUSTOMERS_FILE)
                st.success(f"✅ Customer '{cname}' added successfully!")
                st.rerun()
            else:
                st.error("Please enter customer name and phone number")
    
    st.subheader("Customer List")
    if not customers.empty:
        st.dataframe(customers, width='stretch')
    else:
        st.info("No customers added yet.")
    
    return customers
