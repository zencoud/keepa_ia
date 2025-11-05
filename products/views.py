from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta, datetime
from io import StringIO
from typing import Dict, Any, Optional
import json
from .models import Product, PriceAlert, Notification, BestSellerSearch
from .keepa_service import KeepaService
from .openai_service import OpenAIService
from .document_generator import DocumentGenerator
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
    
    # Breadcrumbs
    breadcrumbs = [
        {'text': 'Inicio', 'url': '/dashboard/'},
        {'text': 'Productos', 'url': '/products/list/'},
        {'text': 'Buscar Producto'},
    ]
    
    context = {
        'breadcrumbs': breadcrumbs,
    }
    
    return render(request, 'products/search.html', context)


@login_required
def product_detail_view(request, asin):
    """
    Vista para mostrar los detalles de un producto
    Si el producto no existe en la BD, intenta obtenerlo de Keepa API automáticamente
    """
    asin = asin.upper().strip()
    
    # Intentar obtener el producto de la BD
    try:
        product = Product.objects.get(asin=asin)
    except Product.DoesNotExist:
        # El producto no existe, intentar obtenerlo de Keepa API
        logger.info(f"Producto {asin} no encontrado en BD, intentando obtenerlo de Keepa API")
        
        try:
            keepa_service = KeepaService()
            product_data = keepa_service.query_product(asin)
            
            if not product_data or not product_data.get('asin'):
                logger.warning(f"No se pudo obtener el producto {asin} de Keepa API")
                from django.http import Http404
                raise Http404(f"Producto con ASIN {asin} no encontrado")
            
            # Guardar el producto en la BD
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
                    messages.success(request, f'Producto {asin} obtenido exitosamente.')
                    logger.info(f"Producto {asin} guardado en BD exitosamente")
            except Exception as db_error:
                logger.error(f"Error guardando producto {asin} en BD después de obtenerlo de Keepa: {db_error}")
                # Aún así intentar mostrar el producto con los datos obtenidos
                # Crear un objeto producto temporal para el template
                from django.http import Http404
                raise Http404(f"No se pudo guardar el producto {asin} en la base de datos")
                
        except ValueError as e:
            logger.error(f"Error de configuración Keepa al obtener producto {asin}: {e}")
            from django.http import Http404
            raise Http404(f"Error de configuración al obtener el producto {asin}")
        except Exception as e:
            logger.error(f"Error obteniendo producto {asin} de Keepa API: {e}")
            from django.http import Http404
            raise Http404(f"Producto con ASIN {asin} no encontrado")
    
    # Breadcrumbs
    breadcrumbs = [
        {'text': 'Inicio', 'url': '/dashboard/'},
        {'text': 'Productos', 'url': '/products/list/'},
        {'text': product.title[:50] + '...' if len(product.title) > 50 else product.title},
    ]
    
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
        'breadcrumbs': breadcrumbs,
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
    
    # Breadcrumbs
    breadcrumbs = [
        {'text': 'Inicio', 'url': '/dashboard/'},
        {'text': 'Productos'},
    ]
    
    context = {
        'page_obj': page_obj,
        'products': page_obj,
        'breadcrumbs': breadcrumbs,
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
        # Redirigir al detalle del producto después de actualizar
        return redirect('products:detail', asin=asin)
        
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
    
    # Breadcrumbs
    breadcrumbs = [
        {'text': 'Inicio', 'url': '/dashboard/'},
        {'text': 'Productos', 'url': '/products/list/'},
        {'text': f'Eliminar {product.asin}'},
    ]
    
    context = {
        'product': product,
        'breadcrumbs': breadcrumbs,
    }
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
    breadcrumbs = [
        {'text': 'Inicio', 'url': '/dashboard/'},
        {'text': 'Productos', 'url': '/products/list/'},
        {'text': product.title[:30] + '...' if len(product.title) > 30 else product.title, 'url': f'/products/detail/{product.asin}/'},
        {'text': 'Crear Alerta'},
    ]
    
    context = {
        'product': product,
        'price_types': PriceAlert.PRICE_TYPE_CHOICES,
        'frequencies': PriceAlert.FREQUENCY_CHOICES,
        'price_new_display': product.get_price_display('new'),
        'price_amazon_display': product.get_price_display('amazon'),
        'price_used_display': product.get_price_display('used'),
        'breadcrumbs': breadcrumbs,
    }
    return render(request, 'products/create_alert.html', context)


@login_required
def list_alerts_view(request):
    """
    Vista para listar las alertas de precio del usuario
    """
    alerts = PriceAlert.objects.filter(user=request.user).select_related('product').order_by('-created_at')
    
    active_alerts_count = alerts.filter(is_active=True).count()
    total_alerts_count = alerts.count()
    
    # Breadcrumbs
    breadcrumbs = [
        {'text': 'Inicio', 'url': '/dashboard/'},
        {'text': 'Alertas de Precio'},
    ]
    
    context = {
        'alerts': alerts,
        'active_alerts_count': active_alerts_count,
        'total_alerts_count': total_alerts_count,
        'breadcrumbs': breadcrumbs,
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
    
    breadcrumbs = [
        {'text': 'Inicio', 'url': '/dashboard/'},
        {'text': 'Alertas', 'url': '/products/alerts/'},
        {'text': 'Eliminar Alerta'},
    ]
    
    context = {
        'alert': alert,
        'breadcrumbs': breadcrumbs,
    }
    return render(request, 'products/delete_alert_confirm.html', context)


# ===== VISTAS PARA NOTIFICACIONES =====

@login_required
def notifications_view(request):
    """
    Vista para el centro de notificaciones del usuario
    """
    notifications = Notification.objects.filter(user=request.user).select_related('alert__product').order_by('-created_at')
    
    # Estadísticas
    total_count = notifications.count()
    unread_count = notifications.filter(is_read=False).count()
    read_count = notifications.filter(is_read=True).count()
    one_day_ago = timezone.now() - timedelta(days=1)
    recent_count = notifications.filter(created_at__gte=one_day_ago).count()
    
    # Paginación
    paginator = Paginator(notifications, 15)  # 15 notificaciones por página
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Breadcrumbs
    breadcrumbs = [
        {'text': 'Inicio', 'url': '/dashboard/'},
        {'text': 'Notificaciones'},
    ]
    
    context = {
        'page_obj': page_obj,
        'notifications': page_obj,
        'total_count': total_count,
        'unread_count': unread_count,
        'read_count': read_count,
        'recent_count': recent_count,
        'breadcrumbs': breadcrumbs,
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


@login_required
@require_http_methods(["POST"])
def detect_document_intent_view(request):
    """
    Vista AJAX para detectar intención de generar documento usando IA
    """
    try:
        data = json.loads(request.body)
        user_message = data.get('message', '').strip()
        
        if not user_message:
            return JsonResponse({
                'success': False,
                'error': 'El mensaje no puede estar vacío'
            }, status=400)
        
        # Detectar intención con OpenAI
        try:
            openai_service = OpenAIService()
            intent_result = openai_service.detect_document_intent(user_message)
            
            if intent_result:
                logger.info(f"Intención de documento detectada para usuario {request.user.username}")
                return JsonResponse({
                    'success': True,
                    'intent': intent_result
                })
            else:
                return JsonResponse({
                    'success': True,
                    'intent': None
                })
                
        except ValueError as e:
            logger.error(f"OpenAI no configurado: {e}")
            return JsonResponse({
                'success': False,
                'error': 'El servicio de IA no está disponible.'
            }, status=500)
            
        except Exception as e:
            logger.error(f"Error detectando intención: {e}")
            return JsonResponse({
                'success': False,
                'error': 'Error al procesar la solicitud'
            }, status=500)
            
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Error en el formato de los datos'
        }, status=400)
        
    except Exception as e:
        logger.error(f"Error en detect_document_intent_view: {e}")
        return JsonResponse({
            'success': False,
            'error': 'Error procesando la solicitud'
        }, status=500)


def ensure_product_in_db(asin: str, user, keepa_service: KeepaService = None) -> Optional[Product]:
    """
    Asegura que un producto esté en la BD. Si no está, lo obtiene desde Keepa y lo guarda.
    Similar a la lógica de product_detail_view pero reutilizable.
    
    Args:
        asin: ASIN del producto
        user: Usuario que realiza la consulta
        keepa_service: Instancia de KeepaService (opcional, se crea si no se proporciona)
        
    Returns:
        Product si se obtiene exitosamente, None si hay error
    """
    asin = asin.upper().strip()
    
    # Verificar si ya existe en BD
    try:
        product = Product.objects.get(asin=asin)
        logger.info(f"[ENSURE_PRODUCT] Producto {asin} ya existe en BD")
        return product
    except Product.DoesNotExist:
        pass
    
    # No existe, obtenerlo desde Keepa
    logger.info(f"[ENSURE_PRODUCT] Producto {asin} no encontrado en BD, obteniendo desde Keepa...")
    
    try:
        if not keepa_service:
            keepa_service = KeepaService()
        
        # Obtener producto con historial completo (como en search_product_view)
        product_data = keepa_service.query_product(asin)
        
        if not product_data or not product_data.get('asin'):
            logger.warning(f"[ENSURE_PRODUCT] No se pudo obtener producto {asin} de Keepa")
            return None
        
        # Verificar que tenga título
        if not product_data.get('title') or not product_data['title'].strip():
            logger.warning(f"[ENSURE_PRODUCT] Producto {asin} sin título válido")
            return None
        
        # Guardar en BD
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
                    queried_by=user
                )
                
                logger.info(f"[ENSURE_PRODUCT] Producto {asin} guardado exitosamente en BD")
                return product
                
        except Exception as db_error:
            logger.error(f"[ENSURE_PRODUCT] Error guardando producto {asin} en BD: {db_error}")
            return None
            
    except ValueError as e:
        logger.error(f"[ENSURE_PRODUCT] Error de configuración Keepa: {e}")
        return None
    except Exception as e:
        logger.error(f"[ENSURE_PRODUCT] Error obteniendo producto {asin} de Keepa: {e}")
        return None


