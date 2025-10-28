from django.urls import path
from . import views

app_name = 'products'

urlpatterns = [
    path('search/', views.search_product_view, name='search'),
    path('detail/<str:asin>/', views.product_detail_view, name='detail'),
    path('list/', views.product_list_view, name='list'),
    path('refresh/<str:asin>/', views.refresh_product_view, name='refresh'),
    path('delete/<str:asin>/', views.delete_product_view, name='delete'),
]
