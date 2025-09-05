import io
import base64
from fpdf import FPDF
from datetime import datetime


def generate_receipt_pdf(order_data, delivery):
    """
    Generate PDF receipt using PyFPDF (FPDF2)
    Returns base64 encoded string for Celery compatibility
    """
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    # Company Info
    pdf.set_font("Arial", "B", 16)
    pdf.cell(200, 10, txt="RECEIPT", ln=True, align="C")
    pdf.set_font("Arial", "B", 12)
    pdf.cell(200, 10, txt="Movbay", ln=True, align="C")
    pdf.set_font("Arial", size=10)
    pdf.cell(200, 10, txt="Your Trusted Delivery Partner", ln=True, align="C")
    pdf.ln(10)

    # Order Details
    pdf.set_font("Arial", "B", 12)
    pdf.cell(200, 10, txt="Order Details", ln=True, align="L")
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())  # Add line
    pdf.ln(5)

    pdf.set_font("Arial", size=11)
    pdf.cell(100, 8, f"Seller: {order_data.store.owner.username}", ln=True)
    pdf.cell(100, 8, f"Buyer: {order_data.buyer.username}", ln=True)
    
    # Handle parcel_id safely
    parcel_id = getattr(delivery, 'parcel_id', 'N/A') or 'N/A'
    pdf.cell(100, 8, f"Parcel ID: {parcel_id}", ln=True)
    
    # Format date properly
    order_date = order_data.created_at.strftime("%Y-%m-%d %H:%M") if hasattr(order_data.created_at, 'strftime') else str(order_data.created_at)
    pdf.cell(100, 8, f"Order Date: {order_date}", ln=True)
    pdf.cell(100, 8, f"Order No: {order_data.order_id}", ln=True)
    
    # Handle delivery method
    delivery_method = getattr(delivery, 'delivery_method', 'Standard')
    pdf.cell(100, 8, f"Delivery Method: {delivery_method.replace('_', ' ').title()}", ln=True)
    
    pdf.ln(3)
    pdf.multi_cell(0, 8, f"Delivery Address: {delivery.delivery_address}")
    pdf.cell(100, 8, f"Buyer Phone: {delivery.phone_number}", ln=True)

    pdf.ln(10)

    # Items Summary (if available)
    if hasattr(order_data, 'items') and order_data.items.exists():
        pdf.set_font("Arial", "B", 12)
        pdf.cell(200, 10, txt="Items", ln=True, align="L")
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(5)
        
        pdf.set_font("Arial", size=10)
        # Table header
        pdf.cell(80, 8, "Product", border=1, align="C")
        pdf.cell(30, 8, "Quantity", border=1, align="C")
        pdf.cell(40, 8, "Amount", border=1, align="C")
        pdf.cell(40, 8, "Total", border=1, align="C")
        pdf.ln()
        
        total_amount = 0
        for item in order_data.items.all():
            product_name = getattr(item.product, 'name', f'Product ID: {item.product}')[:30]  # Truncate long names
            item_total = item.amount * item.quantity
            total_amount += item_total
            
            pdf.cell(80, 8, product_name, border=1)
            pdf.cell(30, 8, str(item.quantity), border=1, align="C")
            pdf.cell(40, 8, f"₦{item.amount:,.2f}", border=1, align="R")
            pdf.cell(40, 8, f"₦{item_total:,.2f}", border=1, align="R")
            pdf.ln()
        
        # Total row
        pdf.set_font("Arial", "B", 10)
        pdf.cell(110, 8, "", border=0)
        pdf.cell(40, 8, "Grand Total:", border=1, align="C")
        pdf.cell(40, 8, f"₦{total_amount:,.2f}", border=1, align="R")
        pdf.ln(10)

    # Support Info
    pdf.set_font("Arial", "B", 12)
    pdf.cell(200, 10, txt="Support & Contact", ln=True, align="L")
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(5)

    pdf.set_font("Arial", size=11)
    pdf.cell(100, 8, f"Email: support@movbay.com", ln=True)
    pdf.cell(100, 8, f"Phone: +234 (0) 809 442 2807", ln=True)
    pdf.cell(100, 8, f"Website: www.movbay.com", ln=True)
    pdf.multi_cell(0, 8, "Address: Port Harcourt, Rivers State, Nigeria")

    # Footer
    pdf.ln(10)
    pdf.set_font("Arial", "I", 9)
    pdf.cell(200, 8, f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True, align="C")
    pdf.cell(200, 8, "Thank you for choosing Movbay!", ln=True, align="C")

    # Get PDF bytes and encode as base64 for Celery compatibility
    try:
        # Try the newer FPDF2 way first
        pdf_bytes = pdf.output()
        if isinstance(pdf_bytes, (bytes, bytearray)):
            pdf_binary = bytes(pdf_bytes)
        else:
            # Fallback for older versions that return strings
            pdf_binary = pdf_bytes.encode("latin-1")
    except TypeError:
        # Alternative approach for different FPDF versions
        pdf_output = io.BytesIO()
        pdf_content = pdf.output(dest="S")
        
        # Handle different return types
        if isinstance(pdf_content, (bytes, bytearray)):
            pdf_output.write(pdf_content)
        else:
            pdf_output.write(pdf_content.encode("latin-1"))
        
        pdf_output.seek(0)
        pdf_binary = pdf_output.getvalue()
    
    # Convert to base64 string for JSON serialization
    pdf_base64 = base64.b64encode(pdf_binary).decode('utf-8')
    return pdf_base64