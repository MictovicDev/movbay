from django.contrib import admin
from .models import Store, Status, StoreFollow, Product, ProductImage, Order, Delivery, OrderItem

# Register your models here.
admin.site.register(Store)
admin.site.register(Status)
admin.site.register(Product)
admin.site.register(ProductImage)
admin.site.register(Order)
admin.site.register(Delivery)
admin.site.register(StoreFollow)
admin.site.register(OrderItem)