def find_product_by_name(product_name: str, user) -> Optional[Product]:
    """
    Busca un producto por nombre en la base de datos
    
    Args:
        product_name: Nombre del producto a buscar
        user: Usuario que realiza la búsqueda
        
    Returns:
        Product si se encuentra, None si no
    """
    if not product_name or not product_name.strip():
        return None
    
    product_name_clean = product_name.strip().lower()
    
    # Buscar productos que contengan el nombre en el título
    # Primero intentar búsqueda exacta (case insensitive)
    products = Product.objects.filter(
        title__icontains=product_name_clean
    ).order_by('-last_updated')[:10]  # Limitar a 10 resultados
    
    if not products.exists():
        # Si no hay resultados, intentar búsqueda por palabras clave
        # Dividir el nombre en palabras y buscar productos que contengan todas o algunas
        keywords = product_name_clean.split()
        if len(keywords) > 1:
            # Buscar productos que contengan al menos algunas de las palabras clave
            from django.db.models import Q
            query = Q()
            for keyword in keywords:
                if len(keyword) > 2:  # Ignorar palabras muy cortas
                    query |= Q(title__icontains=keyword)
            
            if query:
                products = Product.objects.filter(query).order_by('-last_updated')[:10]
    
    # Si hay resultados, intentar encontrar el mejor match
    if products.exists():
        # Priorizar productos con coincidencias exactas o muy cercanas
        best_match = None
        best_score = 0
        
        for product in products:
            title_lower = product.title.lower()
            score = 0
            
            # Calcular score de coincidencia
            if product_name_clean in title_lower:
                score += 100
            
            # Bonus por palabras clave coincidentes
            keywords = product_name_clean.split()
            for keyword in keywords:
                if len(keyword) > 2 and keyword in title_lower:
                    score += 10
            
            # Bonus por longitud similar
            length_diff = abs(len(title_lower) - len(product_name_clean))
            score -= length_diff / 10
            
            if score > best_score:
                best_score = score
                best_match = product
        
        if best_match and best_score > 50:  # Threshold mínimo
            logger.info(f"[PRODUCT_SEARCH] Producto encontrado por nombre: '{product_name}' -> ASIN: {best_match.asin} (score: {best_score})")
            return best_match
    
    logger.info(f"[PRODUCT_SEARCH] No se encontró producto por nombre: '{product_name}'")
    return None


