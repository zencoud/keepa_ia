from .notifications import get_user_unread_notifications_count
from .models import PriceAlert


def notifications_context(request):
    """
    Context processor para agregar el contador de notificaciones no leídas
    y alertas activas a todos los templates
    """
    if request.user.is_authenticated:
        active_alerts_count = PriceAlert.objects.filter(user=request.user, is_active=True).count()
        return {
            'unread_notifications_count': get_user_unread_notifications_count(request.user),
            'active_alerts_count': active_alerts_count
        }
    return {
        'unread_notifications_count': 0,
        'active_alerts_count': 0
    }
