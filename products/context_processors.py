from .notifications import get_user_unread_notifications_count


def notifications_context(request):
    """
    Context processor para agregar el contador de notificaciones no leídas
    a todos los templates
    """
    if request.user.is_authenticated:
        return {
            'unread_notifications_count': get_user_unread_notifications_count(request.user)
        }
    return {
        'unread_notifications_count': 0
    }
