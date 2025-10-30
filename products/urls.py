from django.urls import path
from . import views

app_name = 'products'

urlpatterns = [
    # Productos
    path('search/', views.search_product_view, name='search'),
    path('detail/<str:asin>/', views.product_detail_view, name='detail'),
    path('list/', views.product_list_view, name='list'),
    path('refresh/<str:asin>/', views.refresh_product_view, name='refresh'),
    path('delete/<str:asin>/', views.delete_product_view, name='delete'),
    
    # Alertas de Precio
    path('alert/create/<str:asin>/', views.create_alert_view, name='create_alert'),
    path('alerts/', views.list_alerts_view, name='alerts_list'),
    path('alert/delete/<int:alert_id>/', views.delete_alert_view, name='delete_alert'),
    
    # Notificaciones
    path('notifications/', views.notifications_view, name='notifications'),
    path('notifications/mark-read/<int:notification_id>/', views.mark_notification_read_view, name='mark_notification_read'),
    path('notifications/mark-all-read/', views.mark_all_notifications_read_view, name='mark_all_notifications_read'),
]
