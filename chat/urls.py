from django.urls import path
from . import views


urlpatterns = [
     path('', views.ChatBoxAsyncView.as_view(), name='chats')
]
