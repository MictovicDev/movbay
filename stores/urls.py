from django.contrib import admin
from . import views
from django.urls import path

urlpatterns = [
    path('stores/', views.StoreListCreateView.as_view(), name='store-list'),
    path('dashboard/', views.DashBoardView.as_view(), name='dashboard'),
    path('orders/', views.OrderListCreateView.as_view(), name='order-list'),
    path('orders/<int:pk>/', views.OrderDetailView.as_view(), name='order-detail'),
    path('delivery/', views.DeliveryDetailsCreateView.as_view(),
         name='delivery_details'),
    path('products/', views.ProductListCreateView.as_view(), name='products'),
    path('products/<int:pk>/', views.ProductDetailView.as_view(),
         name='product-detail'),
    path('follow/<str:pk>/', views.StoreFollowView.as_view(), name='followstore'),
    path('followers/', views.StoreFollowers.as_view(), name='viewstorefollowers'),
    path('userproducts/', views.UserProductListView.as_view(), name='user-product'),
    path('userproduct/<int:pk>/', views.UserProductDetailView.as_view(),
         name='user-product-detail'),
    path('status/<str:pk>/', views.StatusView.as_view(), name='status')

]
