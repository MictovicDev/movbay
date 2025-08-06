from django.contrib import admin
from . import views
from django.urls import path

urlpatterns = [
    path('stores/', views.StoreListCreateView.as_view(), name='store-list'),
    path('stores/<str:pk>/', views.StoreDetailView.as_view(), name='store-list'),
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
    path('status/<str:pk>/', views.ProductStatusView.as_view(),
         name='product-status'),
    path('status/', views.StatusView.as_view(), name='status-creation'),
    path('order/<str:pk>/confirm',
         views.ConfirmOrder.as_view(), name='confirm-order'),
    path('order/<str:pk>/mark-for-delivery',
         views.MarkForDeliveryView.as_view(), name='mark-as-delivered'),
    path('order/user/', views.GetUserOrder.as_view(), name='order-history'),
    path('order/<str:pk>/track-order',
         views.TrackOrder.as_view(), name='order_tracking'),
    path('stores/<int:store_id>/reviews/',
         views.ReviewView.as_view(), name='create-review'),
    path('order/<str:pk>/mark-as-delivered',
         views.MarkAsDelivered.as_view(), name='mark-as-delivered'),
    path('verify-order/<str:pk>/', views.VerifyOrderView.as_view(), name='verify-order'),
    path('products/more-from-seller/<str:pk>/', views.MoreFromSeller.as_view(), name='morefromseller'),
    path('rate-product/<str:pk>', views.ProductRatingView.as_view(), name='RateProduct')
]
