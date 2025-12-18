# ui_stock.py
import streamlit as st
import pandas as pd
from datetime import date
from data_utils import record_stock_movement

def stock_management_tab(products, batches_df, stock_movements_df):
    st.header("📦 Stock & Batch Management")
    
    stock_tabs = st.tabs(["Stock Overview", "Batch Management", "Stock Adjustments", "Stock Movements"])
    
    # STOCK OVERVIEW
    with stock_tabs[0]:
        st.subheader("Current Stock Levels")
        
        if products.empty:
            st.info("No products available.")
        else:
            if not batches_df.empty:
                batch_stock = batches_df.groupby('product_id')['quantity'].sum().reset_index()
                products_display = products.merge(batch_stock, left_on='id', right_on='product_id', how='left', suffixes=('', '_batch'))
                products_display['stock'] = products_display['quantity'].fillna(0)
            else:
                products_display = products.copy()
            
            products_display['status'] = products_display['stock'].apply(
                lambda x: '🔴 Low' if x < 10 else '🟡 Medium' if x < 50 else '🟢 Good'
            )
            
            display_cols = ['name', 'hsn', 'stock', 'price', 'status']
            st.dataframe(products_display[display_cols], width='stretch')
            
            low_stock = products_display[products_display['stock'] < 10]
            if not low_stock.empty:
                st.warning(f"⚠️ {len(low_stock)} products are low in stock!")
                with st.expander("View Low Stock Items"):
                    st.dataframe(low_stock[['name', 'stock']], width='stretch')
    
    # BATCH MANAGEMENT
    with stock_tabs[1]:
        st.subheader("Manage Product Batches")
        
        with st.expander("➕ Add New Batch", expanded=False):
            if products.empty:
                st.warning("Please add products first.")
            else:
                col1, col2 = st.columns(2)
                
                with col1:
                    product_id = st.selectbox(
                        "Select Product",
                        products['id'].tolist(),
                        format_func=lambda x: products[products.id == x].iloc[0]['name'],
                        key="batch_product_select"
                    )
                    batch_no = st.text_input("Batch Number", key="batch_no_input")
                    mfg_date = st.date_input("Manufacturing Date", date.today(), key="batch_mfg")
                
                with col2:
                    exp_date = st.date_input("Expiry Date", date.today(), key="batch_exp")
                    quantity = st.number_input("Quantity", min_value=0, value=0, key="batch_qty")
                    price = st.number_input("Purchase Price", min_value=0.0, step=0.01, key="batch_price")
                
                if st.button("Add Batch", key="add_batch_btn"):
                    if batch_no and quantity > 0:
                        new_batch_id = 1 if batches_df.empty else int(batches_df['id'].max()) + 1
                        
                        new_batch = {
                            'id': new_batch_id,
                            'product_id': product_id,
                            'batch_no': batch_no,
                            'mfg_date': str(mfg_date),
                            'exp_date': str(exp_date),
                            'quantity': quantity,
                            'price': price
                        }
                        
                        batches_df = pd.concat([batches_df, pd.DataFrame([new_batch])], ignore_index=True)
                        
                        products.loc[products.id == product_id, 'stock'] = products.loc[products.id == product_id, 'stock'] + quantity
                        
                        stock_movements_df = record_stock_movement(
                            stock_movements_df, product_id, batch_no, "IN", quantity, 
                            f"Batch {batch_no}", "New batch added"
                        )
                        
                        st.success(f"✅ Batch {batch_no} added successfully!")
                        st.rerun()
                    else:
                        st.error("Please enter batch number and quantity.")
        
        st.subheader("All Batches")
        if batches_df.empty:
            st.info("No batches available.")
        else:
            batches_display = batches_df.merge(
                products[['id', 'name']], 
                left_on='product_id', 
                right_on='id', 
                how='left'
            )
            
            display_cols = ['name', 'batch_no', 'mfg_date', 'exp_date', 'quantity', 'price']
            st.dataframe(batches_display[display_cols], width='stretch')
    
    # STOCK ADJUSTMENTS
    with stock_tabs[2]:
        st.subheader("Manual Stock Adjustments")
        
        if products.empty:
            st.info("No products available.")
        else:
            col1, col2 = st.columns(2)
            
            with col1:
                adjust_product_id = st.selectbox(
                    "Select Product to Adjust",
                    products['id'].tolist(),
                    format_func=lambda x: f"{products[products.id == x].iloc[0]['name']} (Current: {products[products.id == x].iloc[0]['stock']})",
                    key="adjust_product_select"
                )
            
            with col2:
                adjustment_type = st.radio(
                    "Adjustment Type",
                    ["Add Stock", "Remove Stock", "Set Stock"],
                    key="adjustment_type_radio"
                )
            
            col3, col4 = st.columns(2)
            
            with col3:
                if adjustment_type == "Set Stock":
                    new_stock = st.number_input("Set Stock To", min_value=0, value=0, key="new_stock_input")
                else:
                    adjustment_qty = st.number_input("Quantity", min_value=0, value=0, key="adjustment_qty_input")
            
            with col4:
                adjustment_reason = st.text_area("Reason/Notes", key="adjustment_reason")
            
            if st.button("Apply Adjustment", key="apply_adjustment_btn", type="primary"):
                current_stock = products[products.id == adjust_product_id].iloc[0]['stock']
                
                if adjustment_type == "Add Stock":
                    products.loc[products.id == adjust_product_id, 'stock'] = current_stock + adjustment_qty
                    movement_type = "ADJUST_IN"
                    qty_change = adjustment_qty
                elif adjustment_type == "Remove Stock":
                    products.loc[products.id == adjust_product_id, 'stock'] = max(0, current_stock - adjustment_qty)
                    movement_type = "ADJUST_OUT"
                    qty_change = -adjustment_qty
                else:
                    products.loc[products.id == adjust_product_id, 'stock'] = new_stock
                    movement_type = "ADJUST_SET"
                    qty_change = new_stock - current_stock
                
                stock_movements_df = record_stock_movement(
                    stock_movements_df, adjust_product_id, "MANUAL", movement_type, 
                    qty_change, "Manual Adjustment", adjustment_reason
                )
                
                st.success("✅ Stock adjusted successfully!")
                st.rerun()
    
    # STOCK MOVEMENTS
    with stock_tabs[3]:
        st.subheader("Stock Movement History")
        
        if stock_movements_df.empty:
            st.info("No stock movements recorded yet.")
        else:
            movements_display = stock_movements_df.merge(
                products[['id', 'name']], 
                left_on='product_id', 
                right_on='id', 
                how='left'
            )
            
            movements_display = movements_display.sort_values('date', ascending=False)
            
            col1, col2 = st.columns(2)
            
            with col1:
                filter_type = st.selectbox(
                    "Filter by Type",
                    ["All", "IN", "OUT", "ADJUST_IN", "ADJUST_OUT", "ADJUST_SET"],
                    key="movement_filter_type"
                )
            
            with col2:
                filter_product = st.selectbox(
                    "Filter by Product",
                    ["All"] + products['name'].tolist(),
                    key="movement_filter_product"
                )
            
            filtered_movements = movements_display.copy()
            
            if filter_type != "All":
                filtered_movements = filtered_movements[filtered_movements['movement_type'] == filter_type]
            
            if filter_product != "All":
                prod_id = products[products.name == filter_product].iloc[0]['id']
                filtered_movements = filtered_movements[filtered_movements['product_id'] == prod_id]
            
            display_cols = ['date', 'name', 'batch_no', 'movement_type', 'quantity', 'reference', 'notes']
            st.dataframe(filtered_movements[display_cols], width='stretch')
            
            csv = filtered_movements.to_csv(index=False)
            st.download_button(
                label="📥 Export Movement History",
                data=csv,
                file_name=f"stock_movements_{date.today()}.csv",
                mime="text/csv",
                key="export_movements_btn"
            )
    
    return products, batches_df, stock_movements_df
