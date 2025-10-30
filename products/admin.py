from django.contrib import admin
from .models import Product, PriceAlert, Notification

# Register your models here.

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('asin', 'title', 'brand', 'current_price_new', 'rating', 'sales_rank_current', 'last_updated', 'queried_by')
    list_filter = ('brand', 'binding', 'availability_amazon', 'last_updated', 'queried_by')
    search_fields = ('asin', 'title', 'brand')
    readonly_fields = ('asin', 'created_at', 'last_updated')
    ordering = ('-last_updated',)
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('asin', 'title', 'brand', 'image_url', 'color', 'binding')
        }),
        ('Disponibilidad', {
            'fields': ('availability_amazon', 'categories', 'category_tree')
        }),
        ('Precios Actuales', {
            'fields': ('current_price_new', 'current_price_amazon', 'current_price_used')
        }),
        ('Métricas', {
            'fields': ('sales_rank_current', 'rating', 'review_count')
        }),
        ('Historiales', {
            'fields': ('price_history', 'rating_history', 'sales_rank_history', 'reviews_data'),
            'classes': ('collapse',)
        }),
        ('Metadatos', {
            'fields': ('queried_by', 'created_at', 'last_updated'),
            'classes': ('collapse',)
        })
    )


@admin.register(PriceAlert)
class PriceAlertAdmin(admin.ModelAdmin):
    list_display = ('user', 'product', 'price_type', 'target_price_display', 'frequency', 'is_active', 'triggered', 'created_at')
    list_filter = ('price_type', 'frequency', 'is_active', 'triggered', 'created_at', 'user')
    search_fields = ('user__username', 'product__asin', 'product__title')
    readonly_fields = ('created_at', 'triggered_at', 'last_checked')
    ordering = ('-created_at',)
    
    fieldsets = (
        ('Información de la Alerta', {
            'fields': ('user', 'product', 'price_type', 'target_price', 'frequency')
        }),
        ('Estado', {
            'fields': ('is_active', 'triggered', 'triggered_at')
        }),
        ('Metadatos', {
            'fields': ('created_at', 'last_checked'),
            'classes': ('collapse',)
        })
    )
    
    def target_price_display(self, obj):
        return f"${obj.get_target_price_display()}"
    target_price_display.short_description = 'Precio Objetivo'


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'title', 'notification_type', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read', 'created_at', 'user')
    search_fields = ('user__username', 'title', 'message')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)
    
    fieldsets = (
        ('Información de la Notificación', {
            'fields': ('user', 'alert', 'notification_type', 'title', 'message')
        }),
        ('Estado', {
            'fields': ('is_read',)
        }),
        ('Metadatos', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        })
    )
