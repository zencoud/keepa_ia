from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
import json
from .models import Product
from .keepa_service import KeepaService
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
            return render(request, 'products/search.html')
        
        # Validar formato básico de ASIN (10 caracteres alfanuméricos)
        if len(asin) != 10 or not asin.isalnum():
            messages.error(request, 'El ASIN debe tener exactamente 10 caracteres alfanuméricos.')
            return render(request, 'products/search.html')
        
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
                    return render(request, 'products/search.html')
                
                # Verificar si el producto tiene al menos el ASIN
                if not product_data.get('asin'):
                    messages.error(request, f'El producto con ASIN {asin} no tiene datos válidos.')
                    return render(request, 'products/search.html')
                    
            except ValueError as e:
                messages.error(request, f'Error de configuración: {str(e)}')
                return render(request, 'products/search.html')
            
            # Guardar producto en la BD
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
                
                messages.success(request, f'Producto {asin} consultado exitosamente.')
                return redirect('products:detail', asin=asin)
                
        except Exception as e:
            logger.error(f"Error en búsqueda de producto {asin}: {e}")
            messages.error(request, f'Error al consultar el producto: {str(e)}')
            return render(request, 'products/search.html')
    
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
        return redirect('products:detail', asin=asin)
        
    except Exception as e:
        logger.error(f"Error actualizando producto {asin}: {e}")
        messages.error(request, f'Error al actualizar el producto: {str(e)}')
        return redirect('products:detail', asin=asin)


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