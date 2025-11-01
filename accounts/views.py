from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.db.models import Count, Avg, Q
from datetime import timedelta
from products.models import Product, PriceAlert, Notification


@require_http_methods(["GET", "POST"])
def login_view(request):
    """Vista de login"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        if username and password:
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'¡Bienvenido, {user.username}!')
                return redirect('dashboard')
            else:
                messages.error(request, 'Usuario o contraseña incorrectos.')
        else:
            messages.error(request, 'Por favor, completa todos los campos.')
    
    return render(request, 'accounts/login.html')


@login_required
def logout_view(request):
    """Vista de logout"""
    logout(request)
    messages.info(request, 'Has cerrado sesión correctamente.')
    return redirect('accounts:login')


@login_required
def dashboard_view(request):
    """Vista de dashboard con estadísticas"""
    user = request.user
    now = timezone.now()
    seven_days_ago = now - timedelta(days=7)
    one_day_ago = now - timedelta(days=1)
    
    # Estadísticas de Productos (filtradas por usuario)
    user_products = Product.objects.filter(queried_by=user)
    total_products = user_products.count()
    recent_products = user_products.filter(last_updated__gte=seven_days_ago).count()
    
    # Precio promedio (solo productos con precio)
    avg_price_result = user_products.filter(
        current_price_new__isnull=False
    ).aggregate(avg_price=Avg('current_price_new'))
    avg_price = (avg_price_result['avg_price'] / 100) if avg_price_result['avg_price'] else 0
    
    # Top 3 productos mejor calificados del usuario
    top_rated_products = user_products.filter(
        rating__isnull=False
    ).order_by('-rating', '-review_count')[:3]
    
    # Estadísticas de Alertas
    user_alerts = PriceAlert.objects.filter(user=user)
    total_alerts = user_alerts.count()
    active_alerts = user_alerts.filter(is_active=True).count()
    triggered_alerts = user_alerts.filter(triggered=True).count()
    
    # Distribución de alertas por tipo de precio
    alerts_by_price_type = user_alerts.values('price_type').annotate(
        count=Count('id')
    )
    alerts_by_type = {
        'new': 0,
        'amazon': 0,
        'used': 0
    }
    for item in alerts_by_price_type:
        alerts_by_type[item['price_type']] = item['count']
    
    # Alertas activas recientes
    recent_active_alerts = user_alerts.filter(
        is_active=True
    ).order_by('-created_at')[:5]
    
    # Estadísticas de Notificaciones
    user_notifications = Notification.objects.filter(user=user)
    total_notifications = user_notifications.count()
    unread_notifications = user_notifications.filter(is_read=False).count()
    recent_notifications_count = user_notifications.filter(
        created_at__gte=one_day_ago
    ).count()
    
    # Distribución de notificaciones por tipo
    notifications_by_type = user_notifications.values('notification_type').annotate(
        count=Count('id')
    )
    notif_by_type = {
        'price_alert': 0,
        'system': 0,
        'info': 0,
        'warning': 0
    }
    for item in notifications_by_type:
        notif_by_type[item['notification_type']] = item['count']
    
    # Notificaciones recientes
    recent_notifications = user_notifications.order_by('-created_at')[:5]
    
    context = {
        'user': user,
        # Productos
        'total_products': total_products,
        'recent_products': recent_products,
        'avg_price': avg_price,
        'top_rated_products': top_rated_products,
        # Alertas
        'total_alerts': total_alerts,
        'active_alerts': active_alerts,
        'triggered_alerts': triggered_alerts,
        'alerts_by_type': alerts_by_type,
        'recent_active_alerts': recent_active_alerts,
        # Notificaciones
        'total_notifications': total_notifications,
        'unread_notifications': unread_notifications,
        'recent_notifications_count': recent_notifications_count,
        'notif_by_type': notif_by_type,
        'recent_notifications': recent_notifications,
    }
    
    return render(request, 'accounts/home.html', context)