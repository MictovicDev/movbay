from django.db import transaction
from ..models import Order, Product, OrderItem, Store, Delivery
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from ..serializers import OrderSerializer
from rest_framework import status
from payment.models import Payment, Transactions
from wallet.models import Wallet
from payment.utils.helper import generate_tx_ref
from django.contrib.auth import get_user_model
from datetime import timedelta, datetime
from django.utils import timezone
from notification.models import Device
from stores.tasks import send_push_notification
from decimal import Decimal
from rest_framework.exceptions import ValidationError
# from stores.tasks import get_shipping_rates
from wallet.models import WalletTransactions


User = get_user_model()


@transaction.atomic
def create_order_with_items(user, order_data, reference, method):
    admin_user = User.objects.filter(is_superuser=True).first()
    platform_wallet, _ = Wallet.objects.get_or_create(owner=admin_user)
    amount = order_data.get("total_amount")
    print(amount)
    delivery_data = order_data['delivery']
    print(delivery_data)
    delivery = Delivery.objects.create(user=user, **delivery_data)
    print(delivery)
    
    if method == 'wallet':
        sender_wallet = user.wallet
        print("BALANCE:", sender_wallet.balance, "AMOUNT:", amount, type(amount))
        print(user.wallet)
        if Decimal(sender_wallet.balance) < Decimal(amount):
            print(True)
            raise ValidationError({"wallet": "Insufficient Funds"})
        sender_wallet.balance -= amount
        sender_wallet.save()
        WalletTransactions.objects.create(content='Payment For Purchase Made Succesfully', type='Item-Purchase', wallet=sender_wallet)
        platform_wallet.balance += amount
        platform_wallet.save()

    payment = Payment.objects.create(
        user=user,
        amount=amount,
        currency="NGN",
        reference=reference,
        transaction_id=generate_tx_ref('PAY'),
        status='completed',
        payment_method='wallet'
    )

    Transactions.objects.create(owner=user, payment=payment)

    response_data = []
    created_orders = {}  # store_id -> order_instance
    cart_items = order_data.get('items')
    for item in cart_items:
        store_id = item.get("store")
        store = get_object_or_404(Store, id=store_id)
        device = Device.objects.get(user=store.owner)
        product = get_object_or_404(Product, id=item.get("product"))
        quantity = item.get("quantity")
        item_amount = item.get("amount")
        print(quantity)
        print(item_amount)
        now = timezone.now()
        order_instance, created = Order.objects.get_or_create(
            store=store,
            payment=payment,
            buyer=user,
            delivery=delivery,
            # amount=0,
        )
        created_orders[store_id] = order_instance

        # Create OrderItem
        try:
            OrderItem.objects.create(
                product=product,
                count=quantity,
                order=order_instance,
                amount=item_amount
            )
        except Exception as e:
            print("Error creating order item:", e)

        # Decrease product stock
        try:
            print('Trying it')
            product.stock_available -= int(quantity)
            product.save()
        except Exception as e:
            print("Error updating stock:", e)

        # Add item amount to order's total
        print(order_instance.amount)
        order_instance.amount += item_amount
        order_instance.save()

    # Serialize all created/used orders
    for order in created_orders.values():
        print(order.order_id)
        # Custom formatting logic
        expected_delivery = timezone.now() + timedelta(hours=4)
        formatted_delivery = expected_delivery.strftime("Today by %I:%M %p")

        response_data.append({
            "order_id": f"{order.order_id if hasattr(order, 'order_id') else order.id}",
            "expected_delivery": formatted_delivery,
            "payment_details": order.payment.payment_method
        }),
        data = "You have a new order on movbay, click to confirm it."
        send_push_notification.delay(
            token=device.token, title='New Order Available', notification_type="New Order", data=data)
        # get_shipping_rates.delay(order)
    
    
    return Response(response_data, status=status.HTTP_201_CREATED)