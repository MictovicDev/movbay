from django.db import transaction
from ..models import Order, Product, OrderItem
from django.shortcuts import get_object_or_404



@transaction.atomic
def create_order_with_items(request, cart_items, payment):
    user = request.user
    order_items = []
    for item in cart_items:
        product = get_object_or_404(Product, id=item.get('product_id'))
        order = Order.objects.create(user=user, store=product.store, payment=payment)
        print(order)
        count = item.get("quantity", 1)
        print(count)
        order_items.append(OrderItem(
            order=order,
            product=product,
            count=count
        ))

        # Optionally update stock
        product.stock -= count
        product.save()

    # Bulk create order items
    order_item = OrderItem.objects.bulk_create(order_items)
    return order_item