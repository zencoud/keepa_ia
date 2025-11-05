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
    
    # IA
    path('detect-document-intent/', views.detect_document_intent_view, name='detect_document_intent'),
    path('ai-chat/', views.ai_chat_view, name='ai_chat'),
    path('generate-ai-summary/<str:asin>/', views.generate_ai_summary_view, name='generate_ai_summary'),
    path('generate-document/', views.generate_document_view, name='generate_document'),
    
    # Best Sellers
    path('categories/search/', views.search_categories_view, name='search_categories'),
    path('bestsellers/', views.best_sellers_view, name='best_sellers'),
    path('bestsellers/api/', views.best_sellers_api_view, name='best_sellers_api'),
    path('bestsellers/clear-history/', views.clear_search_history_view, name='clear_search_history'),
]
