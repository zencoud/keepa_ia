from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal


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