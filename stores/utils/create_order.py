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

User = get_user_model()


@transaction.atomic
def create_order_with_items(user, order_data, reference, method):
    admin_user = User.objects.filter(is_superuser=True).first()
    platform_wallet, _ = Wallet.objects.get_or_create(owner=admin_user)

    amount = order_data.get("total_amount")
    delivery_data = order_data['delivery']
    delivery = Delivery.objects.create(**delivery_data)

    if method == 'wallet':
        sender_wallet = user.wallet
        if sender_wallet.balance < amount:
            raise ValueError("Insufficient Funds")

        sender_wallet.balance -= amount
        sender_wallet.save()

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
        product = get_object_or_404(Product, id=item.get("product"))
        quantity = item.get("quantity")
        item_amount = item.get("amount")

        if store_id not in created_orders:
            # Check if an order already exists for this store + user
            order_instance = Order.objects.filter(
                buyer=user,
                store=store,
                status='new'
            ).first()

            if not order_instance:
                order_instance = Order.objects.create(
                    store=store,
                    amount=0,  # temporarily 0, will update later
                    payment=payment,
                    buyer=user,
                    delivery=delivery
                )

            created_orders[store_id] = order_instance
        else:
            order_instance = created_orders[store_id]

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
            product.stock_available -= int(quantity)
            product.save()
        except Exception as e:
            print("Error updating stock:", e)

        # Add item amount to order's total
        order_instance.amount += item_amount
        order_instance.save()

    # Serialize all created/used orders
    for order in created_orders.values():
        print(order.order_id)
        # Custom formatting logic
        expected_delivery = timezone.now() + timedelta(hours=4)
        formatted_delivery = expected_delivery.strftime("Today by %I:%M %p")
        
        formatted_payment = f"₦{order.amount:,.0f} (Paid via Wallet)"

        response_data.append({
            "order_id": f"{order.order_id if hasattr(order, 'order_id') else order.id}",
            "expected_delivery": formatted_delivery,
            "payment_details": order.payment.payment_method
        })

    return Response(response_data, status=status.HTTP_201_CREATED)
