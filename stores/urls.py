from django.contrib import admin
from . import views
from django.urls import path

urlpatterns = [
    path('stores/', views.StoreListCreateView.as_view(), name='store-list'),
    path('dashboard/', views.DashBoardView.as_view(), name='dashboard'),
    path('orders/', views.OrderListCreateView.as_view(), name='order-list'),
    path('orders/confirm', views.ConfirmOrderView.as_view(), name='confirm-order'),
    path('orders/<int:pk>/', views.OrderDetailView.as_view(), name='order-detail'),
    path('products/', views.ProductListCreateView.as_view(), name='products'),
    path('products/<int:pk>/', views.ProductDetailView.as_view(), name='product-detail'),
    path('products/<int:pk>/delete/', views.DeleteProductView.as_view(), name='delete-product')
]