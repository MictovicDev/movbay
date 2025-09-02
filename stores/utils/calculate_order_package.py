from .categories import categories
from django.shortcuts import get_object_or_404
from stores.models import Product

PACKAGING_OPTIONS = [
    {"name": "Small Box", "length": 20, "width": 15, "height": 10, "max_weight": 2},
    {"name": "Medium Box", "length": 40, "width": 30, "height": 20, "max_weight": 5},
    {"name": "Large Box", "length": 60, "width": 40, "height": 40, "max_weight": 10},
    {"name": "Poly Mailer", "length": 30, "width": 25, "height": 5, "max_weight": 1},
]

def choose_packaging(length, width, height, weight):
    for pkg in PACKAGING_OPTIONS:
        if (length <= pkg["length"] and
            width <= pkg["width"] and
            height <= pkg["height"] and
            weight <= pkg["max_weight"]):
            return pkg["name"]
    return "Custom Packaging"  # fallback if nothing fits


def calculate_order_package(order_items):
    print('Entrederd')
    total_weight = 0
    max_length = 0
    max_width = 0
    total_height = 0
    # print(order_items)
    for item in order_items:
        print(item)
        product_id = item.get('product')
        product = get_object_or_404(Product, id=product_id)
        quantity = item.get('quantity', 1)
        print(product)
        print(quantity)
        try:
            dims = categories[product.category][product.size]
        except Exception as e:
            print(e)
            dims = categories['others'][product.size]
        length, width, height, weight = dims["length"], dims["width"], dims["height"], dims["weight"]

        # Scale by quantity
        total_weight += weight * quantity
        max_length = max(max_length, length)
        max_width = max(max_width, width)
        total_height += height * quantity
    packaging_name = choose_packaging(max_length, max_width, total_height, total_weight)
    print(packaging_name)

    return {
        "length": max_length,
        "width": max_width,
        "height": total_height,
        "weight": total_weight,
        "name":packaging_name,
        "type": 'box',
        "weight_unit": "kg",
        "size_unit": "cm"
        
    }