@login_required
@require_http_methods(["POST"])
def ai_chat_view(request):
    """
    Vista AJAX para chat con IA usando datos completos de Keepa
    Maneja tanto preguntas sobre productos como sobre best sellers
    Ahora detecta automáticamente productos mencionados en el mensaje
    """
    try:
        # Parsear datos del request
        data = json.loads(request.body)
        user_message = data.get('message', '').strip()
        asin = data.get('asin')  # Opcional, puede ser None
        conversation_history = data.get('history', [])
        
        if not user_message:
            return JsonResponse({
                'success': False,
                'error': 'El mensaje no puede estar vacío'
            }, status=400)
        
        # PRIMERO: Detectar si es una solicitud de best sellers
        try:
            openai_service = OpenAIService()
            best_sellers_intent = openai_service.detect_best_sellers_intent(user_message)
            
            if best_sellers_intent and best_sellers_intent.get('intent') == 'best_sellers':
                logger.info(f"[BEST_SELLERS] Intención detectada: {best_sellers_intent}")
                return handle_best_sellers_request(request, user_message, best_sellers_intent)
            
        except ValueError as e:
            logger.warning(f"OpenAI no configurado para detección de intención: {e}")
            # Continuar con chat normal si OpenAI no está configurado
        except Exception as e:
            logger.warning(f"Error detectando intención de best sellers: {e}")
            # Continuar con chat normal si hay error en la detección
        
        # SEGUNDO: Si no hay ASIN pero el mensaje menciona un producto, intentar encontrarlo
        if not asin:
            try:
                if 'openai_service' not in locals():
                    openai_service = OpenAIService()
                
                # Detectar si el mensaje menciona un producto específico
                product_mention = openai_service.detect_product_mention(user_message)
                
                if product_mention and product_mention.get('product_name'):
                    product_name = product_mention.get('product_name')
                    logger.info(f"[PRODUCT_DETECTION] Producto mencionado detectado: '{product_name}'")
                    
                    # Buscar el producto en la base de datos
                    found_product = find_product_by_name(product_name, request.user)
                    
                    if found_product:
                        # Usar el ASIN del producto encontrado
                        asin = found_product.asin
                        logger.info(f"[PRODUCT_DETECTION] Producto encontrado en BD: ASIN {asin}")
                    else:
                        # Si no está en BD, intentar buscar en best sellers recientes del usuario
                        # Esto es útil cuando el usuario pregunta sobre un producto de una lista de best sellers
                        logger.info(f"[PRODUCT_DETECTION] Producto '{product_name}' no encontrado en BD. Buscando en best sellers recientes...")
                        
                        try:
                            # Buscar en las búsquedas de best sellers recientes del usuario
                            # y ver si hay algún producto que coincida
                            recent_searches = BestSellerSearch.objects.filter(
                                user=request.user
                            ).order_by('-created_at')[:5]  # Últimas 5 búsquedas
                            
                            # Esta es una búsqueda limitada - en el futuro se podría mejorar
                            # guardando los ASINs de best sellers en una tabla temporal
                            logger.info(f"[PRODUCT_DETECTION] Revisando {recent_searches.count()} búsquedas recientes de best sellers")
                            
                            # Nota: Keepa no tiene búsqueda directa por nombre, necesitaríamos ASIN
                            # Por ahora, solo logueamos que no se encontró
                            logger.warning(f"[PRODUCT_DETECTION] No se pudo buscar '{product_name}' en Keepa directamente (requiere ASIN). El producto debe estar en la BD para ser encontrado automáticamente.")
                        except Exception as e:
                            logger.warning(f"[PRODUCT_DETECTION] Error buscando producto en best sellers recientes: {e}")
                
            except ValueError as e:
                logger.warning(f"OpenAI no configurado para detección de productos: {e}")
                # Continuar sin detección de productos
            except Exception as e:
                logger.warning(f"Error detectando producto mencionado: {e}")
                # Continuar sin detección de productos
        
        # Si no es solicitud de best sellers, continuar con el chat normal
        # Preparar datos del producto si hay ASIN
        product_data = None
        if asin:
            try:
                product = Product.objects.get(asin=asin)
                product_data = {
                    'title': product.title,
                    'brand': product.brand,
                    'categories': product.categories,
                    'asin': product.asin,
                    # PRECIOS
                    'price_history': product.price_history,
                    'current_price_new': product.current_price_new,
                    'current_price_amazon': product.current_price_amazon,
                    'current_price_used': product.current_price_used,
                    # VENTAS
                    'sales_rank_current': product.sales_rank_current,
                    'sales_rank_history': product.sales_rank_history,
                    # REPUTACIÓN
                    'rating': product.rating,
                    'review_count': product.review_count,
                    'rating_history': product.rating_history,
                    'reviews_data': product.reviews_data,
                }
            except Product.DoesNotExist:
                logger.warning(f"Producto {asin} no encontrado para chat")
                # Continuar sin producto_data
        
        # Generar respuesta con OpenAI
        try:
            if 'openai_service' not in locals():
                openai_service = OpenAIService()
            
            response_text = openai_service.chat_with_product(
                user_message=user_message,
                conversation_history=conversation_history,
                product_data=product_data
            )
            
            logger.info(f"Respuesta de chat generada para usuario {request.user.username}")
            
            return JsonResponse({
                'success': True,
                'response': response_text,
                'timestamp': timezone.now().isoformat()
            })
            
        except ValueError as e:
            logger.error(f"OpenAI no configurado: {e}")
            return JsonResponse({
                'success': False,
                'error': 'El servicio de IA no está disponible en este momento.'
            }, status=500)
            
        except Exception as e:
            logger.error(f"Error generando respuesta de chat: {e}")
            return JsonResponse({
                'success': False,
                'error': 'Error al procesar tu pregunta. Por favor intenta de nuevo.'
            }, status=500)
            
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Error en el formato de los datos'
        }, status=400)
        
    except Exception as e:
        logger.error(f"Error en ai_chat_view: {e}")
        return JsonResponse({
            'success': False,
            'error': 'Error procesando la solicitud'
        }, status=500)


