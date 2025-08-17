


def calculate_order_package(order_items, mapping):
    total_weight = 0
    max_length = 0
    max_width = 0
    total_height = 0

    for item in order_items:
        product = item["product"]
        quantity = item["quantity"]

        dims = mapping[product["category"]][product["size"]]
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
