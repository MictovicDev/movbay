from django.db import transaction
from ..models import Order, Product, OrderItem
from django.shortcuts import get_object_or_404



@transaction.atomic
def create_order_with_items(request, cart_items, payment):
    cart_items = request.data.get("cart_items", [])
    user = request.user
    order_items = []
    for item in cart_items:
        product = get_object_or_404(Product, id=item.product_id)
        order = Order.objects.create(user=user, store=product.store, payment=payment)
        count = item.get("quantity", 1)
        order_items.append(OrderItem(
            order=order,
            product=product,
            count=count
        ))

        # Optionally update stock
        product.stock -= count
        product.save()

    # Bulk create order items
    OrderItem.objects.bulk_create(order_items)