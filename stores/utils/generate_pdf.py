import io
import base64
import logging
from fpdf import FPDF
from datetime import datetime

# Set up logging for debugging
logger = logging.getLogger(__name__)

def generate_receipt_pdf(order_data, delivery):
    """
    Generate PDF receipt using PyFPDF (FPDF2)
    Returns base64 encoded string for Celery compatibility
    Production-ready version with error handling and logging
    """
    try:
        logger.info(f"Starting PDF generation for order: {getattr(order_data, 'order_id', 'Unknown')}")
        
        # Initialize PDF with explicit parameters for production
        pdf = FPDF(orientation='P', unit='mm', format='A4')
        pdf.add_page()
        
        # Set default font (Arial should be available in most production environments)
        try:
            pdf.set_font("Arial", size=12)
        except RuntimeError as e:
            logger.warning(f"Arial font not available, using default: {e}")
            # Fallback to built-in fonts
            pdf.set_font("helvetica", size=12)

        # Company Info
        try:
            pdf.set_font("Arial", "B", 16)
        except RuntimeError:
            pdf.set_font("helvetica", "B", 16)
        
        pdf.cell(200, 10, txt="RECEIPT", ln=True, align="C")
        
        try:
            pdf.set_font("Arial", "B", 12)
        except RuntimeError:
            pdf.set_font("helvetica", "B", 12)
        
        pdf.cell(200, 10, txt="Movbay", ln=True, align="C")
        
        try:
            pdf.set_font("Arial", size=10)
        except RuntimeError:
            pdf.set_font("helvetica", size=10)
        
        pdf.cell(200, 10, txt="Your Trusted Delivery Partner", ln=True, align="C")
        pdf.ln(10)

        # Order Details
        try:
            pdf.set_font("Arial", "B", 12)
        except RuntimeError:
            pdf.set_font("helvetica", "B", 12)
        
        pdf.cell(200, 10, txt="Order Details", ln=True, align="L")
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())  # Add line
        pdf.ln(5)

        try:
            pdf.set_font("Arial", size=11)
        except RuntimeError:
            pdf.set_font("helvetica", size=11)

        # Safely get order data with error handling
        try:
            seller_name = getattr(getattr(order_data, 'store', None), 'owner', None)
            seller_name = getattr(seller_name, 'username', 'Unknown Seller') if seller_name else 'Unknown Seller'
            pdf.cell(100, 8, f"Seller: {seller_name}", ln=True)
        except Exception as e:
            logger.warning(f"Error getting seller name: {e}")
            pdf.cell(100, 8, "Seller: Unknown", ln=True)

        try:
            buyer_name = getattr(getattr(order_data, 'buyer', None), 'username', 'Unknown Buyer')
            pdf.cell(100, 8, f"Buyer: {buyer_name}", ln=True)
        except Exception as e:
            logger.warning(f"Error getting buyer name: {e}")
            pdf.cell(100, 8, "Buyer: Unknown", ln=True)
        
        # Handle parcel_id safely
        parcel_id = getattr(delivery, 'parcel_id', 'N/A') or 'N/A'
        pdf.cell(100, 8, f"Parcel ID: {parcel_id}", ln=True)
        
        # Format date properly with timezone handling
        try:
            if hasattr(order_data, 'created_at') and order_data.created_at:
                if hasattr(order_data.created_at, 'strftime'):
                    order_date = order_data.created_at.strftime("%Y-%m-%d %H:%M")
                else:
                    order_date = str(order_data.created_at)
            else:
                order_date = datetime.now().strftime("%Y-%m-%d %H:%M")
        except Exception as e:
            logger.warning(f"Error formatting date: {e}")
            order_date = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        pdf.cell(100, 8, f"Order Date: {order_date}", ln=True)
        
        # Order ID with safe access
        try:
            order_id = getattr(order_data, 'order_id', 'Unknown')
            pdf.cell(100, 8, f"Order No: {order_id}", ln=True)
        except Exception as e:
            logger.warning(f"Error getting order ID: {e}")
            pdf.cell(100, 8, "Order No: Unknown", ln=True)
        
        # Handle delivery method
        delivery_method = getattr(delivery, 'delivery_method', 'Standard')
        if delivery_method:
            delivery_method_display = delivery_method.replace('_', ' ').title()
        else:
            delivery_method_display = 'Standard'
        pdf.cell(100, 8, f"Delivery Method: {delivery_method_display}", ln=True)
        
        pdf.ln(3)
        
        # Delivery address with safe access
        try:
            delivery_address = getattr(delivery, 'delivery_address', 'Address not provided')
            pdf.multi_cell(0, 8, f"Delivery Address: {delivery_address}")
        except Exception as e:
            logger.warning(f"Error getting delivery address: {e}")
            pdf.multi_cell(0, 8, "Delivery Address: Not provided")
        
        try:
            phone_number = getattr(delivery, 'phone_number', 'Phone not provided')
            pdf.cell(100, 8, f"Buyer Phone: {phone_number}", ln=True)
        except Exception as e:
            logger.warning(f"Error getting phone number: {e}")
            pdf.cell(100, 8, "Buyer Phone: Not provided", ln=True)

        pdf.ln(10)

        # Items Summary with enhanced error handling
        try:
            if hasattr(order_data, 'items') and order_data.items.exists():
                try:
                    pdf.set_font("Arial", "B", 12)
                except RuntimeError:
                    pdf.set_font("helvetica", "B", 12)
                
                pdf.cell(200, 10, txt="Items", ln=True, align="L")
                pdf.line(10, pdf.get_y(), 200, pdf.get_y())
                pdf.ln(5)
                
                try:
                    pdf.set_font("Arial", size=10)
                except RuntimeError:
                    pdf.set_font("helvetica", size=10)
                
                # Table header
                pdf.cell(80, 8, "Product", border=1, align="C")
                pdf.cell(30, 8, "Quantity", border=1, align="C")
                pdf.cell(40, 8, "Amount", border=1, align="C")
                pdf.cell(40, 8, "Total", border=1, align="C")
                pdf.ln()
                
                total_amount = 0
                for item in order_data.items.all():
                    try:
                        # Safe product name extraction
                        if hasattr(item, 'product') and item.product:
                            if hasattr(item.product, 'name'):
                                product_name = str(item.product.name)[:30]
                            else:
                                product_name = f'Product ID: {getattr(item, "product", "Unknown")}'
                        else:
                            product_name = 'Unknown Product'
                        
                        # Safe numeric calculations
                        item_amount = float(getattr(item, 'amount', 0))
                        item_quantity = int(getattr(item, 'quantity', 1))
                        item_total = item_amount * item_quantity
                        total_amount += item_total
                        
                        pdf.cell(80, 8, product_name, border=1)
                        pdf.cell(30, 8, str(item_quantity), border=1, align="C")
                        pdf.cell(40, 8, f"₦{item_amount:,.2f}", border=1, align="R")
                        pdf.cell(40, 8, f"₦{item_total:,.2f}", border=1, align="R")
                        pdf.ln()
                        
                    except Exception as e:
                        logger.warning(f"Error processing item: {e}")
                        # Add a fallback row for problematic items
                        pdf.cell(80, 8, "Item Error", border=1)
                        pdf.cell(30, 8, "1", border=1, align="C")
                        pdf.cell(40, 8, "₦0.00", border=1, align="R")
                        pdf.cell(40, 8, "₦0.00", border=1, align="R")
                        pdf.ln()
                
                # Total row
                try:
                    pdf.set_font("Arial", "B", 10)
                except RuntimeError:
                    pdf.set_font("helvetica", "B", 10)
                
                pdf.cell(110, 8, "", border=0)
                pdf.cell(40, 8, "Grand Total:", border=1, align="C")
                pdf.cell(40, 8, f"₦{total_amount:,.2f}", border=1, align="R")
                pdf.ln(10)
        except Exception as e:
            logger.warning(f"Error processing items section: {e}")

        # Support Info
        try:
            pdf.set_font("Arial", "B", 12)
        except RuntimeError:
            pdf.set_font("helvetica", "B", 12)
        
        pdf.cell(200, 10, txt="Support & Contact", ln=True, align="L")
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(5)

        try:
            pdf.set_font("Arial", size=11)
        except RuntimeError:
            pdf.set_font("helvetica", size=11)
        
        pdf.cell(100, 8, "Email: support@movbay.com", ln=True)
        pdf.cell(100, 8, "Phone: +234 (0) 809 442 2807", ln=True)
        pdf.cell(100, 8, "Website: www.movbay.com", ln=True)
        pdf.multi_cell(0, 8, "Address: Port Harcourt, Rivers State, Nigeria")

        # Footer
        pdf.ln(10)
        try:
            pdf.set_font("Arial", "I", 9)
        except RuntimeError:
            pdf.set_font("helvetica", "I", 9)
        
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        pdf.cell(200, 8, f"Generated on: {current_time}", ln=True, align="C")
        pdf.cell(200, 8, "Thank you for choosing Movbay!", ln=True, align="C")

        # Enhanced PDF output handling for production
        logger.info("Generating PDF binary content...")
        
        try:
            # Method 1: Direct output (FPDF2 new version)
            pdf_content = pdf.output()
            if isinstance(pdf_content, (bytes, bytearray)):
                pdf_binary = bytes(pdf_content)
                logger.info("PDF generated using direct output method")
            else:
                # Handle string return (older versions)
                pdf_binary = pdf_content.encode("latin-1")
                logger.info("PDF generated using string encoding method")
        except Exception as e:
            logger.warning(f"Direct output failed: {e}, trying alternative method")
            
            try:
                # Method 2: BytesIO buffer approach
                pdf_buffer = io.BytesIO()
                pdf_content = pdf.output(dest="S")
                
                if isinstance(pdf_content, (bytes, bytearray)):
                    pdf_buffer.write(pdf_content)
                elif isinstance(pdf_content, str):
                    pdf_buffer.write(pdf_content.encode("latin-1"))
                else:
                    raise ValueError(f"Unexpected PDF content type: {type(pdf_content)}")
                
                pdf_buffer.seek(0)
                pdf_binary = pdf_buffer.getvalue()
                logger.info("PDF generated using BytesIO buffer method")
                
            except Exception as e2:
                logger.error(f"All PDF generation methods failed: {e2}")
                raise Exception(f"PDF generation failed: {e2}")
        
        # Convert to base64 with error handling
        try:
            pdf_base64 = base64.b64encode(pdf_binary).decode('utf-8')
            logger.info(f"PDF successfully converted to base64, size: {len(pdf_base64)} characters")
            return pdf_base64
            
        except Exception as e:
            logger.error(f"Base64 encoding failed: {e}")
            raise Exception(f"PDF base64 encoding failed: {e}")
            
    except Exception as e:
        logger.error(f"Critical error in PDF generation: {e}")
        # Return a minimal error PDF instead of failing completely
        return generate_error_pdf(str(e))


