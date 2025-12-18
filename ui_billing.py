# ui_billing.py
import streamlit as st
import pandas as pd
import os
import base64
from datetime import date
from data_utils import (
    next_invoice_no, 
    get_month_year_folder, 
    safe_str, 
    record_stock_movement
)
from pdf_generator import generate_invoice_pdf


# PDF Viewer Function
def show_pdf(pdf_path):
    """Display PDF inline using base64 encoding"""
    with open(pdf_path, "rb") as f:
        base64_pdf = base64.b64encode(f.read()).decode("utf-8")
    pdf_display = f"""
        <iframe src="data:application/pdf;base64,{base64_pdf}"
                width="100%" height="800" type="application/pdf"></iframe>
    """
    st.markdown(pdf_display, unsafe_allow_html=True)

# CREATE BILL TAB
def create_bill_tab(customers, products, bills, items_df, company_df, batches_df, stock_movements_df, logo_path, upi_id):
    st.header("🧾 Generate Invoice")
    
    if customers.empty or products.empty:
        st.warning("⚠️ Please add customers and products first.")
        return customers, products, bills, items_df, company_df, batches_df, stock_movements_df
    
    if 'bill_created' not in st.session_state:
        st.session_state.bill_created = False
    
    if st.session_state.bill_created:
        st.success("✅ Invoice created successfully!")
        
        col_action1, col_action2 = st.columns(2)
        with col_action1:
            if st.button("➕ Create New Bill", key="new_bill_btn", type="primary"):
                st.session_state.bill_created = False
                st.rerun()
        
        with col_action2:
            if st.button("👁️ View Bills", key="goto_view_btn"):
                st.session_state.bill_created = False
    
    else:
        col1, col2, col3 = st.columns([2, 2, 1])
        
        with col1:
            cust_id = st.selectbox("Select Customer", 
                                  customers.id, 
                                  format_func=lambda x: customers[customers.id==x].iloc[0]['name'],
                                  key="bill_customer_select")
            customer = customers[customers.id==cust_id].iloc[0].to_dict()
        
        with col2:
            bill_date = st.date_input("Invoice Date", date.today(), key="bill_date_input")
        
        with col3:
            default_bill_no = next_invoice_no(bills)
            bill_no = st.text_input("Invoice No.", value=default_bill_no, key="bill_no_input")
        
        st.subheader("Tax Configuration")
        tax_option = st.radio(
            "Select Tax Type:",
            ["GST (CGST + SGST)", "IGST (Interstate)", "No Tax"],
            horizontal=True,
            key="tax_type_radio"
        )
        
        if tax_option == "GST (CGST + SGST)":
            tax_type = "GST"
        elif tax_option == "IGST (Interstate)":
            tax_type = "IGST"
        else:
            tax_type = "NO_TAX"
        
        st.subheader("Add Products")
        
        bill_items = []
        
        for idx, row in products.iterrows():
            with st.container():
                col1, col2, col3, col4, col5, col6, col7 = st.columns([3, 1.5, 1, 1, 1, 1, 1])
                
                with col1:
                    st.write(f"**{row['name']}** (HSN: {row.get('hsn', 'N/A')}) | Stock: {row.get('stock', 0)}")
                
                with col2:
                    # Get available batches for this product
                    product_batches = batches_df[batches_df.product_id == row['id']]
                    if not product_batches.empty:
                        batch_options = [""] + product_batches['batch_no'].tolist()
                        selected_batch = st.selectbox(
                            "Batch",
                            batch_options,
                            key=f"batch_{row['id']}",
                            label_visibility="collapsed"
                        )
                    else:
                        selected_batch = st.text_input("Batch", key=f"batch_{row['id']}", placeholder="No batch", label_visibility="collapsed")
                
                with col3:
                    qty = st.number_input("Qty", min_value=0, value=0, key=f"qty_{row['id']}")
                
                with col4:
                    price = st.number_input("Price", min_value=0.0, value=float(row['price']), step=0.01, key=f"price_{row['id']}")
                
                with col5:
                    free_qty = st.number_input("Free", min_value=0, value=int(row.get('free', 0)), key=f"free_{row['id']}")
                
                with col6:
                    discount = st.number_input("Disc%", min_value=0.0, max_value=100.0, value=float(row.get('discount', 0)), step=0.5, key=f"disc_{row['id']}")
                
                with col7:
                    if qty > 0:
                        subtotal = qty * price
                        disc_amount = subtotal * discount / 100
                        final = subtotal - disc_amount
                        st.success(f"Rs.{final:.2f}")
                
                if qty > 0:
                    gst_rate = float(row.get('gst', 0))
                    subtotal = qty * price
                    disc_amount = subtotal * discount / 100
                    taxable = subtotal - disc_amount
                    
                    if tax_type == "NO_TAX":
                        total = taxable
                        bill_items.append({
                            'name': row['name'],
                            'product': row['name'],
                            'hsn': row.get('hsn', ''),
                            'qty': qty,
                            'price': price,
                            'gst': gst_rate,
                            'mfg': row.get('mfg', ''),
                            'exp': row.get('exp', ''),
                            'free': free_qty,
                            'discount': discount,
                            'rate': price,
                            'taxable': taxable,
                            'cgst': 0,
                            'sgst': 0,
                            'igst': 0,
                            'total': total,
                            'batch_no': selected_batch,
                            'product_id': row['id']
                        })
                    elif tax_type == "IGST":
                        igst_amount = (taxable * gst_rate) / 100
                        total = taxable + igst_amount
                        bill_items.append({
                            'name': row['name'],
                            'product': row['name'],
                            'hsn': row.get('hsn', ''),
                            'qty': qty,
                            'price': price,
                            'gst': gst_rate,
                            'mfg': row.get('mfg', ''),
                            'exp': row.get('exp', ''),
                            'free': free_qty,
                            'discount': discount,
                            'rate': price,
                            'taxable': taxable,
                            'cgst': 0,
                            'sgst': 0,
                            'igst': igst_amount,
                            'total': total,
                            'batch_no': selected_batch,
                            'product_id': row['id']
                        })
                    else:  # GST
                        cgst_amount = (taxable * gst_rate) / 200
                        sgst_amount = (taxable * gst_rate) / 200
                        total = taxable + cgst_amount + sgst_amount
                        bill_items.append({
                            'name': row['name'],
                            'product': row['name'],
                            'hsn': row.get('hsn', ''),
                            'qty': qty,
                            'price': price,
                            'gst': gst_rate,
                            'mfg': row.get('mfg', ''),
                            'exp': row.get('exp', ''),
                            'free': free_qty,
                            'discount': discount,
                            'rate': price,
                            'taxable': taxable,
                            'cgst': cgst_amount,
                            'sgst': sgst_amount,
                            'igst': 0,
                            'total': total,
                            'batch_no': selected_batch,
                            'product_id': row['id']
                        })
        
        st.divider()
        
        # Bill Summary
        if bill_items:
            st.subheader("📋 Bill Summary")
            
            summary_df = pd.DataFrame(bill_items)
            display_cols = ['name', 'batch_no', 'qty', 'price', 'discount', 'taxable']
            
            if tax_type == "NO_TAX":
                display_cols.append('total')
            elif tax_type == "IGST":
                display_cols.extend(['igst', 'total'])
            else:
                display_cols.extend(['cgst', 'sgst', 'total'])
            
            st.dataframe(summary_df[display_cols], width='stretch')
            
            # Totals
            total_taxable = sum(item['taxable'] for item in bill_items)
            total_cgst = sum(item['cgst'] for item in bill_items)
            total_sgst = sum(item['sgst'] for item in bill_items)
            total_igst = sum(item['igst'] for item in bill_items)
            grand_total = sum(item['total'] for item in bill_items)
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Taxable Amount", f"₹{total_taxable:.2f}")
            
            with col2:
                if tax_type == "GST":
                    st.metric("CGST + SGST", f"₹{(total_cgst + total_sgst):.2f}")
                elif tax_type == "IGST":
                    st.metric("IGST", f"₹{total_igst:.2f}")
                else:
                    st.metric("Tax", "₹0.00")
            
            with col3:
                st.metric("Grand Total", f"₹{grand_total:.2f}")
            
            # Terms and Conditions
            st.subheader("Terms & Conditions")
            terms = st.text_area(
                "Terms and Conditions",
                value="Goods once sold will not be taken back. E. & O.E.",
                height=100,
                key="terms_textarea"
            )
            
            # Payment Status
            payment_status = st.selectbox(
                "Payment Status",
                ["Pending", "Paid", "Partially Paid"],
                key="payment_status_select"
            )
            
            # Generate Bill Button
            if st.button("🎯 Generate Invoice PDF", type="primary", key="generate_invoice_btn"):
                if not company_df.loc[0]['name'] or pd.isna(company_df.loc[0]['name']):
                    st.error("⚠️ Please configure company details first!")
                else:
                    # Save bill
                    new_bill_id = 1 if bills.empty else int(bills.id.max()) + 1
                    from data_utils import financial_year
                    fy = financial_year()
                    
                    new_bill = pd.DataFrame([[
                        new_bill_id, bill_no, fy, cust_id, str(bill_date),
                        total_taxable, total_cgst, total_sgst, total_igst,
                        grand_total, payment_status
                    ]], columns=['id','bill_no','fy','customer_id','bill_date',
                               'subtotal','cgst','sgst','igst','grand_total','payment_status'])
                    
                    bills = pd.concat([bills, new_bill], ignore_index=True)
                    save_csv(bills, BILLS_FILE)
                    
                    # Save items
                    for item in bill_items:
                        new_item = {
                        'bill_no': bill_no,
                        'product': item['name'],
                        'qty': item['qty'],
                        'price': item['price'],
                        'gst': item['gst'],
                        'mfg': item['mfg'],
                        'exp': item['exp'],
                        'free': item['free'],
                        'discount': item['discount'],
                        'batch_no': item.get('batch_no', '')
                        }
                        items_df = pd.concat([items_df, pd.DataFrame([new_item])], ignore_index=True)

                    
                    save_csv(items_df, ITEMS_FILE)
                    
                    # Update stock and record movements
                    for item in bill_items:
                        prod_idx = products[products['name'] == item['name']].index
                        if not prod_idx.empty:
                            product_id = products.loc[prod_idx[0], 'id']
                            current_stock = products.loc[prod_idx[0], 'stock']
                            new_stock = max(0, current_stock - item['qty'])
                            products.loc[prod_idx[0], 'stock'] = new_stock
                            
                            # Record stock movement
                            stock_movements_df = record_stock_movement(
                                stock_movements_df, 
                                product_id, 
                                item.get('batch_no', 'N/A'), 
                                "OUT", 
                                item['qty'], 
                                bill_no, 
                                f"Sale to {customer['name']}"
                            )
                            
                            # Update batch quantity if batch was selected
                            if item.get('batch_no'):
                                batch_idx = batches_df[
                                    (batches_df.product_id == product_id) & 
                                    (batches_df.batch_no == item['batch_no'])
                                ].index
                                if not batch_idx.empty:
                                    current_batch_qty = batches_df.loc[batch_idx[0], 'quantity']
                                    batches_df.loc[batch_idx[0], 'quantity'] = max(0, current_batch_qty - item['qty'])
                    
                    save_csv(products, PRODUCTS_FILE)
                    save_csv(batches_df, BATCHES_FILE)
                    save_csv(stock_movements_df, STOCK_MOVEMENTS_FILE)
                    
                    # Generate PDF
                    customer_name = customers[customers.id == cust_id].iloc[0]['name']
                    folder_path = get_month_year_folder(bill_date, customer_name)
                    os.makedirs(folder_path, exist_ok=True)
                    
                    pdf_filename = f"{folder_path}/{bill_no.replace('/', '_')}.pdf"
                    
                    company_dict = {
                        'name': str(company_df.loc[0]['name']),
                        'gstin': str(company_df.loc[0]['gstin']),
                        'msme': str(company_df.loc[0].get('msme', '')),
                        'fssai': str(company_df.loc[0].get('fssai', '')),
                        'phone': str(company_df.loc[0].get('phone', '')),
                        'address': str(company_df.loc[0]['address']),
                        'logo': logo_path
                    }
                    
                    invoice_dict = {
                        'number': bill_no,
                        'date': str(bill_date),
                        'terms': terms
                    }
                    
                    generate_invoice_pdf(
                        company_dict, customer, invoice_dict, bill_items,
                        upi_id, pdf_filename, tax_type, payment_status
                    )
                    
                    # Download button
                    with open(pdf_filename, "rb") as f:
                        pdf_data = f.read()
                    
                    st.download_button(
                        label="📥 Download Invoice PDF",
                        data=pdf_data,
                        file_name=f"{bill_no.replace('/', '_')}.pdf",
                        mime="application/pdf",
                        key="download_pdf_btn"
                    )
                    
                    st.session_state.bill_created = True
                    st.rerun()
        else:
            st.info("Add products to generate invoice")
    
    return customers, products, bills, items_df, company_df, batches_df, stock_movements_df

