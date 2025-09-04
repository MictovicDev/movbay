from django.urls import path
from . import views


urlpatterns = [
     path('', views.ConversationView.as_view(), name='chats'),
     path('<str:room_name>', views.ConversationDetailView.as_view(), name='conversation-detail'),
     path('messages/', views.ProductMessageCreateView.as_view(), name='messages'),
     path('status-message/', views.StatusMessageCreateView.as_view(), name='status-message'),
     path('dm/<str:room_name>', views.DirectMessageCreateView.as_view(), name='dm')
]
