from django.db import transaction
from ..models import Order, Product, OrderItem, Store
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from ..serializers import OrderSerializer
from rest_framework import status
from payment.models import Payment, Transactions
from wallet.models import Wallet
from payment.utils.helper import generate_tx_ref
from django.contrib.auth import get_user_model


User = get_user_model()

{
    "order": {
        "cart_items": [
            {
                "store_id": 29,
                "order_items": [
                    {
                        "product_id": 50,
                        "quantity": 1,
                        "amount": 5000
                    },
                    {
                        "product_id": 51,
                        "quantity": 1,
                        "amount": 2000
                    }
                ],
                "total_amount": 7000
            },
            {
                "store_id": 28,
                "order_items": [
                    {
                        "product_id": 49,
                        "quantity": 1,
                        "amount": 2000
                    }
                ],
                "total_amount": 2000
            }
        ],
        "total_amount": 9000,
        "payment_method": "wallet",
        "provider_name": "paystack"
    }
}


@transaction.atomic
def create_order_with_items(order_data, request, transaction_data):
    admin_user = User.objects.filter(is_superuser=True).first()
    platform_wallet, _ = Wallet.objects.get_or_create(owner=admin_user)
    amount = order_data.get("total_amount")
    sender_wallet = request.user.wallet

    if sender_wallet.balance < amount:
        raise ValueError("Insufficient Funds")

    # Deduct from sender
    sender_wallet.balance -= amount
    sender_wallet.save()

    # Add to platform
    platform_wallet.balance += amount
    platform_wallet.save()

    # Create payment
    payment = Payment.objects.create(
        user=request.user,
        method='wallet',
        amount=amount,
        currency="NGN",
        reference=transaction_data.get('reference'),
        transaction_id=generate_tx_ref('PAY'),
        status='completed',
        payment_method='wallet'
    )

    Transactions.objects.create(owner=request.user, payment=payment)

    response_data = []

    for item in order_data.get('cart_items'):
        store = get_object_or_404(Store, id=item.get("store_id"))
        store_amount = item.get("total_amount")

        order_instance = Order.objects.create(
            store=store, amount=store_amount, payment=payment
        )
        for i in item.get("order_items"):
            product = get_object_or_404(Product, id=i.get("product_id"))
            print(product)
            quantity = i.get("quantity")
            amount = i.get("amount")
            try:
                order_item = OrderItem.objects.create(
                    product=product, count=quantity, order=order_instance, amount=amount
                )
                print(order_item)

            except Exception as e:
                print(e)

            # Decrease stock
            try:
                product.stock_available -= quantity
                product.save()
            except Exception as e:
                print(e)

        response_data.append(OrderSerializer(order_instance).data)

    return Response(response_data, status=status.HTTP_201_CREATED)
