# pdf_utils.py
from fpdf import FPDF
import pandas as pd
import os
import qrcode
from num2words import num2words

def safe_str(val, default=""):
    if pd.isna(val) or val is None:
        return default
    return str(val)

def generate_invoice_pdf(
    company,
    customer,
    invoice,
    items,
    upi_id=None,
    file_path="invoice.pdf",
    tax_type="GST",
    payment_status="Pending"
):
    pdf = FPDF("P", "mm", "A4")
    pdf.add_page()
    pdf.set_auto_page_break(auto=False, margin=15)

    # Border
    pdf.set_line_width(1)
    pdf.rect(5, 5, 200, 287)
    pdf.set_line_width(0.5)
    pdf.line(10, 10, 200, 10)

    y_start = 14

    # Logo
    if company.get("logo") and os.path.exists(company["logo"]):
        pdf.image(company["logo"], x=12, y=y_start, w=28)

    # Company name
    pdf.set_xy(45, y_start)
    pdf.set_font("Arial", "B", 16)
    pdf.cell(90, 7, safe_str(company.get("name")), ln=False)

    # Invoice box
    pdf.set_xy(145, y_start)
    pdf.set_font("Arial", "B", 9)
    pdf.cell(55, 6, "ORIGINAL FOR RECIPIENT", border=1, align="C")

    # Address
    pdf.set_xy(45, y_start + 8)
    pdf.set_font("Arial", "", 9)
    pdf.multi_cell(90, 4, safe_str(company.get("address")))

    addr_end_y = pdf.get_y()
    pdf.set_xy(45, addr_end_y)
    pdf.set_font("Arial", "", 8)
    pdf.cell(90, 4, f"GSTIN : {safe_str(company.get('gstin'), 'N/A')}")
    pdf.set_xy(45, addr_end_y + 4)
    pdf.cell(90, 4, f"Phone : {safe_str(company.get('phone'), 'N/A')}")

    # MSME + FSSAI separate with space
    current_y = addr_end_y + 8
    if company.get("msme"):
        pdf.set_xy(45, current_y)
        pdf.cell(90, 4, f"MSME NO: {safe_str(company.get('msme'))}")
        current_y += 4
    if company.get("fssai"):
        pdf.set_xy(45, current_y)
        pdf.cell(90, 4, f"FSSAI LIC NO: {safe_str(company.get('fssai'))}")

    # Invoice info + payment status
    pdf.set_xy(145, y_start + 6)
    pdf.set_font("Arial", "", 8)
    pdf.cell(27, 5, "Invoice No.", border=1)
    pdf.cell(28, 5, safe_str(invoice["number"]), border=1)

    pdf.set_xy(145, y_start + 11)
    pdf.cell(27, 5, "Invoice Date", border=1)
    pdf.cell(28, 5, safe_str(invoice["date"]), border=1)

    pdf.set_xy(145, y_start + 16)
    pdf.cell(27, 5, "Status", border=1)
    pdf.cell(28, 5, safe_str(payment_status), border=1, align="C")

    pdf.ln(10)

    # Title
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 8, "TAX INVOICE", align="C", ln=True)
    pdf.set_line_width(0.3)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(3)

    # Bill / Ship
    bill_to_y = pdf.get_y()

    pdf.set_xy(10, bill_to_y)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(95, 5, "Bill To:", ln=True)
    pdf.set_xy(10, pdf.get_y())
    pdf.set_font("Arial", "B", 9)
    pdf.cell(95, 5, safe_str(customer.get("name")), ln=True)
    pdf.set_xy(10, pdf.get_y())
    pdf.set_font("Arial", "", 9)

    bill_addr_lines = safe_str(customer.get("address"), "N/A").split("\n")
    for line in bill_addr_lines[:3]:
        pdf.set_x(10)
        pdf.cell(95, 4, line, ln=True)

    bill_end_y = pdf.get_y()
    pdf.set_xy(10, bill_end_y)
    pdf.cell(95, 4, f"Phone: {safe_str(customer.get('phone'), 'N/A')}", ln=True)
    pdf.set_x(10)
    pdf.cell(95, 4, f"GSTIN: {safe_str(customer.get('gstin'), 'N/A')}", ln=True)
    pdf.set_x(10)
    pdf.cell(95, 4, f"Place of Supply: {safe_str(customer.get('place'), 'N/A')}", ln=True)

    # Ship to
    pdf.set_xy(105, bill_to_y)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(95, 5, "Ship To:", ln=True)
    pdf.set_xy(105, bill_to_y + 5)
    pdf.set_font("Arial", "B", 9)
    pdf.cell(95, 5, safe_str(customer.get("ship_name", customer.get("name"))), ln=True)
    pdf.set_xy(105, pdf.get_y())
    pdf.set_font("Arial", "", 9)

    ship_addr = safe_str(customer.get("ship_address", customer.get("address", "N/A")))
    ship_addr_lines = ship_addr.split("\n")
    for line in ship_addr_lines[:3]:
        pdf.set_x(105)
        pdf.cell(95, 4, line, ln=True)

    ship_end_y = pdf.get_y()
    pdf.set_xy(105, ship_end_y)
    pdf.cell(95, 4, f"Phone: {safe_str(customer.get('ship_phone', customer.get('phone')), 'N/A')}", ln=True)
    pdf.set_x(105)
    pdf.cell(95, 4, f"GSTIN: {safe_str(customer.get('ship_gstin', customer.get('gstin')), 'N/A')}", ln=True)

    pdf.set_y(max(pdf.get_y(), bill_end_y + 12))
    pdf.ln(3)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(2)

    # Table header shifted 2pts left
    pdf.set_font("Arial", "B", 8)
    if tax_type == "NO_TAX":
        col_widths = [10, 52, 20, 12, 12, 18, 14, 20, 22]
        headers = ["Sr", "Product", "HSN", "Qty", "Free", "Rate", "Disc%", "Taxable", "Amount"]
    elif tax_type == "IGST":
        col_widths = [10, 48, 18, 12, 12, 16, 12, 20, 18, 24]
        headers = ["Sr", "Product", "HSN", "Qty", "Free", "Rate", "Disc%", "Taxable", "IGST", "Total"]
    else:
        col_widths = [10, 45, 18, 12, 12, 15, 11, 19, 16, 16, 22]
        headers = ["Sr", "Product", "HSN", "Qty", "Free", "Rate", "Disc%", "Taxable", "CGST", "SGST", "Total"]

    pdf.set_fill_color(230, 230, 230)
    x_start = 8
    for h, w in zip(headers, col_widths):
        pdf.set_xy(x_start, pdf.get_y())
        pdf.cell(w, 6, h, border=1, align="C", fill=True)
        x_start += w
    pdf.ln()

    # Items
    pdf.set_font("Arial", "", 8)
    total_taxable = total_cgst = total_sgst = total_igst = grand_total = 0

    for idx, item in enumerate(items):
        x_pos = 8
        free_qty = item.get("free", 0)
        disc_pct = item.get("discount", 0)

        if tax_type == "NO_TAX":
            values = [
                str(idx + 1),
                safe_str(item["product"])[:24],
                safe_str(item.get("hsn", "")),
                str(item.get("qty", 0)),
                str(free_qty) if free_qty > 0 else "-",
                f"{item.get('price', 0):.2f}",
                f"{disc_pct:.1f}%" if disc_pct > 0 else "-",
                f"{item.get('taxable', 0):.2f}",
                f"{item.get('total', 0):.2f}",
            ]
        elif tax_type == "IGST":
            values = [
                str(idx + 1),
                safe_str(item["product"])[:20],
                safe_str(item.get("hsn", "")),
                str(item.get("qty", 0)),
                str(free_qty) if free_qty > 0 else "-",
                f"{item.get('price', 0):.2f}",
                f"{disc_pct:.1f}%" if disc_pct > 0 else "-",
                f"{item.get('taxable', 0):.2f}",
                f"{item.get('igst_amt', 0):.2f}",
                f"{item.get('total', 0):.2f}",
            ]
        else:
            values = [
                str(idx + 1),
                safe_str(item["product"])[:18],
                safe_str(item.get("hsn", "")),
                str(item.get("qty", 0)),
                str(free_qty) if free_qty > 0 else "-",
                f"{item.get('price', 0):.2f}",
                f"{disc_pct:.1f}%" if disc_pct > 0 else "-",
                f"{item.get('taxable', 0):.2f}",
                f"{item.get('cgst_amt', 0):.2f}",
                f"{item.get('sgst_amt', 0):.2f}",
                f"{item.get('total', 0):.2f}",
            ]

        for val, w in zip(values, col_widths):
            pdf.set_xy(x_pos, pdf.get_y())
            pdf.cell(w, 6, val, border=1, align="C" if w in (10, 12) else "R" if w in (18, 20, 22, 24, 16, 15, 11, 19) else "L")
            x_pos += w
        pdf.ln()

        total_taxable += float(item.get("taxable", 0))
        total_cgst += float(item.get("cgst_amt", 0))
        total_sgst += float(item.get("sgst_amt", 0))
        total_igst += float(item.get("igst_amt", 0))
        grand_total += float(item.get("total", 0))

    pdf.ln(2)

    # Totals
    pdf.set_font("Arial", "B", 9)
    x_pos = 8
    if tax_type == "NO_TAX":
        total_width = sum(col_widths[:7])
        pdf.set_xy(x_pos, pdf.get_y())
        pdf.cell(total_width, 7, "Total", border=1, align="C")
        x_pos += total_width
        pdf.cell(col_widths[7], 7, f"{total_taxable:.2f}", border=1, align="R")
        pdf.cell(col_widths[8], 7, f"{grand_total:.2f}", border=1, align="R")
    elif tax_type == "IGST":
        total_width = sum(col_widths[:7])
        pdf.set_xy(x_pos, pdf.get_y())
        pdf.cell(total_width, 7, "Total", border=1, align="C")
        x_pos += total_width
        pdf.cell(col_widths[7], 7, f"{total_taxable:.2f}", border=1, align="R")
        pdf.cell(col_widths[8], 7, f"{total_igst:.2f}", border=1, align="R")
        pdf.cell(col_widths[9], 7, f"{grand_total:.2f}", border=1, align="R")
    else:
        total_width = sum(col_widths[:7])
        pdf.set_xy(x_pos, pdf.get_y())
        pdf.cell(total_width, 7, "Total", border=1, align="C")
        x_pos += total_width
        pdf.cell(col_widths[7], 7, f"{total_taxable:.2f}", border=1, align="R")
        pdf.cell(col_widths[8], 7, f"{total_cgst:.2f}", border=1, align="R")
        pdf.cell(col_widths[9], 7, f"{total_sgst:.2f}", border=1, align="R")
        pdf.cell(col_widths[10], 7, f"{grand_total:.2f}", border=1, align="R")

    pdf.ln(8)

    # Total in words
    pdf.set_font("Arial", "B", 10)
    pdf.cell(130, 6, "Total Amount (In Figures):", border=0)
    pdf.cell(60, 6, f"Rs. {grand_total:.2f}", border=1, align="R", ln=True)

    pdf.ln(2)
    pdf.set_font("Arial", "B", 9)
    try:
        amount_words = num2words(int(round(grand_total)), lang="en_IN").upper()
    except:
        amount_words = num2words(int(round(grand_total))).upper()
    pdf.multi_cell(0, 5, f"Total in words: {amount_words} RUPEES ONLY")

    pdf.ln(2)

    # Terms
    pdf.set_font("Arial", "B", 9)
    pdf.cell(0, 5, "Terms and Conditions:", ln=True)
    pdf.set_font("Arial", "", 8)
    pdf.multi_cell(0, 4, safe_str(invoice.get("terms", "Goods once sold will not be taken back. E. & O.E.")))

    pdf.ln(5)

    footer_y = pdf.get_y()

    # QR
    if upi_id:
        qr_file = "assets/upi_qr.png"
        qr = qrcode.QRCode(version=1, box_size=10, border=2)
        qr.add_data(f"upi://pay?pa={upi_id}&pn={safe_str(company['name'])}&cu=INR")
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        img.save(qr_file)
        pdf.image(qr_file, x=15, y=footer_y, w=30)
        pdf.set_xy(15, footer_y + 32)
        pdf.set_font("Arial", "", 8)
        pdf.cell(30, 3, "Pay using UPI", align="C")

    # Signature
    pdf.set_xy(140, footer_y)
    pdf.set_font("Arial", "B", 9)
    pdf.cell(60, 5, f"For {safe_str(company['name'])}", ln=True, align="R")
    pdf.ln(15)
    pdf.set_xy(140, pdf.get_y())
    pdf.set_font("Arial", "", 8)
    pdf.cell(60, 5, "Authorized Signatory", align="R", ln=True)

    pdf.output(file_path)
    return file_path