def handle_best_sellers_request(request, user_message: str, intent_data: Dict[str, Any]) -> JsonResponse:
    """
    Maneja solicitudes de best sellers desde el chat
    
    Args:
        request: HttpRequest
        user_message: Mensaje original del usuario
        intent_data: Dict con información de la intención detectada
        
    Returns:
        JsonResponse con la respuesta de best sellers
    """
    try:
        category_query = intent_data.get('category_query')
        
        # Si no hay categoría, pedir al usuario que especifique
        if not category_query:
            return JsonResponse({
                'success': True,
                'response': 'Para mostrarte los best sellers, necesito que especifiques una categoría. Por ejemplo: "muéstrame best sellers de laptops" o "más vendidos de libros". ¿De qué categoría te gustaría ver los best sellers?',
                'timestamp': timezone.now().isoformat()
            })
        
        # Buscar categorías usando KeepaService
        try:
            keepa_service = KeepaService()
            categories = keepa_service.search_categories(category_query)
            
            if not categories or len(categories) == 0:
                return JsonResponse({
                    'success': True,
                    'response': f'No encontré categorías que coincidan con "{category_query}". Por favor, intenta con otro término de búsqueda o verifica la ortografía.',
                    'timestamp': timezone.now().isoformat()
                })
            
            # Usar la primera categoría encontrada (la más relevante)
            selected_category = categories[0]
            category_id = selected_category.get('id')
            category_name = selected_category.get('name') or selected_category.get('contextFreeName', category_query)
            
            logger.info(f"[BEST_SELLERS] Categoría seleccionada: {category_name} (ID: {category_id})")
            
            # Obtener best sellers
            asins = keepa_service.get_best_sellers(category_id)
            
            if not asins or len(asins) == 0:
                return JsonResponse({
                    'success': True,
                    'response': f'No encontré best sellers para la categoría "{category_name}". Intenta con otra categoría.',
                    'timestamp': timezone.now().isoformat()
                })
            
            # Limitar a top 20 para evitar respuestas muy largas
            asins_to_fetch = asins[:20]
            
            # Asegurar que todos los productos estén en BD
            # Esto permite que luego se puedan consultar con información completa
            logger.info(f"[BEST_SELLERS] Asegurando que {len(asins_to_fetch)} productos estén en BD...")
            products_in_db = []
            for asin in asins_to_fetch:
                try:
                    product = ensure_product_in_db(asin, request.user, keepa_service)
                    if product:
                        products_in_db.append(product)
                except Exception as e:
                    logger.warning(f"[BEST_SELLERS] Error asegurando producto {asin} en BD: {e}")
                    continue
            
            logger.info(f"[BEST_SELLERS] {len(products_in_db)} productos asegurados en BD")
            
            # Consultar información básica de los productos para la respuesta del chat
            # (aunque ya están en BD, necesitamos datos formateados para OpenAI)
            try:
                products_raw = keepa_service.api.query(
                    asins_to_fetch,
                    history=False,
                    stats=90,  # Necesitamos stats para rating y review_count
                    rating=True
                )
            except Exception as e:
                logger.error(f"Error consultando productos best sellers: {e}")
                return JsonResponse({
                    'success': True,
                    'response': f'Encontré {len(asins)} best sellers para "{category_name}", pero hubo un problema obteniendo los detalles. Por favor, intenta de nuevo.',
                    'timestamp': timezone.now().isoformat()
                })
            
            # Parsear información básica de productos
            best_sellers_data = []
            for product_raw in products_raw:
                try:
                    # Extraer datos básicos
                    product_basic = {
                        'asin': product_raw.get('asin', ''),
                        'title': product_raw.get('title', ''),
                        'brand': product_raw.get('brand', ''),
                        'image_url': keepa_service._extract_image_url(product_raw),
                        'rating': None,
                        'review_count': None,
                        'sales_rank_current': None,
                        'current_price_new': None,
                        'current_price_amazon': None,
                    }
                    
                    # Extraer datos desde stats
                    stats = product_raw.get('stats', {})
                    if stats:
                        current = stats.get('current', [])
                        if current and len(current) > 0:
                            # Rating (índice 16)
                            if len(current) > 16:
                                rating = current[16]
                                if rating is not None and rating > 0:
                                    product_basic['rating'] = round(rating / 10.0, 1)
                            # Review count (índice 17)
                            if len(current) > 17:
                                review_count = current[17]
                                if review_count is not None and review_count >= 0:
                                    product_basic['review_count'] = int(review_count)
                            # Sales rank (índice 3)
                            if len(current) > 3:
                                sales_rank = current[3]
                                if sales_rank is not None and sales_rank > 0:
                                    product_basic['sales_rank_current'] = int(sales_rank)
                    
                    # Extraer precios
                    data = product_raw.get('data', {})
                    if data:
                        product_basic['current_price_new'] = keepa_service._get_latest_price(data.get('NEW', []))
                        product_basic['current_price_amazon'] = keepa_service._get_latest_price(data.get('AMAZON', []))
                    
                    if product_basic['asin'] and product_basic['title']:
                        best_sellers_data.append(product_basic)
                        
                except Exception as e:
                    logger.warning(f"Error parseando producto best seller: {e}")
                    continue
            
            if not best_sellers_data:
                return JsonResponse({
                    'success': True,
                    'response': f'Encontré best sellers para "{category_name}", pero no pude obtener los detalles de los productos. Por favor, intenta de nuevo.',
                    'timestamp': timezone.now().isoformat()
                })
            
            # Generar respuesta usando OpenAI
            try:
                openai_service = OpenAIService()
                response_text = openai_service.chat_with_best_sellers(
                    user_message=user_message,
                    best_sellers_data=best_sellers_data,
                    category_name=category_name
                )
                
                logger.info(f"[BEST_SELLERS] Respuesta generada exitosamente para categoría: {category_name}")
                
                return JsonResponse({
                    'success': True,
                    'response': response_text,
                    'timestamp': timezone.now().isoformat()
                })
                
            except Exception as e:
                logger.error(f"Error generando respuesta de best sellers con OpenAI: {e}")
                # Fallback: respuesta básica
                openai_service = OpenAIService()
                response_text = openai_service._build_fallback_best_sellers_response(
                    best_sellers_data,
                    category_name
                )
                return JsonResponse({
                    'success': True,
                    'response': response_text,
                    'timestamp': timezone.now().isoformat()
                })
            
        except Exception as e:
            logger.error(f"Error manejando solicitud de best sellers: {e}")
            return JsonResponse({
                'success': True,
                'response': 'Hubo un problema buscando los best sellers. Por favor, intenta de nuevo o verifica que la categoría sea correcta.',
                'timestamp': timezone.now().isoformat()
            })
            
    except Exception as e:
        logger.error(f"Error en handle_best_sellers_request: {e}")
        return JsonResponse({
            'success': False,
            'error': 'Error procesando la solicitud de best sellers'
        }, status=500)


