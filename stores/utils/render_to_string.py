from django.template.loader import render_to_string
def render_to_new_string(order_data, delivery):
   html_string = render_to_string('emails/receipt.html', {
        'company_name': 'Your Company Name',
        'seller_name': order_data.store.owner.username,
        'buyer_name': order_data.buyer.username,
        'order_id': delivery.order_id if order_data.delivery else 'N/A',
        "delivery_amount": delivery.shiiping_amount if order_data.delivery else 'N/A',
        'parcel_id': delivery.parcel_id,
        'delivery_rider_name': delivery.courier_name if order_data.delivery else 'N/A',
        'order_date': order_data.created_at.strftime('%Y-%m-%d'),
        'order_number': order_data.order_id,
        # 'estimated_delivery_date': order_data.delivery.estimated_delivery_date.strftime('%Y-%m-%d') if order_data.estimated_delivery_date else 'N/A',
        'delivery_address': delivery.delivery_address if order_data.delivery else 'N/A',
        'buyer_phone': order_data.buyer.phone_number,
        'support_email': 'support@movbay.com',
        'support_phone': '+1234567890',
        'your_website': 'www.movbay.com',
        'your_address': 'Kimberly Lane, Ikeja, Lagos',
    })
   return html_string