import logging
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone
from .models import PriceAlert, Notification

logger = logging.getLogger(__name__)


def create_system_notification(user, title, message, notification_type='info', alert=None):
    """
    Crea una notificación en el sistema
    
    Args:
        user: Usuario destinatario
        title: Título de la notificación
        message: Mensaje completo
        notification_type: Tipo de notificación
        alert: Alerta relacionada (opcional)
    
    Returns:
        Notification object creada
    """
    try:
        notification = Notification.objects.create(
            user=user,
            alert=alert,
            notification_type=notification_type,
            title=title,
            message=message
        )
        logger.info(f"Notificación creada para {user.username}: {title}")
        return notification
    except Exception as e:
        logger.error(f"Error creando notificación para {user.username}: {e}")
        return None


def send_email_notification(user, subject, html_content, text_content=None):
    """
    Envía una notificación por email
    
    Args:
        user: Usuario destinatario
        subject: Asunto del email
        html_content: Contenido HTML del email
        text_content: Contenido texto plano (opcional)
    
    Returns:
        bool: True si se envió correctamente
    """
    try:
        if text_content is None:
            # Generar contenido texto plano básico desde HTML
            import re
            text_content = re.sub(r'<[^>]+>', '', html_content)
            text_content = re.sub(r'\s+', ' ', text_content).strip()
        
        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email]
        )
        msg.attach_alternative(html_content, "text/html")
        
        result = msg.send()
        logger.info(f"Email enviado a {user.email}: {subject}")
        return True
        
    except Exception as e:
        logger.error(f"Error enviando email a {user.email}: {e}")
        return False


def send_price_alert_notification(alert, current_price):
    """
    Envía notificación de alerta de precio (email + sistema)
    
    Args:
        alert: Objeto PriceAlert
        current_price: Precio actual en centavos
    
    Returns:
        bool: True si se envió correctamente
    """
    try:
        # Preparar datos para templates
        context = {
            'alert': alert,
            'product': alert.product,
            'user': alert.user,
            'current_price': current_price,
            'current_price_display': f"${current_price / 100:.2f}",
            'target_price_display': alert.get_target_price_display(),
            'savings': alert.target_price - current_price,
            'savings_display': f"${(alert.target_price - current_price) / 100:.2f}",
            'site_name': getattr(settings, 'SITE_NAME', 'Keepa IA'),
            'site_url': getattr(settings, 'SITE_URL', 'http://localhost:8000'),
            'product_url': f"{getattr(settings, 'SITE_URL', 'http://localhost:8000')}/products/detail/{alert.product.asin}/",
        }
        
        # Crear notificación en el sistema
        title = f"¡Alerta de Precio! {alert.product.title[:50]}..."
        message = f"El precio de {alert.product.title} bajó a {context['current_price_display']} (objetivo: {context['target_price_display']})"
        
        notification = create_system_notification(
            user=alert.user,
            title=title,
            message=message,
            notification_type='price_alert',
            alert=alert
        )
        
        # Enviar email
        subject = f"💰 {context['site_name']} - Alerta de Precio: {alert.product.title[:50]}..."
        
        html_content = render_to_string('products/email/price_alert.html', context)
        text_content = render_to_string('products/email/price_alert.txt', context)
        
        email_sent = send_email_notification(
            user=alert.user,
            subject=subject,
            html_content=html_content,
            text_content=text_content
        )
        
        # Marcar alerta como disparada
        alert.triggered = True
        alert.triggered_at = timezone.now()
        alert.is_active = False  # Desactivar alerta después de disparar
        alert.save()
        
        logger.info(f"Alerta disparada para {alert.user.username} - {alert.product.asin}")
        return True
        
    except Exception as e:
        logger.error(f"Error enviando alerta de precio para {alert.user.username}: {e}")
        return False


def send_welcome_notification(user):
    """
    Envía notificación de bienvenida a un nuevo usuario
    
    Args:
        user: Usuario nuevo
    """
    title = f"¡Bienvenido a {getattr(settings, 'SITE_NAME', 'Keepa IA')}!"
    message = "Gracias por registrarte. Ahora puedes crear alertas de precio para tus productos favoritos de Amazon."
    
    create_system_notification(
        user=user,
        title=title,
        message=message,
        notification_type='info'
    )


def send_system_maintenance_notification(message, notification_type='system'):
    """
    Envía notificación de mantenimiento a todos los usuarios
    
    Args:
        message: Mensaje de mantenimiento
        notification_type: Tipo de notificación
    """
    from django.contrib.auth.models import User
    
    users = User.objects.filter(is_active=True)
    
    for user in users:
        create_system_notification(
            user=user,
            title="Mantenimiento del Sistema",
            message=message,
            notification_type=notification_type
        )
    
    logger.info(f"Notificación de mantenimiento enviada a {users.count()} usuarios")


def get_user_unread_notifications_count(user):
    """
    Obtiene el número de notificaciones no leídas de un usuario
    
    Args:
        user: Usuario
    
    Returns:
        int: Número de notificaciones no leídas
    """
    return Notification.objects.filter(user=user, is_read=False).count()


def mark_notification_as_read(notification_id, user):
    """
    Marca una notificación como leída
    
    Args:
        notification_id: ID de la notificación
        user: Usuario que marca como leída
    
    Returns:
        bool: True si se marcó correctamente
    """
    try:
        notification = Notification.objects.get(id=notification_id, user=user)
        notification.is_read = True
        notification.save()
        return True
    except Notification.DoesNotExist:
        return False


def mark_all_notifications_as_read(user):
    """
    Marca todas las notificaciones de un usuario como leídas
    
    Args:
        user: Usuario
    
    Returns:
        int: Número de notificaciones marcadas como leídas
    """
    updated_count = Notification.objects.filter(
        user=user, 
        is_read=False
    ).update(is_read=True)
    
    logger.info(f"Marcadas {updated_count} notificaciones como leídas para {user.username}")
    return updated_count