@login_required
@require_http_methods(["POST"])
def generate_ai_summary_view(request, asin):
    """
    Vista AJAX para generar resumen de IA bajo demanda
    """
    try:
        product = get_object_or_404(Product, asin=asin)
        
        # Preparar datos COMPLETOS del producto para OpenAI
        product_data = {
            'title': product.title,
            'brand': product.brand,
            'categories': product.categories,
            'asin': product.asin,
            # PRECIOS - Historial completo
            'price_history': product.price_history,
            'current_price_new': product.current_price_new,
            'current_price_amazon': product.current_price_amazon,
            'current_price_used': product.current_price_used,
            # VENTAS - Actual + Historial
            'sales_rank_current': product.sales_rank_current,
            'sales_rank_history': product.sales_rank_history,
            # REPUTACIÓN - Actual + Historiales
            'rating': product.rating,
            'review_count': product.review_count,
            'rating_history': product.rating_history,
            'reviews_data': product.reviews_data,
        }
        
        # Generar resumen con OpenAI
        try:
            openai_service = OpenAIService()
            ai_summary = openai_service.generate_price_summary(product_data)
            
            if ai_summary:
                # Guardar resumen en la base de datos con timestamp
                product.ai_summary = ai_summary
                product.ai_summary_generated_at = timezone.now()
                product.save()
                
                logger.info(f"Resumen de IA generado exitosamente para {asin}")
                
                return JsonResponse({
                    'success': True,
                    'summary': ai_summary,
                    'generated_at': product.ai_summary_generated_at.strftime('%d/%m/%Y %H:%M')
                })
            else:
                logger.warning(f"No se pudo generar resumen de IA para {asin}")
                return JsonResponse({
                    'success': False,
                    'error': 'No se pudo generar el resumen. Verifica que el producto tenga historial de precios.'
                }, status=400)
                
        except ValueError as e:
            logger.error(f"OpenAI no configurado: {e}")
            return JsonResponse({
                'success': False,
                'error': 'OpenAI no está configurado. Por favor, contacta al administrador.'
            }, status=500)
            
        except Exception as e:
            logger.error(f"Error generando resumen de IA para {asin}: {e}")
            return JsonResponse({
                'success': False,
                'error': f'Error al generar el resumen: {str(e)}'
            }, status=500)
            
    except Exception as e:
        logger.error(f"Error en generate_ai_summary_view para {asin}: {e}")
        return JsonResponse({
            'success': False,
            'error': 'Error procesando la solicitud'
        }, status=500)


@login_required
@require_http_methods(["POST"])
def generate_document_view(request):
    """
    Vista AJAX para generar documentos (PDF, CSV, TXT, Excel, JSON, Markdown)
    """
    try:
        # Parsear datos del request
        data = json.loads(request.body)
        asin = data.get('asin')
        format_type = data.get('format', 'pdf').lower()  # pdf, csv, txt, xlsx, json, md
        user_request = data.get('user_request')  # Solicitud específica del usuario
        
        if not asin:
            return JsonResponse({
                'success': False,
                'error': 'ASIN es requerido'
            }, status=400)
        
        # Validar formato - Solo soportamos PDF, Excel y TXT
        valid_formats = ['pdf', 'txt', 'xlsx']
        if format_type not in valid_formats:
            return JsonResponse({
                'success': False,
                'error': f'Formato no válido. Formatos soportados: PDF, Excel (xlsx) y TXT'
            }, status=400)
        
        try:
            product = Product.objects.get(asin=asin)
        except Product.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Producto no encontrado'
            }, status=404)
        
        # Preparar datos COMPLETOS del producto - ABSOLUTAMENTE TODOS LOS CAMPOS
        product_data = {
            # IDENTIFICACIÓN
            'asin': product.asin,
            'title': product.title,
            'brand': product.brand,
            
            # CLASIFICACIÓN
            'categories': product.categories,
            'category_tree': product.category_tree,
            'binding': product.binding,
            
            # VISUAL
            'image_url': product.image_url,
            'color': product.color,
            
            # DISPONIBILIDAD
            'availability_amazon': product.availability_amazon,
            
            # PRECIOS ACTUALES
            'current_price_new': product.current_price_new,
            'current_price_amazon': product.current_price_amazon,
            'current_price_used': product.current_price_used,
            
            # HISTORIAL COMPLETO DE PRECIOS (sin resumir)
            'price_history': product.price_history,
            
            # VENTAS Y POPULARIDAD
            'sales_rank_current': product.sales_rank_current,
            'sales_rank_history': product.sales_rank_history,
            
            # REPUTACIÓN Y CALIDAD
            'rating': product.rating,
            'review_count': product.review_count,
            'rating_history': product.rating_history,
            'reviews_data': product.reviews_data,
            
            # METADATA
            'last_updated': product.last_updated.isoformat() if product.last_updated else None,
            'created_at': product.created_at.isoformat() if product.created_at else None,
            'queried_by': product.queried_by.username if product.queried_by else None,
        }
        
        # FLUJO DE GENERACIÓN DE DOCUMENTO
        # Siempre generar análisis completo, con o sin user_request
        try:
            openai_service = OpenAIService()
            
            # Determinar la solicitud a usar
            if user_request:
                logger.info(f"[FLUJO] Generando documento con solicitud específica: '{user_request}'")
                # Usar la solicitud del usuario
                request_text = user_request
            else:
                logger.info(f"[FLUJO] Generando análisis completo (no hay user_request específico)")
                # Generar con solicitud de análisis completo por defecto
                request_text = "genera un análisis completo y detallado del producto con toda la información disponible incluyendo historiales completos"
            
            # Generar contenido con TODOS los datos disponibles
            logger.info(f"[FLUJO] Iniciando generación de contenido Markdown")
            markdown_content = openai_service.generate_document_content(product_data, user_request=request_text)
            content = markdown_content
            logger.info(f"[FLUJO] ✓ Contenido generado ({len(markdown_content)} caracteres)")
                
        except ValueError as e:
            # Error de configuración (OpenAI no configurado)
            logger.error(f"OpenAI no configurado: {e}")
            # Usar fallback mejorado que genera análisis completo
            logger.warning(f"[FLUJO] Usando análisis completo de fallback (OpenAI no disponible)")
            openai_service = OpenAIService()
            try:
                content = openai_service._get_fallback_markdown(product_data, user_request)
            except:
                # Si incluso el fallback falla, usar contenido mínimo
                content = f"# Análisis de Producto - Keepa AI\n\n## Información del Producto\n\n- **Título**: {product_data.get('title', 'N/A')}\n- **ASIN**: {product_data.get('asin', 'N/A')}\n- **Precio Actual**: ${product_data.get('current_price_new', 0) / 100:.2f}\n\n---\n*Generado por Keepa AI*"
                        
        except Exception as e:
            logger.error(f"[FLUJO] Error generando contenido: {e}")
            import traceback
            logger.error(f"[FLUJO] Traceback: {traceback.format_exc()}")
            # Usar fallback mejorado que genera análisis completo
            logger.warning(f"[FLUJO] Usando análisis completo de fallback debido a error")
            try:
                openai_service = OpenAIService()
                content = openai_service._get_fallback_markdown(product_data, user_request)
            except Exception as fallback_error:
                logger.error(f"[FLUJO] Error incluso en fallback: {fallback_error}")
                # Último recurso: contenido mínimo
                content = f"# Análisis de Producto - Keepa AI\n\n## Información del Producto\n\n- **Título**: {product_data.get('title', 'N/A')}\n- **ASIN**: {product_data.get('asin', 'N/A')}\n- **Precio Actual**: ${product_data.get('current_price_new', 0) / 100:.2f}\n\n---\n*Generado por Keepa AI*"
        
        # Generar documento en el formato solicitado
        try:
            doc_generator = DocumentGenerator()
            
            # Nombre del archivo
            safe_title = "".join(c for c in product.title[:30] if c.isalnum() or c in (' ', '-', '_')).strip()
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            if format_type == 'pdf':
                buffer = doc_generator.generate_pdf(content, product_data)
                filename = f"Keepa_Analysis_{safe_title}_{timestamp}.pdf"
                content_type = 'application/pdf'
                
            elif format_type == 'txt':
                buffer = doc_generator.generate_txt_from_markdown(content, product_data)
                filename = f"Keepa_Analysis_{safe_title}_{timestamp}.txt"
                content_type = 'text/plain'
                
            elif format_type == 'xlsx':
                buffer = doc_generator.generate_excel_from_markdown(content, product_data)
                filename = f"Keepa_Analysis_{safe_title}_{timestamp}.xlsx"
                content_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            
            # Crear respuesta con el archivo
            from django.http import HttpResponse
            response = HttpResponse(buffer.read(), content_type=content_type)
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            
            logger.info(f"Documento {format_type.upper()} generado exitosamente para {asin}")
            
            return response
            
        except Exception as e:
            logger.error(f"Error generando documento {format_type}: {e}")
            return JsonResponse({
                'success': False,
                'error': f'Error generando el documento: {str(e)}'
            }, status=500)
            
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Error en el formato de los datos'
        }, status=400)
        
    except Exception as e:
        logger.error(f"Error en generate_document_view: {e}")
        return JsonResponse({
            'success': False,
            'error': 'Error procesando la solicitud'
        }, status=500)


