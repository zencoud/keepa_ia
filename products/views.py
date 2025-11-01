from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from django.utils import timezone
import json
from .models import Product, PriceAlert, Notification
from .keepa_service import KeepaService
from .notifications import create_system_notification, get_user_unread_notifications_count
import logging

logger = logging.getLogger(__name__)


@login_required
@require_http_methods(["GET", "POST"])
def search_product_view(request):
    """
    Vista para buscar productos por ASIN
    GET: Muestra el formulario de búsqueda
    POST: Procesa la búsqueda y redirige al detalle del producto
    """
    if request.method == 'POST':
        asin = request.POST.get('asin', '').strip().upper()
        
        if not asin:
            messages.error(request, 'Por favor, ingresa un ASIN válido.')
            # Patrón POST-REDIRECT-GET: redirigir para que el mensaje se consuma
            return redirect('products:search')
        
        # Validar formato básico de ASIN (10 caracteres alfanuméricos)
        if len(asin) != 10 or not asin.isalnum():
            messages.error(request, 'El ASIN debe tener exactamente 10 caracteres alfanuméricos.')
            # Patrón POST-REDIRECT-GET: redirigir para que el mensaje se consuma
            return redirect('products:search')
        
        try:
            # Verificar si el producto ya existe en la BD
            existing_product = Product.objects.filter(asin=asin).first()
            
            if existing_product:
                messages.info(request, f'Producto {asin} encontrado en la base de datos.')
                return redirect('products:detail', asin=asin)
            
            # Consultar producto usando Keepa API
            try:
                keepa_service = KeepaService()
                product_data = keepa_service.query_product(asin)
                
                if not product_data:
                    messages.error(request, f'No se pudo encontrar el producto con ASIN: {asin}. Verifica que el ASIN sea correcto y que exista en Amazon.')
                    # Patrón POST-REDIRECT-GET: redirigir para que el mensaje se consuma
                    return redirect('products:search')
                
                # Verificar si el producto tiene al menos el ASIN
                if not product_data.get('asin'):
                    messages.error(request, 'El producto no tiene datos válidos. Por favor, verifica que el ASIN sea correcto.')
                    # Patrón POST-REDIRECT-GET: redirigir para que el mensaje se consuma
                    return redirect('products:search')
                
                # Verificar que el producto tenga título (requerido)
                if not product_data.get('title') or not product_data['title'].strip():
                    messages.error(request, 'No se pudo encontrar información completa del producto. El ASIN puede ser incorrecto o el producto puede no estar disponible en Amazon.')
                    # Patrón POST-REDIRECT-GET: redirigir para que el mensaje se consuma
                    return redirect('products:search')
                    
            except ValueError as e:
                messages.error(request, 'Error de configuración del sistema. Por favor, contacta al administrador.')
                logger.error(f"Error de configuración Keepa: {e}")
                # Patrón POST-REDIRECT-GET: redirigir para que el mensaje se consuma
                return redirect('products:search')
            
            # Guardar producto en la BD
            try:
                with transaction.atomic():
                    product = Product.objects.create(
                        asin=product_data['asin'],
                        title=product_data['title'],
                        brand=product_data.get('brand'),
                        image_url=product_data.get('image_url'),
                        color=product_data.get('color'),
                        binding=product_data.get('binding'),
                        availability_amazon=product_data.get('availability_amazon', 0),
                        categories=product_data.get('categories', []),
                        category_tree=product_data.get('category_tree', []),
                        current_price_new=product_data.get('current_price_new'),
                        current_price_amazon=product_data.get('current_price_amazon'),
                        current_price_used=product_data.get('current_price_used'),
                        sales_rank_current=product_data.get('sales_rank_current'),
                        rating=product_data.get('rating'),
                        review_count=product_data.get('review_count'),
                        price_history=product_data.get('price_history', {}),
                        rating_history=product_data.get('rating_history', {}),
                        sales_rank_history=product_data.get('sales_rank_history', {}),
                        reviews_data=product_data.get('reviews_data', {}),
                        queried_by=request.user
                    )
                    
                    messages.success(request, f'Producto consultado exitosamente.')
                    return redirect('products:detail', asin=asin)
            except Exception as db_error:
                logger.error(f"Error guardando producto {asin} en BD: {db_error}")
                # Si es error de campo requerido, dar mensaje específico
                if 'cannot be null' in str(db_error) or 'NOT NULL constraint' in str(db_error):
                    messages.error(request, 'No se encontró información completa del producto. El ASIN puede ser incorrecto o el producto puede no estar disponible en Amazon.')
                else:
                    messages.error(request, 'Hubo un problema al guardar el producto. Por favor, intenta de nuevo.')
                # Patrón POST-REDIRECT-GET: redirigir para que el mensaje se consuma
                return redirect('products:search')
                
        except Exception as e:
            logger.error(f"Error en búsqueda de producto {asin}: {e}")
            # Mensaje amigable sin exponer detalles técnicos
            if 'cannot be null' in str(e) or 'NOT NULL constraint' in str(e):
                messages.error(request, 'No se encontró información completa del producto. El ASIN puede ser incorrecto o el producto puede no estar disponible en Amazon.')
            else:
                messages.error(request, 'No se pudo consultar el producto. Por favor, verifica que el ASIN sea correcto y que el producto exista en Amazon.')
            # Patrón POST-REDIRECT-GET: redirigir para que el mensaje se consuma
            return redirect('products:search')
    
    return render(request, 'products/search.html')