def generate_error_pdf(error_message):
    """
    Generate a simple error PDF when main PDF generation fails
    """
    try:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("helvetica", size=12)
        
        pdf.cell(200, 10, txt="PDF Generation Error", ln=True, align="C")
        pdf.ln(10)
        pdf.cell(200, 10, txt="An error occurred while generating your receipt.", ln=True, align="L")
        pdf.cell(200, 10, txt="Please contact support@movbay.com", ln=True, align="L")
        pdf.ln(10)
        pdf.cell(200, 10, txt=f"Error: {error_message[:100]}...", ln=True, align="L")
        
        pdf_content = pdf.output()
        if isinstance(pdf_content, (bytes, bytearray)):
            pdf_binary = bytes(pdf_content)
        else:
            pdf_binary = pdf_content.encode("latin-1")
            
        return base64.b64encode(pdf_binary).decode('utf-8')
        
    except Exception as e:
        logger.error(f"Even error PDF generation failed: {e}")
        return None


# Production debugging helper
def test_pdf_generation_environment():
    """
    Test function to check PDF generation capabilities in production
    """
    try:
        from fpdf import FPDF
        pdf = FPDF()
        pdf.add_page()
        
        # Test different fonts
        fonts_available = []
        for font in ['Arial', 'helvetica', 'Times', 'Courier']:
            try:
                pdf.set_font(font, size=12)
                fonts_available.append(font)
            except:
                pass
        
        logger.info(f"Available fonts in production: {fonts_available}")
        
        # Test basic PDF generation
        pdf.cell(200, 10, txt="Test PDF", ln=True, align="C")
        test_output = pdf.output()
        
        logger.info(f"PDF output type: {type(test_output)}")
        logger.info("PDF generation test successful in production")
        
        return True
        
    except Exception as e:
        logger.error(f"PDF generation test failed: {e}")
        return False