# ===== VISTAS PARA BEST SELLERS =====

@login_required
@require_http_methods(["GET"])
def search_categories_view(request):
    """
    Vista AJAX para buscar categorías por nombre
    GET: ?q=nombre_categoria
    """
    try:
        query = request.GET.get('q', '').strip()
        
        if not query:
            return JsonResponse({
                'success': False,
                'error': 'El parámetro "q" es requerido'
            }, status=400)
        
        try:
            keepa_service = KeepaService()
            categories = keepa_service.search_categories(query)
            
            # Limitar resultados a 10
            categories = categories[:10]
            
            return JsonResponse({
                'success': True,
                'categories': categories,
                'count': len(categories)
            })
            
        except ValueError as e:
            logger.error(f"Error de configuración Keepa: {e}")
            return JsonResponse({
                'success': False,
                'error': 'Error de configuración del sistema'
            }, status=500)
            
    except Exception as e:
        logger.error(f"Error en search_categories_view: {e}")
        return JsonResponse({
            'success': False,
            'error': 'Error procesando la solicitud'
        }, status=500)


@login_required
def best_sellers_view(request):
    """
    Vista principal para listar best sellers de una categoría
    GET: ?category_id=X&page=1
    """
    try:
        category_id = request.GET.get('category_id', '').strip()
        category_search = request.GET.get('category_search', '').strip()  # Nombre de búsqueda para contexto
        page_number = request.GET.get('page', 1)
        
        logger.info(f"best_sellers_view - category_id recibido: '{category_id}', category_search: '{category_search}'")
        
        category_name = category_search or None  # Usar category_search si está disponible
        products_data = []
        paginator = None
        page_obj = None
        results_count = 0
        
        # Permitir búsqueda global sin categoría: si hay category_search pero no category_id
        if category_search and not category_id:
            try:
                keepa_service = KeepaService()
                # Buscar categorías que coincidan con el término de búsqueda
                categories = keepa_service.search_categories(category_search)
                
                if categories and len(categories) > 0:
                    # Usar la primera categoría encontrada
                    selected_category = categories[0]
                    category_id = selected_category.get('id')
                    category_name = selected_category.get('name') or selected_category.get('contextFreeName', category_search)
                    logger.info(f"Búsqueda global: usando categoría '{category_name}' (ID: {category_id}) para término '{category_search}'")
                else:
                    messages.warning(request, f'No se encontraron categorías que coincidan con "{category_search}". Por favor, selecciona una categoría de la lista.')
            except Exception as e:
                logger.error(f"Error en búsqueda global: {e}")
                messages.error(request, f'Error al buscar categorías: {str(e)[:100]}')
        
        if category_id:
            # Validar que category_id sea numérico
            if not category_id.isdigit():
                messages.error(request, f'ID de categoría inválido: "{category_id}". El ID debe ser numérico.')
                logger.error(f"Category ID no es numérico: '{category_id}'")
                category_id = ''  # Limpiar para que no entre al bloque de búsqueda
            else:
                # category_id es válido, proceder con la búsqueda
                try:
                    keepa_service = KeepaService()
                    
                    logger.info(f"Buscando best sellers para category_id: '{category_id}'")
                    
                    # Obtener ASINs de best sellers
                    asins = keepa_service.get_best_sellers(category_id)
                    
                    logger.info(f"Best sellers obtenidos: {len(asins) if asins else 0} ASINs")
                    if asins:
                        logger.info(f"Primeros 5 ASINs obtenidos: {asins[:5]}")
                    
                    if not asins:
                        messages.warning(request, f'No se encontraron best sellers para la categoría seleccionada. Verifica que el ID de categoría sea válido y que existan productos en esa categoría.')
                        logger.warning(f"No se encontraron best sellers para category_id: '{category_id}'")
                    else:
                        # Asegurar que todos los productos estén en BD antes de mostrarlos
                        # Esto permite que luego se puedan consultar con información completa
                        asins_to_process = asins[:100]  # Limitar a 100 para no consumir demasiados tokens
                        logger.info(f"[BEST_SELLERS_VIEW] Asegurando que {len(asins_to_process)} productos estén en BD...")
                        
                        products_ensured = 0
                        for asin in asins_to_process:
                            try:
                                product = ensure_product_in_db(asin, request.user, keepa_service)
                                if product:
                                    products_ensured += 1
                            except Exception as e:
                                logger.warning(f"[BEST_SELLERS_VIEW] Error asegurando producto {asin} en BD: {e}")
                                continue
                        
                        logger.info(f"[BEST_SELLERS_VIEW] {products_ensured} productos asegurados en BD de {len(asins_to_process)}")
                        
                        # Consultar información básica de cada ASIN en batch
                        # Usar query sin historial completo para ahorrar tokens (ya están en BD con historial completo)
                        logger.info(f"Consultando información de {len(asins_to_process)} best sellers para mostrar")
                        
                        # Consultar productos en batch con stats para obtener rating y review count
                        products_raw = keepa_service.api.query(
                            asins_to_process,
                            history=False,  # Sin historial para ahorrar tokens (ya están guardados en BD)
                            stats=90,  # Con estadísticas para obtener rating y review count
                            rating=True  # Con rating para obtener información completa
                        )
                        
                        logger.info(f"Productos raw obtenidos de Keepa: {len(products_raw) if products_raw else 0}")
                        
                        # Contador de tipos de productos para debugging
                        binding_counts = {}
                        
                        # Parsear información básica de cada producto
                        for product_raw in products_raw:
                            try:
                                # Extraer información básica incluyendo binding para verificar tipo
                                product_basic = {
                                    'asin': product_raw.get('asin', ''),
                                    'title': product_raw.get('title', ''),
                                    'brand': product_raw.get('brand', ''),
                                    'binding': product_raw.get('binding', ''),  # Tipo de producto (Books, Electronics, etc.)
                                    'image_url': keepa_service._extract_image_url(product_raw),
                                    'rating': None,
                                    'review_count': None,
                                    'sales_rank_current': None,
                                    'current_price_new': None,
                                    'current_price_amazon': None,
                                    'current_price_used': None,
                                }
                                
                                # Log para debugging - ver qué tipo de productos está obteniendo
                                binding = product_basic.get('binding', 'Unknown')
                                if binding:
                                    binding_counts[binding] = binding_counts.get(binding, 0) + 1
                                    logger.debug(f"Producto ASIN {product_basic['asin']}: binding={binding}, title={product_basic['title'][:50]}")
                                
                                # Extraer rating y review count desde stats si están disponibles
                                stats = product_raw.get('stats', {})
                                if stats:
                                    current = stats.get('current', [])
                                    if current and len(current) > 0:
                                        # Rating (índice 16)
                                        if len(current) > 16:
                                            rating = current[16]
                                            if rating is not None and rating > 0:
                                                product_basic['rating'] = round(rating / 10.0, 1)
                                        
                                        # Review count (índice 17)
                                        if len(current) > 17:
                                            review_count = current[17]
                                            if review_count is not None and review_count >= 0:
                                                product_basic['review_count'] = int(review_count)
                                        
                                        # Sales rank (índice 3)
                                        if len(current) > 3:
                                            sales_rank = current[3]
                                            if sales_rank is not None and sales_rank > 0:
                                                product_basic['sales_rank_current'] = int(sales_rank)
                                
                                # Extraer precios actuales si están disponibles
                                data = product_raw.get('data', {})
                                if data:
                                    product_basic['current_price_new'] = keepa_service._get_latest_price(data.get('NEW', []))
                                    product_basic['current_price_amazon'] = keepa_service._get_latest_price(data.get('AMAZON', []))
                                    product_basic['current_price_used'] = keepa_service._get_latest_price(data.get('USED', []))
                                
                                # Solo agregar si tiene ASIN y título
                                if product_basic['asin'] and product_basic['title']:
                                    # Convertir precios de centavos a dólares para mostrar
                                    if product_basic['current_price_new']:
                                        product_basic['current_price_new'] = round(float(product_basic['current_price_new']) / 100, 2)
                                    if product_basic['current_price_amazon']:
                                        product_basic['current_price_amazon'] = round(float(product_basic['current_price_amazon']) / 100, 2)
                                    if product_basic['current_price_used']:
                                        product_basic['current_price_used'] = round(float(product_basic['current_price_used']) / 100, 2)
                                    
                                    products_data.append(product_basic)
                                    
                            except Exception as e:
                                logger.warning(f"Error parseando producto best seller: {e}")
                                continue
                        
                        # Log de resumen de tipos de productos
                        if binding_counts:
                            logger.info(f"Resumen de tipos de productos obtenidos: {binding_counts}")
                            logger.info(f"Total de productos parseados: {len(products_data)}")
                        
                        # Obtener nombre de la categoría usando una búsqueda específica
                        # Intentar obtener info de la categoría consultando directamente
                        # Si no funciona, buscar usando un término común
                        try:
                            # Intentar buscar categorías que contengan el ID
                            test_categories = keepa_service.search_categories(category_id)
                            if test_categories:
                                for cat in test_categories:
                                    if cat['id'] == category_id:
                                        category_name = cat['name']
                                        break
                        except:
                            pass
                        
                        # Guardar el conteo de resultados
                        results_count = len(products_data)
                        
                        # Paginación
                        paginator = Paginator(products_data, 20)  # 20 productos por página
                        try:
                            page_number = int(page_number)
                            page_obj = paginator.page(page_number)
                        except (ValueError, TypeError):
                            page_obj = paginator.page(1)
                        except:
                            page_obj = paginator.page(1)
                        
                        # Guardar o actualizar la búsqueda en el historial
                        # Solo guardar si hay resultados o si es una búsqueda válida
                        if category_id and category_search:
                            try:
                                # Buscar si ya existe una búsqueda reciente (últimos 5 minutos) con la misma categoría
                                last_search = BestSellerSearch.objects.filter(
                                    user=request.user,
                                    category_id=category_id
                                ).order_by('-created_at').first()
                                
                                # Si existe una búsqueda reciente (últimos 5 minutos), actualizarla
                                should_update = False
                                if last_search:
                                    time_diff = timezone.now() - last_search.created_at
                                    if time_diff.total_seconds() < 300:  # 5 minutos
                                        should_update = True
                                
                                if should_update:
                                    # Actualizar búsqueda existente con el nuevo conteo
                                    last_search.results_count = results_count
                                    last_search.category_name = category_name
                                    last_search.save()
                                    logger.info(f"Búsqueda de best sellers actualizada en historial: {category_search} ({category_id}) - {results_count} resultados")
                                else:
                                    # Crear nueva entrada en el historial
                                    BestSellerSearch.objects.create(
                                        user=request.user,
                                        category_id=category_id,
                                        category_search=category_search,
                                        category_name=category_name,
                                        results_count=results_count
                                    )
                                    logger.info(f"Búsqueda de best sellers guardada en historial: {category_search} ({category_id}) - {results_count} resultados")
                            except Exception as e:
                                # No fallar si hay error al guardar el historial
                                logger.warning(f"Error guardando búsqueda en historial: {e}")
                        
                except ValueError as e:
                    messages.error(request, 'Error de configuración del sistema. Por favor, contacta al administrador.')
                    logger.error(f"Error de configuración Keepa: {e}", exc_info=True)
                except Exception as e:
                    logger.error(f"Error obteniendo best sellers para category_id '{category_id}': {e}", exc_info=True)
                    error_msg = str(e)
                    if "domain" in error_msg.lower():
                        messages.error(request, 'Error con la configuración del dominio de Amazon. Por favor, contacta al administrador.')
                    elif "category" in error_msg.lower():
                        messages.error(request, f'Error con la categoría seleccionada. Verifica que el ID de categoría sea válido.')
                    else:
                        messages.error(request, f'Error al obtener los best sellers. Detalles: {error_msg[:100]}')
        
        # Breadcrumbs
        breadcrumbs = [
            {'text': 'Inicio', 'url': '/dashboard/'},
            {'text': 'Productos', 'url': '/products/list/'},
            {'text': 'Best Sellers'},
        ]
        
        if category_name:
            breadcrumbs.append({'text': category_name})
        
        # Obtener las últimas búsquedas del usuario (máximo 10)
        # Envolver en try-except por si la tabla aún no existe o hay algún error
        recent_searches = []
        try:
            recent_searches = BestSellerSearch.objects.filter(
                user=request.user
            ).order_by('-created_at')[:10]
        except Exception as e:
            # Si hay error (tabla no existe, etc.), simplemente usar lista vacía
            logger.warning(f"Error obteniendo búsquedas recientes: {e}")
            recent_searches = []
        
        # Parámetros para la paginación
        extra_pagination_params = {}
        if category_id:
            extra_pagination_params['category_id'] = category_id
        if category_search:
            extra_pagination_params['category_search'] = category_search
        
        context = {
            'category_id': category_id,
            'category_search': category_search,  # Para pre-llenar el input
            'category_name': category_name,
            'page_obj': page_obj,
            'products': page_obj if page_obj else [],
            'breadcrumbs': breadcrumbs,
            'recent_searches': recent_searches,
            'extra_pagination_params': extra_pagination_params,
        }
        
        return render(request, 'products/best_sellers.html', context)
        
    except Exception as e:
        import traceback
        logger.error(f"Error en best_sellers_view: {e}")
        logger.error(f"Traceback completo: {traceback.format_exc()}")
        messages.error(request, f'Error procesando la solicitud: {str(e)[:100]}')
        return redirect('products:list')