@login_required
def product_detail_view(request, asin):
    """
    Vista para mostrar los detalles de un producto
    """
    product = get_object_or_404(Product, asin=asin)
    
    # Preparar datos para el template
    context = {
        'product': product,
        'price_new_display': product.get_price_display('new'),
        'price_amazon_display': product.get_price_display('amazon'),
        'price_used_display': product.get_price_display('used'),
        'rating_display': product.get_rating_display(),
        'sales_rank_display': product.get_sales_rank_display(),
        'price_history_json': json.dumps(product.price_history),
        'rating_history_json': json.dumps(product.rating_history),
        'sales_rank_history_json': json.dumps(product.sales_rank_history),
        'reviews_data_json': json.dumps(product.reviews_data),
    }
    
    return render(request, 'products/detail.html', context)


@login_required
def product_list_view(request):
    """
    Vista para listar productos consultados por el usuario
    """
    products = Product.objects.filter(queried_by=request.user).order_by('-last_updated')
    
    # Paginación
    paginator = Paginator(products, 10)  # 10 productos por página
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'products': page_obj,
    }
    
    return render(request, 'products/list.html', context)


@login_required
def refresh_product_view(request, asin):
    """
    Vista para actualizar los datos de un producto existente
    """
    product = get_object_or_404(Product, asin=asin)
    
    try:
        keepa_service = KeepaService()
        product_data = keepa_service.query_product(asin)
        
        if not product_data:
            messages.error(request, f'No se pudo actualizar el producto {asin}')
            return redirect('products:detail', asin=asin)
        
        # Actualizar campos del producto
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
        
        messages.success(request, f'Producto {asin} actualizado exitosamente.')
        # Redirigir a la lista de productos después de actualizar
        return redirect('products:list')
        
    except Exception as e:
        logger.error(f"Error actualizando producto {asin}: {e}")
        messages.error(request, f'Error al actualizar el producto: {str(e)}')
        # Redirigir a la lista de productos en caso de error
        return redirect('products:list')


@login_required
def delete_product_view(request, asin):
    """
    Vista para eliminar un producto de la lista del usuario
    """
    product = get_object_or_404(Product, asin=asin, queried_by=request.user)
    
    if request.method == 'POST':
        product.delete()
        messages.success(request, f'Producto {asin} eliminado exitosamente.')
        return redirect('products:list')
    
    context = {'product': product}
    return render(request, 'products/delete_confirm.html', context)


# ===== VISTAS PARA ALERTAS DE PRECIO =====

