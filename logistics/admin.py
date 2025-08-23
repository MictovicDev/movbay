from django.contrib import admin
from .models import Ride, KYC, BankDetail, DeliveryPreference, Address, ShippingRate
# Register your models here.


admin.site.register(Ride)
admin.site.register(KYC)
admin.site.register(DeliveryPreference)
admin.site.register(BankDetail)
admin.site.register(Address)
admin.site.register(ShippingRate)