@login_required
@require_http_methods(["POST"])
def clear_search_history_view(request):
    """
    Vista AJAX para limpiar el historial de búsquedas de best sellers del usuario
    """
    try:
        deleted_count, _ = BestSellerSearch.objects.filter(user=request.user).delete()
        logger.info(f"Historial de búsquedas limpiado para usuario {request.user.username}: {deleted_count} registros eliminados")
        return JsonResponse({
            'success': True,
            'message': f'Se eliminaron {deleted_count} búsqueda(s) del historial.',
            'deleted_count': deleted_count
        })
    except Exception as e:
        logger.error(f"Error limpiando historial de búsquedas: {e}")
        return JsonResponse({
            'success': False,
            'error': 'Error al limpiar el historial'
        }, status=500)


@login_required
@require_http_methods(["GET"])
def best_sellers_api_view(request):
    """
    Vista AJAX para obtener best sellers en formato JSON
    GET: ?category_id=X&page=1
    """
    try:
        category_id = request.GET.get('category_id', '').strip()
        page_number = int(request.GET.get('page', 1))
        
        if not category_id:
            return JsonResponse({
                'success': False,
                'error': 'El parámetro "category_id" es requerido'
            }, status=400)
        
        try:
            keepa_service = KeepaService()
            
            # Obtener ASINs de best sellers
            asins = keepa_service.get_best_sellers(category_id)
            
            if not asins:
                return JsonResponse({
                    'success': True,
                    'asins': [],
                    'products': [],
                    'count': 0,
                    'page': 1,
                    'total_pages': 0
                })
            
            # Consultar información básica en batch
            products_raw = keepa_service.api.query(
                asins[:100],  # Limitar a 100
                history=False,
                stats=0,
                rating=False
            )
            
            # Parsear información básica
            products_data = []
            for product_raw in products_raw:
                try:
                    product_basic = {
                        'asin': product_raw.get('asin', ''),
                        'title': product_raw.get('title', ''),
                        'brand': product_raw.get('brand', ''),
                        'image_url': keepa_service._extract_image_url(product_raw),
                        'rating': None,
                        'review_count': None,
                        'sales_rank_current': None,
                        'current_price_new': None,
                        'current_price_amazon': None,
                    }
                    
                    # Extraer datos básicos desde stats
                    stats = product_raw.get('stats', {})
                    if stats:
                        current = stats.get('current', {})
                        if current:
                            if len(current) > 16:
                                rating = current[16]
                                if rating is not None and rating > 0:
                                    product_basic['rating'] = round(rating / 10.0, 1)
                            if len(current) > 17:
                                review_count = current[17]
                                if review_count is not None and review_count >= 0:
                                    product_basic['review_count'] = int(review_count)
                            if len(current) > 3:
                                sales_rank = current[3]
                                if sales_rank is not None and sales_rank > 0:
                                    product_basic['sales_rank_current'] = int(sales_rank)
                    
                    # Extraer precios
                    data = product_raw.get('data', {})
                    if data:
                        product_basic['current_price_new'] = keepa_service._get_latest_price(data.get('NEW', []))
                        product_basic['current_price_amazon'] = keepa_service._get_latest_price(data.get('AMAZON', []))
                    
                    if product_basic['asin'] and product_basic['title']:
                        products_data.append(product_basic)
                        
                except Exception as e:
                    logger.warning(f"Error parseando producto en API: {e}")
                    continue
            
            # Paginación
            paginator = Paginator(products_data, 20)
            try:
                page_obj = paginator.page(page_number)
            except:
                page_obj = paginator.page(1)
            
            # Convertir precios a formato legible
            products_json = []
            for p in page_obj:
                product_json = {
                    'asin': p['asin'],
                    'title': p['title'],
                    'brand': p.get('brand'),
                    'image_url': p.get('image_url'),
                    'rating': p.get('rating'),
                    'review_count': p.get('review_count'),
                    'sales_rank_current': p.get('sales_rank_current'),
                    'current_price_new': float(p['current_price_new']) / 100 if p.get('current_price_new') else None,
                    'current_price_amazon': float(p['current_price_amazon']) / 100 if p.get('current_price_amazon') else None,
                }
                products_json.append(product_json)
            
            return JsonResponse({
                'success': True,
                'asins': asins[:100],  # Retornar todos los ASINs consultados
                'products': products_json,
                'count': len(products_json),
                'page': page_obj.number,
                'total_pages': paginator.num_pages,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous(),
            })
            
        except ValueError as e:
            logger.error(f"Error de configuración Keepa: {e}")
            return JsonResponse({
                'success': False,
                'error': 'Error de configuración del sistema'
            }, status=500)
            
    except Exception as e:
        logger.error(f"Error en best_sellers_api_view: {e}")
        return JsonResponse({
            'success': False,
            'error': 'Error procesando la solicitud'
        }, status=500)