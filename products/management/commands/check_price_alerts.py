from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
import logging
from products.models import PriceAlert, Product
from products.keepa_service import KeepaService
from products.notifications import send_price_alert_notification

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Verifica alertas de precio y envía notificaciones cuando se cumplan las condiciones'

    def add_arguments(self, parser):
        parser.add_argument(
            '--frequency',
            type=int,
            choices=[1, 2, 4],
            help='Verificar solo alertas con esta frecuencia (1, 2, o 4 veces al día)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Ejecutar sin enviar notificaciones (solo mostrar qué se haría)'
        )
        parser.add_argument(
            '--force-update',
            action='store_true',
            help='Forzar actualización de precios aunque no sea necesario'
        )

    def handle(self, *args, **options):
        frequency = options.get('frequency')
        dry_run = options.get('dry_run', False)
        force_update = options.get('force_update', False)
        
        self.stdout.write(
            self.style.SUCCESS(f'Iniciando verificación de alertas de precio...')
        )
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('MODO DRY-RUN: No se enviarán notificaciones reales')
            )
        
        # Obtener alertas activas
        alerts_query = PriceAlert.objects.filter(
            is_active=True,
            triggered=False
        )
        
        if frequency:
            alerts_query = alerts_query.filter(frequency=frequency)
            self.stdout.write(f'Verificando alertas con frecuencia: {frequency} veces al día')
        
        # Filtrar alertas que deben verificarse ahora
        alerts_to_check = []
        for alert in alerts_query:
            if alert.should_check_now() or force_update:
                alerts_to_check.append(alert)
        
        if not alerts_to_check:
            self.stdout.write(
                self.style.WARNING('No hay alertas que necesiten verificación en este momento')
            )
            return
        
        self.stdout.write(f'Verificando {len(alerts_to_check)} alertas...')
        
        # Agrupar alertas por producto para optimizar llamadas a Keepa
        products_to_update = {}
        for alert in alerts_to_check:
            asin = alert.product.asin
            if asin not in products_to_update:
                products_to_update[asin] = {
                    'product': alert.product,
                    'alerts': []
                }
            products_to_update[asin]['alerts'].append(alert)
        
        self.stdout.write(f'Actualizando {len(products_to_update)} productos únicos...')
        
        # Inicializar servicio de Keepa
        try:
            keepa_service = KeepaService()
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error inicializando Keepa service: {e}')
            )
            return
        
        alerts_triggered = 0
        errors = 0
        
        # Procesar cada producto
        for asin, data in products_to_update.items():
            product = data['product']
            alerts = data['alerts']
            
            self.stdout.write(f'Procesando {asin}: {product.title[:50]}...')
            
            try:
                # Verificar si necesitamos actualizar el producto
                needs_update = force_update
                if not needs_update:
                    # Actualizar si la última actualización fue hace más de 1 hora
                    if product.last_updated:
                        hours_since_update = (timezone.now() - product.last_updated).total_seconds() / 3600
                        needs_update = hours_since_update >= 1
                    else:
                        needs_update = True
                
                if needs_update:
                    self.stdout.write(f'  Actualizando precio desde Keepa...')
                    product_data = keepa_service.query_product(asin)
                    
                    if not product_data:
                        self.stdout.write(
                            self.style.WARNING(f'  No se pudo obtener datos actualizados para {asin}')
                        )
                        continue
                    
                    # Actualizar producto con nuevos datos
                    with transaction.atomic():
                        product.title = product_data['title']
                        product.brand = product_data.get('brand')
                        product.image_url = product_data.get('image_url')
                        product.color = product_data.get('color')
                        product.binding = product_data.get('binding')
                        product.availability_amazon = product_data.get('availability_amazon', 0)
                        product.categories = product_data.get('categories', [])
                        product.category_tree = product_data.get('category_tree', [])
                        product.current_price_new = product_data.get('current_price_new')
                        product.current_price_amazon = product_data.get('current_price_amazon')
                        product.current_price_used = product_data.get('current_price_used')
                        product.sales_rank_current = product_data.get('sales_rank_current')
                        product.rating = product_data.get('rating')
                        product.review_count = product_data.get('review_count')
                        product.price_history = product_data.get('price_history', {})
                        product.rating_history = product_data.get('rating_history', {})
                        product.sales_rank_history = product_data.get('sales_rank_history', {})
                        product.reviews_data = product_data.get('reviews_data', {})
                        product.save()
                    
                    self.stdout.write(f'  Producto actualizado exitosamente')
                else:
                    self.stdout.write(f'  Usando precio actual (actualizado hace menos de 1 hora)')
                
                # Verificar cada alerta para este producto
                for alert in alerts:
                    try:
                        # Obtener precio actual según el tipo de alerta
                        current_price = None
                        if alert.price_type == 'new':
                            current_price = product.current_price_new
                        elif alert.price_type == 'amazon':
                            current_price = product.current_price_amazon
                        elif alert.price_type == 'used':
                            current_price = product.current_price_used
                        
                        if current_price is None:
                            self.stdout.write(
                                self.style.WARNING(f'  Alerta {alert.id}: No hay precio {alert.price_type} disponible')
                            )
                            continue
                        
                        # Verificar si se cumple la condición de la alerta
                        if current_price <= alert.target_price:
                            self.stdout.write(
                                self.style.SUCCESS(
                                    f'  🎯 ALERTA DISPARADA: {alert.user.username} - '
                                    f'Precio actual: ${current_price/100:.2f} <= '
                                    f'Objetivo: ${alert.target_price/100:.2f}'
                                )
                            )
                            
                            if not dry_run:
                                # Enviar notificación
                                success = send_price_alert_notification(alert, current_price)
                                if success:
                                    alerts_triggered += 1
                                    self.stdout.write(f'    ✅ Notificación enviada')
                                else:
                                    errors += 1
                                    self.stdout.write(f'    ❌ Error enviando notificación')
                            else:
                                alerts_triggered += 1
                                self.stdout.write(f'    [DRY-RUN] Notificación se enviaría aquí')
                        else:
                            self.stdout.write(
                                f'  Alerta {alert.id}: Precio actual ${current_price/100:.2f} > '
                                f'Objetivo ${alert.target_price/100:.2f} (no se dispara)'
                            )
                        
                        # Actualizar timestamp de verificación
                        alert.last_checked = timezone.now()
                        alert.save()
                        
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(f'  Error procesando alerta {alert.id}: {e}')
                        )
                        errors += 1
                        logger.error(f"Error procesando alerta {alert.id}: {e}")
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error procesando producto {asin}: {e}')
                )
                errors += 1
                logger.error(f"Error procesando producto {asin}: {e}")
        
        # Resumen final
        self.stdout.write('\n' + '='*50)
        self.stdout.write('RESUMEN DE VERIFICACIÓN:')
        self.stdout.write(f'  Alertas verificadas: {len(alerts_to_check)}')
        self.stdout.write(f'  Alertas disparadas: {alerts_triggered}')
        self.stdout.write(f'  Errores: {errors}')
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('MODO DRY-RUN: No se enviaron notificaciones reales')
            )
        
        if alerts_triggered > 0:
            self.stdout.write(
                self.style.SUCCESS(f'✅ {alerts_triggered} alertas disparadas exitosamente')
            )
        
        if errors > 0:
            self.stdout.write(
                self.style.ERROR(f'❌ {errors} errores encontrados')
            )
        
        self.stdout.write(
            self.style.SUCCESS('Verificación de alertas completada')
        )
