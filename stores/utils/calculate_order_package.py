from .categories import categories
from django.shortcuts import get_object_or_404
from stores.models import Product


# {
#     "status": "success",
#     "message": "Retrieved successfully",
#     "data": [
#         {
#             "box_size_id": 27459899,
#             "name": "tiny box",
#             "description_image_url": "https://res.cloudinary.com/delivry/image/upload/v1635776054/package_boxes/tiny_box_ie9dob.jpg",
#             "height": 2,
#             "width": 5,
#             "length": 5,
#             "max_weight": 5
#         },
#         {
#             "box_size_id": 44174253,
#             "name": "medium box",
#             "description_image_url": "https://res.cloudinary.com/delivry/image/upload/v1635776059/package_boxes/medium_box_v1oisg.png",
#             "height": 10,
#             "width": 20,
#             "length": 20,
#             "max_weight": 20
#         },
#         {
#             "box_size_id": 42172412,
#             "name": "big box",
#             "description_image_url": "https://res.cloudinary.com/delivry/image/upload/v1635776049/package_boxes/big_box_wrcubo.png",
#             "height": 2,
#             "width": 40,
#             "length": 40,
#             "max_weight": 40
#         }
#     ]
# }

# PACKAGING_OPTIONS = [
#     {"name": "tiny_box", "length": 5, "width": 5, "height": 2, "max_weight": 5},
#     {"name": "medium_box", "length": 20, "width": 20, "height": 10, "max_weight": 5},
#     {"name": "big_box", "length": 40, "width": 40, "height": 2, "max_weight": 40},

# ]


PACKAGING_OPTIONS = [
    {"name": "small_box", "length": 25, "width": 25, "height": 15, "max_weight": 3},
    {"name": "medium_box", "length": 40, "width": 35, "height": 25, "max_weight": 8},
    {"name": "large_box", "length": 60, "width": 50, "height": 35, "max_weight": 20},
    {"name": "xlarge_box", "length": 90, "width": 70, "height": 50, "max_weight": 50},
    {"name": "xxlarge_box", "length": 150,
        "width": 100, "height": 80, "max_weight": 100},
]


def choose_packaging(length, width, height, weight):
    for pkg in PACKAGING_OPTIONS:
        if (length <= pkg["length"] and
            width <= pkg["width"] and
            height <= pkg["height"] and
                weight <= pkg["max_weight"]):
            return pkg["name"]
    return "Custom Packaging"  # fallback if nothing fits


# def calculate_order_package(order_items):
#     # print('Entrederd')
#     categories_id = []
#     total_weight = 0
#     max_length = 0
#     max_width = 0
#     total_height = 0
#     # print(order_items)
#     for item in order_items:
#         # print(item)
#         product_id = item.get('product')
#         product = get_object_or_404(Product, id=product_id)
#         quantity = item.get('quantity', 1)
#         # print(product)
#         # print(quantity)
#         try:
#             dims = categories[product.category.lower()][product.size]
#             # categories_id = [categories[product.category.lower()]['category_id'] if categories[product.category.lower()]['category_id'] not in categr ]
#             categories_id.append(
#                 categories[product.category.lower()]['category_id'])
#             # print(dims)
#         except Exception as e:
#             # print('Error' + str(e))
#             # print(e)
#             print('Me' + str(e))
#             dims = categories['others'][product.size]
#         length, width, height, weight = dims["length"], dims["width"], dims["height"], dims["weight"]

#         # Scale by quantity
#         total_weight += weight * quantity
#         max_length = max(max_length, length)
#         max_width = max(max_width, width)
#         total_height += height * quantity
#     packaging_name = choose_packaging(
#         max_length, max_width, total_height, total_weight)
#     # print(categories_id)
#     return {
#         "product_name": product.store.name,
#         "length": max_length,
#         "width": max_width,
#         "height": total_height,
#         "weight": total_weight,
#         "name": packaging_name,
#         "type": 'box',
#         "weight_unit": "kg",
#         "category_id": categories_id,
#         "size_unit": "cm"
#     }


# def calculate_order_package(order_items):
#     results = []  # will hold individual package details for each item

#     for item in order_items:
#         product_id = item.get('product')
#         product = get_object_or_404(Product, id=product_id)
#         quantity = item.get('quantity', 1)

#         try:
#             dims = categories[product.category.lower()][product.size]
#             category_id = categories[product.category.lower()]['category_id']
#         except Exception as e:
#             print(f"Category error for {product.name}: {e}")
#             dims = categories['others'][product.size]
#             category_id = categories['others']['category_id']

#         # Extract item dimensions
#         length, width, height, weight = (
#             dims["length"],
#             dims["width"],
#             dims["height"],
#             dims["weight"],
#         )

#         # Multiply per quantity
#         total_weight = weight * quantity
#         total_height = height * quantity

#         # Determine packaging for this item
#         packaging_name = choose_packaging(length, width, total_height, total_weight)

#         # Build item-specific result
#         results.append({
#             "name": product.title,
#             "description": product.description,
#             "unit_weight": total_weight,
#             "unit_amount": product.original_price,
#             # "name": packaging_name,
#             # "type": "box",
#             "category_id": category_id,
#             "quantity": quantity
#         })
#     dimensions = []
#     return [results, ]


def calculate_order_package(order_items):
    results = []
    total_height = 0
    max_length = 0
    max_width = 0
    total_weight = 0

    for item in order_items:
        product_id = item.get('product')
        product = get_object_or_404(Product, id=product_id)
        quantity = item.get('quantity', 1)

        try:
            dims = categories[product.category.lower()][product.size]
            category_id = categories[product.category.lower()]['category_id']
        except Exception as e:
            print(f"Category error for {product.title}: {e}")
            dims = categories['others'][product.size]
            category_id = categories['others']['category_id']

        length, width, height, weight = (
            dims["length"],
            dims["width"],
            dims["height"],
            dims["weight"]
        )

        total_height += height * quantity
        total_weight += weight * quantity
        max_length = max(max_length, length)
        max_width = max(max_width, width)

        # Choose packaging (based on item dimension)
        packaging_name = choose_packaging(
            length, width, height * quantity, weight * quantity)

        # Append item info without dimensions
        results.append({
            "name": product.title,
            "description": product.description,
            "unit_amount": product.original_price,
            "unit_weight": weight * quantity,
            "category_id": category_id,
            "quantity": quantity
        })

    # Add overall dimension summary
    overall_dimension = {
        "package_dimension": {
            "length": max_length,
            "width": max_width,
            "height": total_height
        },
        "total_weight": total_weight,
        "package_items": results
    }

    return overall_dimension
