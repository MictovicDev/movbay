from django.contrib import admin
from .models import Store, Status, StoreFollower, Product, ProductImage

# Register your models here.
admin.site.register(Store)
admin.site.register(Status)
admin.site.register(Product)
admin.site.register(ProductImage)
