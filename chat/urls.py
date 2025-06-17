from django.urls import path
from . import views


urlpatterns = [
     path('', views.ChatBoxView.as_view(), name='chats')
]
