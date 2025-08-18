from .categories import categories

def calculate_order_package(order_items):
    total_weight = 0
    max_length = 0
    max_width = 0
    total_height = 0
    print(order_items)
    for item in order_items:
        print(item)
        product = item.product
        quantity = item.count
        print(product)
        print(quantity)
        try:
            dims = categories[product.category][product.size]
        except Exception as e:
             dims = categories['others'][product.size]
        length, width, height, weight = dims["length"], dims["width"], dims["height"], dims["weight"]

        # Scale by quantity
        total_weight += weight * quantity
        max_length = max(max_length, length)
        max_width = max(max_width, width)
        total_height += height * quantity

    return {
        "length": max_length,
        "width": max_width,
        "height": total_height,
        "weight": total_weight,
        "weight_unit": "kg",
        "size_unit": "cm"
        
    }
