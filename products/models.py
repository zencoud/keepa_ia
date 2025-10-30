from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal
from django.utils import timezone


class Product(models.Model):
    """Modelo para almacenar información de productos de Amazon obtenida de Keepa API"""
    
    asin = models.CharField(
        max_length=10, 
        unique=True, 
        primary_key=True,
        help_text="Amazon Standard Identification Number"
    )
    title = models.CharField(
        max_length=500,
        help_text="Título del producto"
    )
    brand = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="Marca del producto"
    )
    image_url = models.URLField(
        max_length=500,
        null=True,
        blank=True,
        help_text="URL de la imagen principal del producto"
    )
    color = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="Color del producto"
    )
    binding = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="Tipo de producto (Electronics, Books, etc.)"
    )
    availability_amazon = models.IntegerField(
        default=0,
        help_text="Disponibilidad en Amazon (0=No disponible, 1=Disponible)"
    )
    categories = models.JSONField(
        default=list,
        help_text="Lista de categorías del producto"
    )
    category_tree = models.JSONField(
        default=list,
        help_text="Árbol de categorías del producto"
    )
    current_price_new = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Precio actual del producto nuevo (en centavos)"
    )
    current_price_amazon = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Precio actual vendido por Amazon (en centavos)"
    )
    current_price_used = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Precio actual del producto usado (en centavos)"
    )
    sales_rank_current = models.IntegerField(
        null=True,
        blank=True,
        help_text="Sales Rank actual del producto"
    )
    rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Calificación promedio del producto (0-5)"
    )
    review_count = models.IntegerField(
        null=True,
        blank=True,
        help_text="Número total de reseñas"
    )
    price_history = models.JSONField(
        default=dict,
        help_text="Historial completo de precios en formato JSON"
    )
    rating_history = models.JSONField(
        default=dict,
        help_text="Historial de calificaciones en formato JSON"
    )
    sales_rank_history = models.JSONField(
        default=dict,
        help_text="Historial de sales rank en formato JSON"
    )
    reviews_data = models.JSONField(
        default=dict,
        help_text="Datos de reseñas en formato JSON"
    )
    last_updated = models.DateTimeField(
        auto_now=True,
        help_text="Última vez que se actualizó la información"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Fecha de creación del registro"
    )
    queried_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        help_text="Usuario que consultó el producto"
    )
    
    class Meta:
        ordering = ['-last_updated']
        verbose_name = "Producto"
        verbose_name_plural = "Productos"
    
    def __str__(self):
        return f"{self.asin} - {self.title[:50]}..."
    
    def get_price_display(self, price_type='new'):
        """Convierte precio de centavos a formato legible"""
        price_field = f'current_price_{price_type}'
        price = getattr(self, price_field)
        if price:
            return f"${price / 100:.2f}"
        return "N/A"
    
    def get_rating_display(self):
        """Formatea la calificación con estrellas"""
        if self.rating:
            return f"{self.rating:.1f} ⭐"
        return "Sin calificación"
    
    def get_sales_rank_display(self):
        """Formatea el sales rank"""
        if self.sales_rank_current:
            return f"#{self.sales_rank_current:,}"
        return "N/A"


class PriceAlert(models.Model):
    """Modelo para alertas de precio configuradas por usuarios"""
    
    FREQUENCY_CHOICES = [
        (4, '4 veces al día (cada 6 horas)'),
        (2, '2 veces al día (cada 12 horas)'),
        (1, '1 vez al día (cada 24 horas)'),
    ]
    
    PRICE_TYPE_CHOICES = [
        ('new', 'Precio Nuevo'),
        ('amazon', 'Precio Amazon'),
        ('used', 'Precio Usado'),
    ]
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        help_text="Usuario que crea la alerta"
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        help_text="Producto a monitorear"
    )
    target_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Precio objetivo en centavos"
    )
    price_type = models.CharField(
        max_length=10,
        choices=PRICE_TYPE_CHOICES,
        default='new',
        help_text="Tipo de precio a monitorear"
    )
    frequency = models.IntegerField(
        choices=FREQUENCY_CHOICES,
        default=2,
        help_text="Frecuencia de verificación"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Si la alerta está activa"
    )
    triggered = models.BooleanField(
        default=False,
        help_text="Si ya se disparó la alerta"
    )
    triggered_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Fecha y hora cuando se disparó la alerta"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Fecha de creación de la alerta"
    )
    last_checked = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Última vez que se verificó esta alerta"
    )
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Alerta de Precio"
        verbose_name_plural = "Alertas de Precio"
        unique_together = ['user', 'product', 'price_type', 'target_price']
    
    def __str__(self):
        return f"{self.user.username} - {self.product.asin} - ${self.get_target_price_display()}"
    
    def get_target_price_display(self):
        """Convierte precio objetivo de centavos a formato legible"""
        return f"{self.target_price / 100:.2f}"
    
    def get_price_type_display(self):
        """Obtiene el display del tipo de precio"""
        return dict(self.PRICE_TYPE_CHOICES)[self.price_type]
    
    def get_frequency_display(self):
        """Obtiene el display de la frecuencia"""
        return dict(self.FREQUENCY_CHOICES)[self.frequency]
    
    def should_check_now(self):
        """Determina si la alerta debe verificarse ahora basado en su frecuencia"""
        if not self.last_checked:
            return True
        
        now = timezone.now()
        hours_since_last_check = (now - self.last_checked).total_seconds() / 3600
        
        if self.frequency == 4:  # Cada 6 horas
            return hours_since_last_check >= 6
        elif self.frequency == 2:  # Cada 12 horas
            return hours_since_last_check >= 12
        elif self.frequency == 1:  # Cada 24 horas
            return hours_since_last_check >= 24
        
        return False


class Notification(models.Model):
    """Modelo para notificaciones del sistema"""
    
    NOTIFICATION_TYPES = [
        ('price_alert', 'Alerta de Precio'),
        ('system', 'Sistema'),
        ('info', 'Información'),
        ('warning', 'Advertencia'),
    ]
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        help_text="Usuario destinatario"
    )
    alert = models.ForeignKey(
        PriceAlert,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="Alerta relacionada (si aplica)"
    )
    notification_type = models.CharField(
        max_length=20,
        choices=NOTIFICATION_TYPES,
        default='info',
        help_text="Tipo de notificación"
    )
    title = models.CharField(
        max_length=200,
        help_text="Título de la notificación"
    )
    message = models.TextField(
        help_text="Mensaje completo de la notificación"
    )
    is_read = models.BooleanField(
        default=False,
        help_text="Si la notificación fue leída"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Fecha de creación de la notificación"
    )
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Notificación"
        verbose_name_plural = "Notificaciones"
    
    def __str__(self):
        return f"{self.user.username} - {self.title}"
    
    def get_type_display(self):
        """Obtiene el display del tipo de notificación"""
        return dict(self.NOTIFICATION_TYPES)[self.notification_type]
    
    def get_type_icon(self):
        """Obtiene un icono para el tipo de notificación"""
        icons = {
            'price_alert': '💰',
            'system': '⚙️',
            'info': 'ℹ️',
            'warning': '⚠️',
        }
        return icons.get(self.notification_type, '📢')