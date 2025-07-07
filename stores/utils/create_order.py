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

User = get_user_model()


@transaction.atomic
def create_order_with_items(order_data, request, reference, method):
    admin_user = User.objects.filter(is_superuser=True).first()
    platform_wallet, _ = Wallet.objects.get_or_create(owner=admin_user)
    amount = order_data.get("total_amount")
    delivery_data = order_data['delivery']
    delivery = Delivery.objects.create(**delivery_data)
    sender_wallet = request.user.wallet
    
    if sender_wallet.balance < amount:
        raise ValueError("Insufficient Funds")

    # Deduct from sender
    sender_wallet.balance -= amount
    sender_wallet.save()

    # Add to platform
    platform_wallet.balance += amount
    platform_wallet.save()
    payment = Payment.objects.create(
        user=request.user,
        amount=amount,
        currency="NGN",
        reference= reference,
        transaction_id=generate_tx_ref('PAY'),
        status='completed',
        payment_method='wallet'
    )
    # delivery = Delivery.objects.create(delivery_method=)
    Transactions.objects.create(owner=request.user, payment=payment)

    response_data = []
    cart_items = order_data.get('items')
    for item in cart_items:
        store = get_object_or_404(Store, id=item.get("store"))
        store_amount = item.get("amount")
        order_instance = Order.objects.create(
            store=store, amount=store_amount, payment=payment
        )
        product = get_object_or_404(Product, id=item.get("product"))
        quantity = item.get("quantity")
        amount = item.get("amount")
        try:
            order_item = OrderItem.objects.create(
                product=product, count=quantity, order=order_instance, amount=amount
            )
            print(order_item)

        except Exception as e:
            print(e)
        try:
            product.stock_available -= quantity
            product.save()
        except Exception as e:
            print(e)
    print(order_instance)
    response_data.append(OrderSerializer(order_instance).data)
    return Response(response_data, status=status.HTTP_201_CREATED)