# VIEW BILL TAB - WITH PDF VIEWER
def view_bill_tab(bills, items_df, customers):
    st.header("👁️ View Invoice")
    
    if bills.empty:
        st.info("No bills available to view.")
        return
    
    selected_bill_no = st.selectbox(
        "Select Invoice to View",
        bills['bill_no'].tolist(),
        key="view_bill_select"
    )
    
    if selected_bill_no:
        bill_data = bills[bills.bill_no == selected_bill_no].iloc[0]
        bill_items_data = items_df[items_df.bill_no == selected_bill_no]
        customer_info = customers[customers.id == bill_data['customer_id']].iloc[0]
        
        st.subheader(f"Invoice: {selected_bill_no}")
        
        # Display bill details
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Customer", customer_info['name'])
        with col2:
            st.metric("Date", bill_data['bill_date'])
        with col3:
            st.metric("Total", f"₹{bill_data['grand_total']:.2f}")
        with col4:
            payment_badge = "🟢 Paid" if bill_data['payment_status'] == "Paid" else "🔴 Pending" if bill_data['payment_status'] == "Pending" else "🟠 Partially Paid"
            st.metric("Status", payment_badge)
        
        st.divider()
        
        # Bill summary
        st.subheader("Bill Summary")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.write(f"**Subtotal:** ₹{bill_data['subtotal']:.2f}")
        with col2:
            if bill_data['cgst'] > 0 or bill_data['sgst'] > 0:
                st.write(f"**CGST + SGST:** ₹{(bill_data['cgst'] + bill_data['sgst']):.2f}")
            elif bill_data['igst'] > 0:
                st.write(f"**IGST:** ₹{bill_data['igst']:.2f}")
            else:
                st.write(f"**Tax:** ₹0.00")
        with col3:
            st.write(f"**Grand Total:** ₹{bill_data['grand_total']:.2f}")
        
        st.divider()
        
        # Bill items
        st.subheader("Items")
        st.dataframe(bill_items_data, width='stretch')
        
        st.divider()
        
        # PDF Viewer
        customer_name = customer_info['name']
        folder_path = get_month_year_folder(bill_data['bill_date'], customer_name)
        pdf_path = f"{folder_path}/{selected_bill_no.replace('/', '_')}.pdf"
        
        if os.path.exists(pdf_path):
            st.subheader("📄 Invoice PDF Preview")
            show_pdf(pdf_path)
            
            st.divider()
            
            # Download button
            with open(pdf_path, "rb") as f:
                pdf_data = f.read()
            
            st.download_button(
                label="📥 Download Invoice PDF",
                data=pdf_data,
                file_name=f"{selected_bill_no.replace('/', '_')}.pdf",
                mime="application/pdf",
                key="view_download_pdf"
            )
        else:
            st.warning("PDF file not found in customer folder.")

