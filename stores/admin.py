from django.contrib import admin
from .models import Store, StoreStatus, StoreFollower, Product, ProductImage

# Register your models here.
admin.site.register(Store)
admin.site.register(StoreStatus)
admin.site.register(Product)
admin.site.register(ProductImage)
