# ui_reports.py
import streamlit as st
import pandas as pd
import os
from datetime import datetime
from data_utils import get_month_year_folder

def reports_tab(bills, items_df, customers):
    st.header("📊 Sales Reports & Ledger")
    
    report_tabs = st.tabs(["Sales Summary", "Customer Ledger"])
    
    # Sales Summary
    with report_tabs[0]:
        if bills.empty:
            st.info("No bills generated yet.")
        else:
            col1, col2, col3 = st.columns(3)
            
            with col1:
                filter_fy = st.selectbox("Financial Year", ["All"] + list(bills.fy.unique()), key="filter_fy_select")
            
            with col2:
                filter_status = st.selectbox("Payment Status", ["All", "Paid", "Pending", "Partially Paid"], key="filter_status_select")
            
            with col3:
                filter_customer = st.selectbox(
                    "Customer",
                    ["All"] + list(customers.name.tolist()) if not customers.empty else ["All"],
                    key="filter_customer_select"
                )
            
            filtered_bills = bills.copy()
            
            if filter_fy != "All":
                filtered_bills = filtered_bills[filtered_bills.fy == filter_fy]
            
            if filter_status != "All":
                filtered_bills = filtered_bills[filtered_bills.payment_status == filter_status]
            
            if filter_customer != "All":
                cust_id_filter = customers[customers.name == filter_customer].iloc[0]['id']
                filtered_bills = filtered_bills[filtered_bills.customer_id == cust_id_filter]
            
            st.subheader("Summary")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Bills", len(filtered_bills))
            
            with col2:
                total_sales = filtered_bills['grand_total'].sum()
                st.metric("Total Sales", f"₹{total_sales:,.2f}")
            
            with col3:
                paid_bills = filtered_bills[filtered_bills.payment_status == "Paid"]
                paid_amount = paid_bills['grand_total'].sum()
                st.metric("Paid Amount", f"₹{paid_amount:,.2f}")
            
            with col4:
                pending_bills = filtered_bills[filtered_bills.payment_status.isin(["Pending", "Partially Paid"])]
                pending_amount = pending_bills['grand_total'].sum()
                st.metric("Pending Amount", f"₹{pending_amount:,.2f}")
            
            st.divider()
            
            st.subheader("Bills List")
            
            if not filtered_bills.empty:
                display_bills = filtered_bills.merge(
                    customers[['id', 'name']],
                    left_on='customer_id',
                    right_on='id',
                    how='left'
                )
                
                display_cols = ['bill_no', 'bill_date', 'name', 'subtotal', 'cgst', 'sgst', 'igst', 'grand_total', 'payment_status']
                st.dataframe(display_bills[display_cols], width='stretch')
                
                csv = display_bills.to_csv(index=False)
                st.download_button(
                    label="📥 Export to CSV",
                    data=csv,
                    file_name=f"sales_report_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                    key="export_csv_btn"
                )
            else:
                st.info("No bills match the selected filters.")
    
    # Customer Ledger
    with report_tabs[1]:
        st.subheader("Customer-wise Ledger")
        
        if customers.empty or bills.empty:
            st.info("No customer transactions available.")
        else:
            selected_customer = st.selectbox(
                "Select Customer",
                customers.name.tolist(),
                key="ledger_customer_select"
            )
            
            if selected_customer:
                cust_id_ledger = customers[customers.name == selected_customer].iloc[0]['id']
                customer_bills = bills[bills.customer_id == cust_id_ledger].copy()
                
                if not customer_bills.empty:
                    total_invoices = len(customer_bills)
                    total_amount = customer_bills['grand_total'].sum()
                    paid_amount = customer_bills[customer_bills.payment_status == "Paid"]['grand_total'].sum()
                    pending_amount = customer_bills[customer_bills.payment_status.isin(["Pending", "Partially Paid"])]['grand_total'].sum()
                    
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.metric("Total Invoices", total_invoices)
                    with col2:
                        st.metric("Total Amount", f"₹{total_amount:,.2f}")
                    with col3:
                        st.metric("Paid", f"₹{paid_amount:,.2f}")
                    with col4:
                        st.metric("Outstanding", f"₹{pending_amount:,.2f}")
                    
                    st.divider()
                    
                    st.subheader("Transaction History")
                    customer_bills_display = customer_bills[['bill_no', 'bill_date', 'subtotal', 'cgst', 'sgst', 'igst', 'grand_total', 'payment_status']]
                    customer_bills_display = customer_bills_display.sort_values('bill_date', ascending=False)
                    st.dataframe(customer_bills_display, width='stretch')
                    
                    ledger_csv = customer_bills_display.to_csv(index=False)
                    st.download_button(
                        label="📥 Export Customer Ledger",
                        data=ledger_csv,
                        file_name=f"ledger_{selected_customer}_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv",
                        key="export_ledger_btn"
                    )
                    
                    st.subheader("Customer Bill Files")
                    customer_obj = customers[customers.id == cust_id_ledger].iloc[0]
                    
                    # FIXED: Use enumerate to create unique keys
                    for idx, (bill_idx, bill) in enumerate(customer_bills.iterrows()):
                        folder_path = get_month_year_folder(bill['bill_date'], customer_obj['name'])
                        pdf_path = f"{folder_path}/{bill['bill_no'].replace('/', '_')}.pdf"
                        
                        if os.path.exists(pdf_path):
                            with open(pdf_path, "rb") as f:
                                pdf_data = f.read()
                            
                            col_info, col_btn = st.columns([3, 1])
                            with col_info:
                                status_badge = "🟢" if bill['payment_status'] == "Paid" else "🔴" if bill['payment_status'] == "Pending" else "🟠"
                                st.write(f"{status_badge} {bill['bill_no']} - {bill['bill_date']} - ₹{bill['grand_total']:.2f}")
                            with col_btn:
                                # Use unique key with index
                                st.download_button(
                                    label="Download",
                                    data=pdf_data,
                                    file_name=f"{bill['bill_no'].replace('/', '_')}.pdf",
                                    mime="application/pdf",
                                    key=f"ledger_download_{bill['id']}_{idx}"  # FIXED: Use bill ID + index
                                )
                else:
                    st.info(f"No transactions found for {selected_customer}")
