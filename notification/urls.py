from django.urls import path
from . import views


urlpatterns = [
    path('fcm-token/', views.RegisterFcmToken.as_view(), name='fcm-token'),
    path('', views.NotificationView.as_view(), name='notifications')

]
