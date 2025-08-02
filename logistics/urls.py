from django.urls import path
from . import views


urlpatterns = [
    path('go-online', views.GoOnlineView.as_view(), name='go-online'),
    path('update-longlat', views.UpdateLatLongView.as_view(), name='update-longlat'),
    path('accept-ride/<str:pk>/', views.AcceptRide.as_view(), name='accept-rides'),
    path('rides/', views.RideView.as_view(), name='get_all_views'),
    path('rides/<str:pk>/', views.RideDetailView.as_view(), name='ride_details'),
    path('kyc/', views.KYCDetailAPIView.as_view(), name='kyc_verification'),
    path('bank-details/', views.BankDetailAPIView.as_view(), name='bank-detail'),
    path('delivery-preference', views.DeliveryPreferenceAPIView.as_view(), name='delivery_view'),
    path('rider/', views.BaseRiderProfileView.as_view(), name='rider-view'),
    path('mark-as-picked/<str:pk>/', views.PickedView.as_view(), name='mark-as-picked')
]
