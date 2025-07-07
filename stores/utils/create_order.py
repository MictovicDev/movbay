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
def create_order_with_items(user, order_data, reference, method):
    admin_user = User.objects.filter(is_superuser=True).first()
    platform_wallet, _ = Wallet.objects.get_or_create(owner=admin_user)
    amount = order_data.get("total_amount")
    delivery_data = order_data['delivery']
    delivery = Delivery.objects.create(**delivery_data)
    if method == 'wallet':
        sender_wallet = user.wallet
        print(sender_wallet)
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
        reference= reference,
        transaction_id=generate_tx_ref('PAY'),
        status='completed',
        payment_method='wallet'
    )
    # delivery = Delivery.objects.create(delivery_method=)
    Transactions.objects.create(owner=user, payment=payment)

    response_data = []
    cart_items = order_data.get('items')
    for item in cart_items:
        store = get_object_or_404(Store, id=item.get("store"))
        store_amount = item.get("amount")
        order_instance = Order.objects.create(
            store=store, amount=store_amount, payment=payment, buyer_name=user.fullname, buyer_number=user.phone_number
        )
        print(order_instance)
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
            product.stock_available -= int(quantity)
            product.save()
        except Exception as e:
            print(e)
    print(order_instance)
    response_data.append(OrderSerializer(order_instance).data)
    return Response(response_data, status=status.HTTP_201_CREATED)