@login_required
@require_http_methods(["GET", "POST"])
def create_alert_view(request, asin):
    """
    Vista para crear una alerta de precio para un producto
    GET: Muestra el formulario
    POST: Procesa la creación de la alerta
    """
    product = get_object_or_404(Product, asin=asin)
    
    if request.method == 'POST':
        try:
            target_price = request.POST.get('target_price')
            price_type = request.POST.get('price_type', 'new')
            frequency = int(request.POST.get('frequency', 2))
            
            # Validaciones
            if not target_price:
                messages.error(request, 'El precio objetivo es requerido.')
                # Patrón POST-REDIRECT-GET: redirigir para que el mensaje se consuma
                return redirect('products:create_alert', asin=asin)
            
            try:
                target_price_cents = int(float(target_price) * 100)
            except (ValueError, TypeError):
                messages.error(request, 'El precio objetivo debe ser un número válido.')
                # Patrón POST-REDIRECT-GET: redirigir para que el mensaje se consuma
                return redirect('products:create_alert', asin=asin)
            
            if target_price_cents <= 0:
                messages.error(request, 'El precio objetivo debe ser mayor a 0.')
                # Patrón POST-REDIRECT-GET: redirigir para que el mensaje se consuma
                return redirect('products:create_alert', asin=asin)
            
            # Verificar si ya existe una alerta similar
            existing_alert = PriceAlert.objects.filter(
                user=request.user,
                product=product,
                price_type=price_type,
                target_price=target_price_cents,
                is_active=True
            ).first()
            
            if existing_alert:
                messages.warning(request, 'Ya tienes una alerta activa con estos parámetros.')
                return redirect('products:detail', asin=asin)
            
            # Obtener precio actual para validación
            current_price = None
            if price_type == 'new':
                current_price = product.current_price_new
            elif price_type == 'amazon':
                current_price = product.current_price_amazon
            elif price_type == 'used':
                current_price = product.current_price_used
            
            if current_price and target_price_cents >= current_price:
                messages.warning(
                    request, 
                    f'El precio objetivo (${target_price}) debe ser menor al precio actual '
                    f'(${current_price/100:.2f}) para que la alerta sea útil.'
                )
                # Patrón POST-REDIRECT-GET: redirigir para que el mensaje se consuma
                return redirect('products:create_alert', asin=asin)
            
            # Crear la alerta
            with transaction.atomic():
                alert = PriceAlert.objects.create(
                    user=request.user,
                    product=product,
                    target_price=target_price_cents,
                    price_type=price_type,
                    frequency=frequency
                )
                
                # Crear notificación de confirmación
                create_system_notification(
                    user=request.user,
                    title=f"Alerta de Precio Creada",
                    message=f"Se creó una alerta para {product.title[:50]}... cuando el precio {price_type} baje de ${target_price}",
                    notification_type='info',
                    alert=alert
                )
            
            messages.success(
                request, 
                f'Alerta de precio creada exitosamente. Te notificaremos cuando el precio '
                f'{alert.get_price_type_display().lower()} baje de ${target_price}.'
            )
            return redirect('products:detail', asin=asin)
            
        except Exception as e:
            logger.error(f"Error creando alerta para {asin}: {e}")
            messages.error(request, f'Error creando la alerta: {str(e)}')
            return render(request, 'products/create_alert.html', {'product': product})
    
    # GET: Mostrar formulario
    context = {
        'product': product,
        'price_types': PriceAlert.PRICE_TYPE_CHOICES,
        'frequencies': PriceAlert.FREQUENCY_CHOICES,
    }
    return render(request, 'products/create_alert.html', context)


@login_required
def list_alerts_view(request):
    """
    Vista para listar las alertas de precio del usuario
    """
    alerts = PriceAlert.objects.filter(user=request.user).order_by('-created_at')
    
    # Paginación
    paginator = Paginator(alerts, 10)  # 10 alertas por página
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'alerts': page_obj,
    }
    
    return render(request, 'products/alerts_list.html', context)


@login_required
def delete_alert_view(request, alert_id):
    """
    Vista para eliminar/desactivar una alerta de precio
    """
    alert = get_object_or_404(PriceAlert, id=alert_id, user=request.user)
    
    if request.method == 'POST':
        alert.is_active = False
        alert.save()
        
        messages.success(request, f'Alerta para {alert.product.title[:50]}... desactivada exitosamente.')
        return redirect('products:alerts_list')
    
    context = {'alert': alert}
    return render(request, 'products/delete_alert_confirm.html', context)


# ===== VISTAS PARA NOTIFICACIONES =====

@login_required
def notifications_view(request):
    """
    Vista para el centro de notificaciones del usuario
    """
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')
    
    # Paginación
    paginator = Paginator(notifications, 20)  # 20 notificaciones por página
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'notifications': page_obj,
    }
    
    return render(request, 'products/notifications_center.html', context)


@login_required
def mark_notification_read_view(request, notification_id):
    """
    Vista AJAX para marcar una notificación como leída
    """
    if request.method == 'POST':
        try:
            notification = Notification.objects.get(id=notification_id, user=request.user)
            notification.is_read = True
            notification.save()
            
            return JsonResponse({
                'success': True,
                'unread_count': get_user_unread_notifications_count(request.user)
            })
        except Notification.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Notificación no encontrada'})
    
    return JsonResponse({'success': False, 'error': 'Método no permitido'})


@login_required
def mark_all_notifications_read_view(request):
    """
    Vista para marcar todas las notificaciones como leídas
    """
    if request.method == 'POST':
        from .notifications import mark_all_notifications_as_read
        
        updated_count = mark_all_notifications_as_read(request.user)
        messages.success(request, f'{updated_count} notificaciones marcadas como leídas.')
        return redirect('products:notifications')
    
    return redirect('products:notifications')