# EDIT BILL TAB - FULLY EDITABLE
# Replace the edit_bill_tab function in ui_billing.py with this corrected version:

def edit_bill_tab(bills, items_df, customers, products, company_df, batches_df, stock_movements_df, logo_path, upi_id):
    st.header("✏️ Edit Invoice")
    
    if bills.empty:
        st.info("No bills available to edit.")
        return bills, items_df, products, batches_df, stock_movements_df
    
    selected_bill_no = st.selectbox(
        "Select Invoice to Edit",
        bills['bill_no'].tolist(),
        key="edit_bill_select"
    )
    
    if selected_bill_no:
        bill_data = bills[bills.bill_no == selected_bill_no].iloc[0]
        bill_items_data = items_df[items_df.bill_no == selected_bill_no].copy()
        customer_info = customers[customers.id == bill_data['customer_id']].iloc[0]
        
        st.subheader(f"Editing Invoice: {selected_bill_no}")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write(f"**Customer:** {customer_info['name']}")
            st.write(f"**Date:** {bill_data['bill_date']}")
        
        with col2:
            st.write(f"**Current Total:** ₹{bill_data['grand_total']:.2f}")
            new_payment_status = st.selectbox(
                "Payment Status",
                ["Pending", "Paid", "Partially Paid"],
                index=["Pending", "Paid", "Partially Paid"].index(bill_data['payment_status']),
                key="edit_payment_status"
            )
        
        st.divider()
        st.subheader("Edit Bill Items")
        st.info("💡 You can edit quantities, prices, discounts, and batch numbers below. Add/remove rows as needed.")
        
        # Ensure batch_no column exists
        if 'batch_no' not in bill_items_data.columns:
            bill_items_data['batch_no'] = ''
        
        # FIXED: Convert mfg, exp, batch_no to string to avoid float/text type conflicts
        bill_items_data['mfg'] = bill_items_data['mfg'].fillna('').astype(str)
        bill_items_data['exp'] = bill_items_data['exp'].fillna('').astype(str)
        bill_items_data['batch_no'] = bill_items_data['batch_no'].fillna('').astype(str)
        bill_items_data['product'] = bill_items_data['product'].fillna('').astype(str)
        
        # Convert numeric columns to proper types
        bill_items_data['qty'] = pd.to_numeric(bill_items_data['qty'], errors='coerce').fillna(0)
        bill_items_data['price'] = pd.to_numeric(bill_items_data['price'], errors='coerce').fillna(0.0)
        bill_items_data['gst'] = pd.to_numeric(bill_items_data['gst'], errors='coerce').fillna(0.0)
        bill_items_data['free'] = pd.to_numeric(bill_items_data['free'], errors='coerce').fillna(0)
        bill_items_data['discount'] = pd.to_numeric(bill_items_data['discount'], errors='coerce').fillna(0.0)
        
        # EDITABLE DATAFRAME using st.data_editor
        edited_items = st.data_editor(
            bill_items_data,
            width='stretch',
            num_rows="dynamic",  # Allow adding/removing rows
            key="edit_items_data_editor",
            column_config={
                "bill_no": st.column_config.TextColumn("Bill No", disabled=True),
                "product": st.column_config.TextColumn("Product", required=True),
                "batch_no": st.column_config.TextColumn("Batch No"),
                "qty": st.column_config.NumberColumn("Quantity", min_value=0, required=True),
                "price": st.column_config.NumberColumn("Price", min_value=0.0, format="%.2f", required=True),
                "gst": st.column_config.NumberColumn("GST %", min_value=0.0, max_value=100.0, format="%.2f"),
                "free": st.column_config.NumberColumn("Free Qty", min_value=0),
                "discount": st.column_config.NumberColumn("Discount %", min_value=0.0, max_value=100.0, format="%.2f"),
                "mfg": st.column_config.TextColumn("MFG"),
                "exp": st.column_config.TextColumn("EXP"),
            },
            hide_index=True
        )
        
        st.divider()
        
        # Preview recalculated totals
        st.subheader("Updated Totals Preview")
        
        preview_subtotal = 0
        preview_cgst = 0
        preview_sgst = 0
        preview_igst = 0
        preview_grand_total = 0
        
        for _, item in edited_items.iterrows():
            qty = float(item.get('qty', 0))
            price = float(item.get('price', 0))
            discount = float(item.get('discount', 0))
            gst_rate = float(item.get('gst', 0))
            
            subtotal = qty * price
            disc_amount = subtotal * discount / 100
            taxable = subtotal - disc_amount
            
            # Detect tax type from original bill
            if bill_data['igst'] > 0:
                igst_amt = (taxable * gst_rate) / 100
                cgst_amt = 0
                sgst_amt = 0
                total = taxable + igst_amt
            elif bill_data['cgst'] > 0 or bill_data['sgst'] > 0:
                cgst_amt = (taxable * gst_rate) / 200
                sgst_amt = (taxable * gst_rate) / 200
                igst_amt = 0
                total = taxable + cgst_amt + sgst_amt
            else:
                cgst_amt = sgst_amt = igst_amt = 0
                total = taxable
            
            preview_subtotal += taxable
            preview_cgst += cgst_amt
            preview_sgst += sgst_amt
            preview_igst += igst_amt
            preview_grand_total += total
        
        col_p1, col_p2, col_p3 = st.columns(3)
        with col_p1:
            st.metric("New Subtotal", f"₹{preview_subtotal:.2f}", delta=f"₹{preview_subtotal - bill_data['subtotal']:.2f}")
        with col_p2:
            if preview_igst > 0:
                st.metric("New IGST", f"₹{preview_igst:.2f}")
            else:
                st.metric("New CGST+SGST", f"₹{(preview_cgst + preview_sgst):.2f}")
        with col_p3:
            st.metric("New Grand Total", f"₹{preview_grand_total:.2f}", delta=f"₹{preview_grand_total - bill_data['grand_total']:.2f}")
        
        st.divider()
        
        col_btn1, col_btn2, col_btn3 = st.columns(3)
        
        with col_btn1:
            if st.button("💾 Save Changes & Regenerate PDF", key="save_edit_bill_btn", type="primary"):
                # Calculate new totals
                new_subtotal = 0
                new_cgst = 0
                new_sgst = 0
                new_igst = 0
                new_grand_total = 0
                
                updated_items = []
                
                for _, item in edited_items.iterrows():
                    qty = float(item.get('qty', 0))
                    price = float(item.get('price', 0))
                    discount = float(item.get('discount', 0))
                    gst_rate = float(item.get('gst', 0))
                    
                    subtotal = qty * price
                    disc_amount = subtotal * discount / 100
                    taxable = subtotal - disc_amount
                    
                    # Detect tax type from original bill
                    if bill_data['igst'] > 0:
                        igst_amt = (taxable * gst_rate) / 100
                        cgst_amt = 0
                        sgst_amt = 0
                        total = taxable + igst_amt
                    elif bill_data['cgst'] > 0 or bill_data['sgst'] > 0:
                        cgst_amt = (taxable * gst_rate) / 200
                        sgst_amt = (taxable * gst_rate) / 200
                        igst_amt = 0
                        total = taxable + cgst_amt + sgst_amt
                    else:
                        cgst_amt = sgst_amt = igst_amt = 0
                        total = taxable
                    
                    new_subtotal += taxable
                    new_cgst += cgst_amt
                    new_sgst += sgst_amt
                    new_igst += igst_amt
                    new_grand_total += total
                    
                    updated_items.append({
                        'name': str(item.get('product', '')),
                        'product': str(item.get('product', '')),
                        'batch_no': str(item.get('batch_no', '')),
                        'qty': qty,
                        'rate': price,
                        'price': price,
                        'gst': gst_rate,
                        'free': int(item.get('free', 0)),
                        'discount': discount,
                        'mfg': str(item.get('mfg', '')),
                        'exp': str(item.get('exp', '')),
                        'taxable': taxable,
                        'cgst': cgst_amt,
                        'sgst': sgst_amt,
                        'igst': igst_amt,
                        'total': total
                    })
                
                # Update bills table
                bills.loc[bills.bill_no == selected_bill_no, 'subtotal'] = new_subtotal
                bills.loc[bills.bill_no == selected_bill_no, 'cgst'] = new_cgst
                bills.loc[bills.bill_no == selected_bill_no, 'sgst'] = new_sgst
                bills.loc[bills.bill_no == selected_bill_no, 'igst'] = new_igst
                bills.loc[bills.bill_no == selected_bill_no, 'grand_total'] = new_grand_total
                bills.loc[bills.bill_no == selected_bill_no, 'payment_status'] = new_payment_status
                
                save_csv(bills, BILLS_FILE)
                
                # Update items
                items_df = items_df[items_df.bill_no != selected_bill_no]  # Remove old items
                
                for item in updated_items:
                    new_item = {
                        'bill_no': selected_bill_no,
                        'product': item['name'],
                        'qty': item['qty'],
                        'price': item['price'],
                        'gst': item['gst'],
                        'mfg': item['mfg'],
                        'exp': item['exp'],
                        'free': item['free'],
                        'discount': item['discount'],
                        'batch_no': item['batch_no']
                    }
                    items_df = pd.concat([items_df, pd.DataFrame([new_item])], ignore_index=True)

                save_csv(items_df, ITEMS_FILE)
                
                # Regenerate PDF
                customer_dict = customer_info.to_dict()
                customer_name = customer_dict['name']
                folder_path = get_month_year_folder(bill_data['bill_date'], customer_name)
                pdf_path = f"{folder_path}/{selected_bill_no.replace('/', '_')}.pdf"
                
                # Detect tax type
                tax_type = "GST"
                if new_igst > 0:
                    tax_type = "IGST"
                elif new_cgst == 0 and new_sgst == 0:
                    tax_type = "NO_TAX"
                
                company_dict = {
                    'name': str(company_df.loc[0]['name']),
                    'gstin': str(company_df.loc[0]['gstin']),
                    'msme': str(company_df.loc[0].get('msme', '')),
                    'fssai': str(company_df.loc[0].get('fssai', '')),
                    'phone': str(company_df.loc[0].get('phone', '')),
                    'address': str(company_df.loc[0]['address']),
                    'logo': logo_path
                }
                
                invoice_dict = {
                    'number': selected_bill_no,
                    'date': str(bill_data['bill_date']),
                    'terms': "Goods once sold will not be taken back. E. & O.E."
                }
                
                generate_invoice_pdf(
                    company_dict, customer_dict, invoice_dict, updated_items,
                    upi_id, pdf_path, tax_type, new_payment_status
                )
                
                st.success("✅ Bill updated and PDF regenerated!")
                st.rerun()
        
        with col_btn2:
            if st.button("🔄 Recalculate Stock", key="recalc_stock_btn"):
                st.info("💡 Stock will be automatically adjusted based on the changes when you save.")
        
        with col_btn3:
            folder_path = get_month_year_folder(bill_data['bill_date'], customer_info['name'])
            pdf_path = f"{folder_path}/{selected_bill_no.replace('/', '_')}.pdf"
            
            if os.path.exists(pdf_path):
                with open(pdf_path, "rb") as f:
                    pdf_data = f.read()
                
                st.download_button(
                    label="📥 Download Current PDF",
                    data=pdf_data,
                    file_name=f"{selected_bill_no.replace('/', '_')}.pdf",
                    mime="application/pdf",
                    key="edit_download_pdf"
                )
    
    return bills, items_df, products, batches_df, stock_movements_df


