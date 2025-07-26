from django.urls import path
from . import views


urlpatterns = [
    path('go-online', views.GoOnlineView.as_view(), name='go-online'),
    path('update-longlat', views.UpdateLatLongView.as_view(), name='update-longlat')
    
    ]
