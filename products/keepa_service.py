import keepa
import logging
from dataclasses import dataclass
from django.conf import settings
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class RootCategoryDTO:
    """DTO to represent a root category of Amazon"""
    cat_id: int
    name: str
    context_free_name: str
    domain_id: int
    parent: int
    children: List[int]
    product_count: int
    highest_rank: int
    lowest_rank: int
    matched: bool


class KeepaService:
    """Service to interact with the Keepa API"""
    
    def __init__(self):
        """Inicializa el cliente de Keepa con la API key"""
        self.api_key = settings.KEEPA_API_KEY
        if not self.api_key:
            raise ValueError("KEEPA_API_KEY no está configurada en settings")
        
        try:
            self.api = keepa.Keepa(self.api_key)
        except Exception as e:
            logger.error(f"Error inicializando Keepa API: {e}")
            raise
    
    def query_product(self, asin: str) -> Optional[Dict[str, Any]]:
        """
        Consulta un producto por ASIN
        
        Args:
            asin (str): ASIN del producto a consultar
            
        Returns:
            Dict con los datos del producto o None si hay error
        """
        try:
            logger.info(f"Consultando producto ASIN: {asin}")
            
            # Verificar que el ASIN tenga el formato correcto
            if len(asin) != 10:
                logger.error(f"ASIN inválido: {asin} (debe tener 10 caracteres)")
                return None
            
            # Realizar la consulta con historial completo y stats
            products = self.api.query(asin, history=True, stats=90, rating=True)
            
            if not products:
                logger.warning(f"No se encontró el producto con ASIN: {asin}")
                return None
            
            product_data = products[0]
            
            # Verificar si el producto tiene datos válidos
            # Algunos productos pueden no tener título, pero sí otros datos útiles
            if not product_data.get('title'):
                logger.warning(f"Producto encontrado pero sin título: {asin}")
                # No retornar None, continuar con el parsing

            logger.info(f"Producto encontrado: {product_data.get('title', 'Sin título')}")

            # Guardar datos raw para debugging
            parsed_data = self.parse_product_data(product_data)
            parsed_data['raw_data'] = product_data  # Incluir datos raw para debugging
            return parsed_data
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error consultando producto {asin}: {error_msg}")
            
            # Proporcionar mensajes más específicos según el tipo de error
            if "REQUEST_REJECTED" in error_msg:
                logger.error("La solicitud fue rechazada por Keepa API. Verifica tu token y suscripción.")
            elif "INVALID_ASIN" in error_msg:
                logger.error(f"ASIN inválido: {asin}")
            elif "ASIN_NOT_FOUND" in error_msg:
                logger.error(f"ASIN no encontrado en la base de datos de Keepa: {asin}")
            
            return None
    
    def parse_product_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convierte los datos raw de Keepa a un formato limpio
        
        Args:
            raw_data: Datos raw de la API de Keepa
            
        Returns:
            Dict con los datos parseados
        """
        try:
            # Extraer stats si están disponibles
            stats = raw_data.get('stats', {})
            
            # Extraer rating y review count desde stats (más confiable)
            rating_value = None
            review_count_value = None
            sales_rank_value = None
            
            # Primero intentar desde stats
            if stats:
                # Rating actual (avg está en escala 0-50, dividir entre 10)
                current_rating = stats.get('current', {})
                if current_rating and len(current_rating) > 16:
                    avg_rating = current_rating[16]  # Índice 16 es RATING
                    if avg_rating is not None and avg_rating > 0:
                        rating_value = round(avg_rating / 10.0, 1)
                
                # Review count actual
                if current_rating and len(current_rating) > 17:
                    review_count = current_rating[17]  # Índice 17 es COUNT_REVIEWS
                    if review_count is not None and review_count >= 0:
                        review_count_value = int(review_count)
                
                # Sales Rank actual
                if current_rating and len(current_rating) > 3:
                    sales_rank = current_rating[3]  # Índice 3 es SALES
                    if sales_rank is not None and sales_rank > 0:
                        sales_rank_value = int(sales_rank)
            
            # Si no hay stats, intentar desde csv
            if not rating_value or not review_count_value or not sales_rank_value:
                csv_data = raw_data.get('csv', [])
                
                # Extraer rating del csv (índice 16)
                if not rating_value and csv_data and len(csv_data) > 16 and csv_data[16]:
                    rating_array = csv_data[16]
                    if isinstance(rating_array, list) and len(rating_array) >= 2:
                        # El último valor está en la última posición (índice impar)
                        last_rating = rating_array[-1] if len(rating_array) % 2 == 0 else rating_array[-2]
                        if last_rating is not None and last_rating > 0:
                            rating_value = round(last_rating / 10.0, 1)
                
                # Extraer review count del csv (índice 17)
                if not review_count_value and csv_data and len(csv_data) > 17 and csv_data[17]:
                    review_array = csv_data[17]
                    if isinstance(review_array, list) and len(review_array) >= 2:
                        last_review_count = review_array[-1] if len(review_array) % 2 == 0 else review_array[-2]
                        if last_review_count is not None and last_review_count >= 0:
                            review_count_value = int(last_review_count)
                
                # Extraer sales rank del csv (índice 3)
                if not sales_rank_value and csv_data and len(csv_data) > 3 and csv_data[3]:
                    sales_array = csv_data[3]
                    if isinstance(sales_array, list) and len(sales_array) >= 2:
                        last_sales_rank = sales_array[-1] if len(sales_array) % 2 == 0 else sales_array[-2]
                        if last_sales_rank is not None and last_sales_rank > 0:
                            sales_rank_value = int(last_sales_rank)
            
            # Extraer nombres de categorías
            category_names = self._extract_category_names(raw_data)
            
            # Extraer datos básicos
            parsed_data = {
                'asin': raw_data.get('asin', ''),
                'title': raw_data.get('title', ''),
                'brand': raw_data.get('brand', ''),
                'image_url': self._extract_image_url(raw_data),
                'rating': rating_value,
                'review_count': self._safe_int(review_count_value),
                'sales_rank_current': self._safe_int(sales_rank_value),
                'color': raw_data.get('color', ''),
                'binding': raw_data.get('binding', ''),
                'availability_amazon': raw_data.get('availabilityAmazon', 0),
                'categories': category_names,
                'category_tree': raw_data.get('categoryTree', []),
            }
            
            # Extraer precios actuales
            data = raw_data.get('data', {})
            if data:
                # Precios están en centavos, mantenerlos así para el modelo
                parsed_data['current_price_new'] = self._get_latest_price(data.get('NEW', []))
                parsed_data['current_price_amazon'] = self._get_latest_price(data.get('AMAZON', []))
                parsed_data['current_price_used'] = self._get_latest_price(data.get('USED', []))
                
                # Extraer sales rank, rating y review count del historial si no se encontraron antes
                if not parsed_data['sales_rank_current']:
                    sales_data = data.get('SALES', [])
                    if isinstance(sales_data, (list, tuple)) and len(sales_data) > 0:
                        # Filtrar valores válidos (mayores a 0 y no -1)
                        valid_ranks = [r for r in sales_data if isinstance(r, (int, float)) and r > 0]
                        if valid_ranks:
                            parsed_data['sales_rank_current'] = int(valid_ranks[-1])
                
                # Extraer rating del historial si no se encontró antes
                if not parsed_data['rating']:
                    rating_data = data.get('RATING', [])
                    if isinstance(rating_data, (list, tuple)) and len(rating_data) > 0:
                        # Filtrar valores válidos y tomar el último
                        valid_ratings = [r for r in rating_data if isinstance(r, (int, float)) and r > 0]
                        if valid_ratings:
                            parsed_data['rating'] = round(valid_ratings[-1] / 10.0, 2)
                
                # Extraer review count del historial si no se encontró antes
                if not parsed_data['review_count']:
                    review_data = data.get('COUNT_REVIEWS', [])
                    if isinstance(review_data, (list, tuple)) and len(review_data) > 0:
                        # Filtrar valores válidos y tomar el último
                        valid_reviews = [r for r in review_data if isinstance(r, (int, float)) and r >= 0]
                        if valid_reviews:
                            parsed_data['review_count'] = int(valid_reviews[-1])
                
                # Guardar historial completo de precios
                parsed_data['price_history'] = self.extract_price_history(data)
                
                # Extraer historial de calificaciones
                parsed_data['rating_history'] = self.extract_rating_history(data)
                
                # Extraer historial de sales rank
                parsed_data['sales_rank_history'] = self.extract_sales_rank_history(data)
                
                # Extraer datos de reseñas
                parsed_data['reviews_data'] = self.extract_reviews_data(raw_data)
            else:
                # Si no hay datos de precios, inicializar con valores por defecto
                parsed_data['current_price_new'] = None
                parsed_data['current_price_amazon'] = None
                parsed_data['current_price_used'] = None
                parsed_data['price_history'] = {}
            
            return parsed_data
            
        except Exception as e:
            logger.error(f"Error parseando datos del producto: {e}")
            # Devolver datos básicos aunque haya error en el parsing
            return {
                'asin': raw_data.get('asin', ''),
                'title': raw_data.get('title', ''),
                'brand': raw_data.get('brand', ''),
                'rating': raw_data.get('rating', None),
                'review_count': raw_data.get('reviewCount', None),
                'sales_rank_current': raw_data.get('salesRank', None),
                'current_price_new': None,
                'current_price_amazon': None,
                'current_price_used': None,
                'price_history': {},
            }
    
    def _get_latest_price(self, price_list) -> Optional[int]:
        """
        Obtiene el precio más reciente de una lista de precios
        
        Args:
            price_list: Lista de precios en centavos (puede ser array de numpy)
            
        Returns:
            Precio más reciente o None si no hay datos
        """
        if price_list is None:
            return None
        
        # Convertir a lista si es un array de numpy
        try:
            if hasattr(price_list, 'tolist'):
                price_list = price_list.tolist()
            elif not isinstance(price_list, (list, tuple)):
                return None
        except:
            return None
        
        # Verificar que tenga elementos
        if len(price_list) == 0:
            return None
        
        # Filtrar precios válidos (mayores a 0, no NaN)
        valid_prices = []
        for p in price_list:
            try:
                if isinstance(p, (int, float)) and not (p != p) and p > 0:  # p != p detecta NaN
                    valid_prices.append(float(p))
            except (ValueError, TypeError):
                continue
        
        if len(valid_prices) == 0:
            return None
        
        # Los precios de Keepa vienen en dólares, convertir a centavos para almacenar
        return int(valid_prices[-1] * 100)  # Último precio válido en centavos
    
    def _safe_int(self, value) -> Optional[int]:
        """Convierte valor a int de forma segura"""
        if value is None:
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None
    
    def _safe_float(self, value) -> Optional[float]:
        """Convierte valor a float de forma segura"""
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    def _extract_category_names(self, raw_data: Dict[str, Any]) -> List[str]:
        """
        Extrae nombres de categorías de los datos de Keepa
        
        Args:
            raw_data: Datos raw de Keepa
            
        Returns:
            Lista de nombres de categorías
        """
        category_names = []
        
        # Intentar extraer desde categoryTree (tiene nombres y IDs)
        category_tree = raw_data.get('categoryTree', [])
        if category_tree and isinstance(category_tree, list):
            for category in category_tree:
                if isinstance(category, dict):
                    # Extraer nombre de la categoría
                    name = category.get('name', '')
                    if name and name not in category_names:
                        category_names.append(name)
        
        # Si no hay categoryTree, intentar desde el campo categories
        # pero este suele contener solo IDs
        if not category_names:
            categories = raw_data.get('categories', [])
            if categories and isinstance(categories, list):
                # Si son números (IDs), no los mostramos, solo si son strings (nombres)
                for cat in categories:
                    if isinstance(cat, str) and not cat.isdigit():
                        category_names.append(cat)
        
        return category_names
    
    def _extract_image_url(self, raw_data: Dict[str, Any]) -> Optional[str]:
        """
        Extrae la URL de imagen del producto de los datos de Keepa
        
        Args:
            raw_data: Datos raw de Keepa
            
        Returns:
            URL de imagen o None si no se encuentra
        """
        # Intentar extraer de diferentes campos de Keepa
        image_fields = ['image', 'imageUrl', 'mainImage', 'img']
        
        for field in image_fields:
            image_data = raw_data.get(field)
            if image_data:
                if isinstance(image_data, str) and image_data.startswith('http'):
                    return image_data
        
        # Campo específico de Keepa: 'images' contiene array de objetos con imagen
        images = raw_data.get('images', [])
        if isinstance(images, list) and len(images) > 0:
            first_image = images[0]
            if isinstance(first_image, dict) and 'm' in first_image:
                # Construir URL usando el patrón de Amazon con el nombre del archivo
                image_name = first_image['m']
                return f"https://images-na.ssl-images-amazon.com/images/I/{image_name}"
            elif isinstance(first_image, str):
                # Si es string directo
                return f"https://images-na.ssl-images-amazon.com/images/I/{first_image}"
        
        return None
    
    def _keepa_time_to_datetime(self, keepa_minutes: int) -> datetime:
        """
        Convierte el tiempo de Keepa a datetime
        
        Args:
            keepa_minutes: Minutos desde la base de Keepa (21564000 minutos desde 01-01-1970)
            
        Returns:
            datetime object
        """
        # Keepa usa como base: 21564000 minutos desde 01-01-1970
        base_minutes = 21564000
        total_minutes = base_minutes + keepa_minutes
        timestamp = total_minutes * 60  # Convertir a segundos
        return datetime.fromtimestamp(timestamp)
    
    def extract_price_history(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extrae el historial de precios de los datos raw
        
        Args:
            data: Datos raw de precios de Keepa
            
        Returns:
            Dict con el historial de precios organizado
        """
        price_history = {}
        
        # Tipos de precios a extraer
        price_types = ['NEW', 'AMAZON', 'USED', 'COLLECTIBLE', 'REFURBISHED']
        
        for price_type in price_types:
            if price_type in data:
                prices = data[price_type]
                times = data.get(f'{price_type}_time', [])
                
                # Convertir a lista si es array de numpy
                if hasattr(prices, 'tolist'):
                    prices = prices.tolist()
                if hasattr(times, 'tolist'):
                    times = times.tolist()
                
                # Asegurar que prices y times sean listas
                if not isinstance(prices, list):
                    prices = []
                if not isinstance(times, list):
                    times = []
                
                # Los datos de Keepa ya vienen como datetime objects
                formatted_times = []
                if times and len(times) > 0:
                    try:
                        # Los tiempos ya vienen como datetime objects
                        formatted_times = [t.strftime('%Y-%m-%d %H:%M') if hasattr(t, 'strftime') else str(t) for t in times]
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Error formateando fechas para {price_type}: {e}")
                        formatted_times = []
                
                # Convertir datetime objects a strings para serialización JSON
                times_str = []
                if times and len(times) > 0:
                    times_str = [t.isoformat() if hasattr(t, 'isoformat') else str(t) for t in times]
                
                # Filtrar precios válidos (no NaN, no -1) y convertir a centavos
                valid_indices = []
                valid_prices = []
                valid_times = []
                valid_formatted_times = []
                
                for i, price in enumerate(prices):
                    if (price is not None and 
                        str(price) != 'nan' and 
                        price != -1 and 
                        price > 0):
                        valid_indices.append(i)
                        # Los precios vienen en dólares, convertir a centavos
                        valid_prices.append(int(price * 100))
                        if i < len(times_str):
                            valid_times.append(times_str[i])
                        if i < len(formatted_times):
                            valid_formatted_times.append(formatted_times[i])
                
                price_history[price_type] = {
                    'prices': valid_prices,
                    'times': valid_times,
                    'formatted_times': valid_formatted_times
                }
        
        return price_history
    
    def extract_rating_history(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extrae el historial de calificaciones de los datos raw
        
        Args:
            data: Datos raw de Keepa
            
        Returns:
            Dict con el historial de calificaciones organizado
        """
        rating_history = {}
        
        # Extraer datos de rating
        ratings = data.get('RATING', [])
        rating_times = data.get('RATING_time', [])
        
        # Convertir a lista si es array de numpy
        if hasattr(ratings, 'tolist'):
            ratings = ratings.tolist()
        if hasattr(rating_times, 'tolist'):
            rating_times = rating_times.tolist()
        
        # Asegurar que sean listas
        if not isinstance(ratings, list):
            ratings = []
        if not isinstance(rating_times, list):
            rating_times = []
        
        # Procesar datos de rating
        rating_data = []
        for t, r in zip(rating_times, ratings):
            if r != -1:  # -1 = sin dato
                try:
                    # Convertir tiempo de Keepa a datetime
                    if isinstance(t, (int, float)) and t > 0:
                        date_obj = self._keepa_time_to_datetime(t)
                        date_str = date_obj.isoformat()
                    else:
                        date_str = str(t)
                except:
                    date_str = str(t)
                
                rating_data.append({
                    "date": date_str,
                    "rating": r / 10 if r > 0 else 0  # Keepa devuelve rating * 10
                })
        
        rating_history = {
            'ratings': rating_data,
            'formatted_times': [item['date'] for item in rating_data],
            'values': [item['rating'] for item in rating_data]
        }
        
        return rating_history
    
    def extract_sales_rank_history(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extrae el historial de sales rank de los datos raw
        
        Args:
            data: Datos raw de Keepa
            
        Returns:
            Dict con el historial de sales rank organizado
        """
        sales_rank_history = {}
        
        # Extraer datos de sales rank
        sales_ranks = data.get('SALES', [])
        sales_times = data.get('SALES_time', [])
        
        # Convertir a lista si es array de numpy
        if hasattr(sales_ranks, 'tolist'):
            sales_ranks = sales_ranks.tolist()
        if hasattr(sales_times, 'tolist'):
            sales_times = sales_times.tolist()
        
        # Asegurar que sean listas
        if not isinstance(sales_ranks, list):
            sales_ranks = []
        if not isinstance(sales_times, list):
            sales_times = []
        
        # Procesar datos de sales rank
        sales_data = []
        for t, s in zip(sales_times, sales_ranks):
            if s != -1:  # -1 = sin dato
                try:
                    # Convertir tiempo de Keepa a datetime
                    if isinstance(t, (int, float)) and t > 0:
                        date_obj = self._keepa_time_to_datetime(t)
                        date_str = date_obj.isoformat()
                    else:
                        date_str = str(t)
                except:
                    date_str = str(t)
                
                sales_data.append({
                    "date": date_str,
                    "salesRank": int(s) if s > 0 else 0
                })
        
        sales_rank_history = {
            'sales_ranks': sales_data,
            'formatted_times': [item['date'] for item in sales_data],
            'values': [item['salesRank'] for item in sales_data]
        }
        
        return sales_rank_history
    
    def extract_reviews_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extrae datos de reseñas de los datos raw
        
        Args:
            raw_data: Datos raw de Keepa
            
        Returns:
            Dict con los datos de reseñas organizados
        """
        reviews_data = {}
        
        # Extraer datos básicos de reseñas
        review_count = raw_data.get('reviewCount', 0)
        rating = raw_data.get('rating', 0)
        
        # Extraer distribución de calificaciones si está disponible
        rating_histogram = raw_data.get('ratingHistogram', {})
        
        # Procesar distribución de calificaciones
        rating_distribution = {}
        if rating_histogram:
            for star_rating in range(1, 6):
                count = rating_histogram.get(str(star_rating), 0)
                if count > 0:
                    rating_distribution[star_rating] = count
        
        reviews_data = {
            'total_reviews': review_count,
            'average_rating': rating / 10 if rating > 0 else 0,  # Keepa devuelve rating * 10
            'rating_distribution': rating_distribution,
            'has_reviews': review_count > 0
        }
        
        return reviews_data
    
    def search_products(self, search_params: Dict[str, Any]) -> List[str]:
        """
        Busca productos usando parámetros de búsqueda
        
        Args:
            search_params: Parámetros de búsqueda (author, title, etc.)
            
        Returns:
            Lista de ASINs encontrados
        """
        try:
            logger.info(f"Buscando productos con parámetros: {search_params}")
            asins = self.api.product_finder(search_params)
            logger.info(f"Encontrados {len(asins)} productos")
            return asins
            
        except Exception as e:
            logger.error(f"Error buscando productos: {e}")
            return []
    
    def get_product_offers(self, asin: str, offers_count: int = 20) -> List[Dict[str, Any]]:
        """
        Obtiene ofertas de un producto
        
        Args:
            asin: ASIN del producto
            offers_count: Número de ofertas a obtener
            
        Returns:
            Lista de ofertas
        """
        try:
            logger.info(f"Obteniendo ofertas para ASIN: {asin}")
            products = self.api.query(asin, offers=offers_count)
            
            if not products:
                return []
            
            product = products[0]
            offers = product.get('offers', [])
            live_offers_order = product.get('liveOffersOrder', [])
            
            # Procesar ofertas activas
            active_offers = []
            for index in live_offers_order:
                if index < len(offers):
                    offer = offers[index]
                    active_offers.append({
                        'seller_id': offer.get('sellerId', ''),
                        'seller_name': offer.get('sellerName', ''),
                        'price': offer.get('price', 0),
                        'shipping': offer.get('shipping', 0),
                        'is_amazon': offer.get('isAmazon', False),
                        'is_fba': offer.get('isFBA', False),
                        'condition': offer.get('condition', ''),
                        'offer_csV': offer.get('offerCSV', ''),
                    })
            
            return active_offers
            
        except Exception as e:
            logger.error(f"Error obteniendo ofertas para {asin}: {e}")
            return []
    
    def search_categories(self, query: str, domain: str = 'MX') -> List[Dict[str, Any]]:
        """
        Busca categorías por nombre
        
        Args:
            query: Nombre o término de búsqueda de la categoría
            domain: Dominio de Amazon ('MX', 'US', 'UK', etc.). Default: 'MX' (México)
            
        Returns:
            Lista de diccionarios con información de categorías encontradas
            Cada diccionario contiene: id, name, contextFreeName, domainId
            Ordenadas por relevancia (categorías de México primero)
        """
        try:
            logger.info(f"Buscando categorías con query: {query} (domain: {domain})")
            
            if not query or not query.strip():
                logger.warning("Query de búsqueda de categoría vacío")
                return []
            
            # Buscar categorías usando la API de Keepa con dominio de México
            categories = self.api.search_for_categories(query.strip(), domain=domain)
            
            if not categories:
                logger.info(f"No se encontraron categorías para: {query} en dominio {domain}")
                return []
            
            # Convertir el diccionario de categorías a lista de diccionarios
            category_list = []
            query_lower = query.lower().strip()
            is_book_search = any(term in query_lower for term in ['book', 'libro', 'ebook', 'e-book', 'kindle'])
            
            # Mapeo de domainId: 11 = MX (México)
            mx_domain_id = 11
            
            for category_id, category_data in categories.items():
                name = category_data.get('name', '')
                context_free_name = category_data.get('contextFreeName', '')
                domain_id = category_data.get('domainId', 1)
                binding = category_data.get('binding', '').lower() if category_data.get('binding') else ''
                
                category_info = {
                    'id': str(category_id),
                    'name': name,
                    'contextFreeName': context_free_name,
                    'domainId': domain_id,
                    'binding': category_data.get('binding', ''),
                }
                
                # Calcular score de relevancia
                score = 0
                name_lower = name.lower()
                context_lower = context_free_name.lower() if context_free_name else ''
                
                # Priorizar coincidencias exactas en el nombre
                if query_lower == name_lower:
                    score += 1000
                elif query_lower in name_lower:
                    score += 500
                elif any(word in name_lower for word in query_lower.split()):
                    score += 200
                
                # Priorizar coincidencias en contextFreeName
                if context_free_name and query_lower in context_lower:
                    score += 300
                
                # Priorizar categorías de México (domainId=11)
                if domain_id == mx_domain_id:
                    score += 100
                else:
                    # Penalizar categorías de otros dominios
                    score -= 200
                
                # Penalizar categorías de Books si no se buscan libros
                if not is_book_search and binding == 'books':
                    score -= 500
                    logger.debug(f"Penalizando categoría Books: {name} (ID: {category_id})")
                
                category_info['relevance_score'] = score
                category_list.append(category_info)
            
            # Ordenar por score de relevancia (mayor primero)
            category_list.sort(key=lambda x: x['relevance_score'], reverse=True)
            
            # Log para debugging
            logger.info(f"Encontradas {len(category_list)} categorías para: {query} (domain: {domain})")
            if category_list:
                top_5 = category_list[:5]
                top_5_info = [(c['name'], c['id'], c['relevance_score'], f"domainId={c['domainId']}") for c in top_5]
                logger.info(f"Top 5 categorías: {top_5_info}")
            
            return category_list
            
        except Exception as e:
            logger.error(f"Error buscando categorías para '{query}': {e}")
            return []
    
    def get_best_sellers(self, category_id: str, domain: str = 'MX') -> List[str]:
        """
        Obtiene los ASINs de los productos best sellers de una categoría
        
        Args:
            category_id: ID de la categoría de Amazon (como string, ej: "541966")
            domain: Dominio de Amazon ('MX', 'US', 'UK', etc.). Default: 'MX' (México)
            
        Returns:
            Lista de ASINs ordenados por popularidad
        """
        try:
            category_id_clean = str(category_id).strip() if category_id else ""
            
            logger.info(f"Obteniendo best sellers para categoría '{category_id_clean}' (domain: {domain})")
            
            if not category_id_clean:
                logger.error("category_id no puede estar vacío")
                return []
            
            # Validar que category_id sea numérico (los IDs de categoría son números)
            if not category_id_clean.isdigit():
                logger.error(f"category_id debe ser numérico. Recibido: '{category_id_clean}'")
                return []
            
            # Consultar best sellers usando la API de Keepa
            # El método espera domain como string ('MX', 'US', 'UK', etc.) no como int
            logger.debug(f"Llamando a api.best_sellers_query con category='{category_id_clean}', domain='{domain}'")
            best_sellers = self.api.best_sellers_query(category_id_clean, domain=domain)
            
            logger.debug(f"Respuesta de best_sellers_query: tipo={type(best_sellers)}, valor={best_sellers}")
            
            if not best_sellers:
                logger.warning(f"No se encontraron best sellers para categoría {category_id_clean} (domain: {domain})")
                return []
            
            # La respuesta puede ser una lista o None
            if not isinstance(best_sellers, list):
                logger.warning(f"Respuesta inesperada de best_sellers_query: {type(best_sellers)}")
                return []
            
            # Asegurar que todos los ASINs sean strings válidos
            asin_list = []
            for asin in best_sellers:
                if asin:
                    asin_str = str(asin).strip()
                    if len(asin_str) == 10:  # Los ASINs tienen 10 caracteres
                        asin_list.append(asin_str)
                    else:
                        logger.warning(f"ASIN inválido encontrado: '{asin_str}' (longitud: {len(asin_str)})")
            
            logger.info(f"Encontrados {len(asin_list)} best sellers válidos para categoría {category_id_clean} (domain: {domain})")
            return asin_list
            
        except Exception as e:
            error_msg = str(e)
            import traceback
            logger.error(f"Error obteniendo best sellers para categoría {category_id}: {error_msg}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            
            # Proporcionar mensajes más específicos según el tipo de error
            if "INVALID_CATEGORY" in error_msg or "CATEGORY_NOT_FOUND" in error_msg:
                logger.error(f"Categoría inválida o no encontrada: {category_id}")
            elif "REQUEST_REJECTED" in error_msg:
                logger.error("La solicitud fue rechazada por Keepa API. Verifica tu token y suscripción.")
            elif "domain" in error_msg.lower():
                logger.error(f"Error con el dominio '{domain}'. Verifica que sea válido (ej: 'MX', 'US', 'UK', 'DE')")
            
            return []
    
    def get_root_categories(self, domain: str = 'MX') -> List[RootCategoryDTO]:
        """
        Gets the root categories of Amazon for a specific domain
        
        Args:
            domain: Amazon domain ('MX', 'US', 'UK', etc.). Default: 'MX' (Mexico)
            
        Returns:
            List of RootCategoryDTO with the root categories found
        """
        try:
            logger.info(f"Getting root categories for domain: {domain}")
            
            # Query root categories using category_lookup(0)
            # category_id=0 returns all root categories
            logger.debug(f"Calling api.category_lookup with category_id=0, domain='{domain}'")
            categories = self.api.category_lookup(0, domain=domain)
            
            logger.debug(f"Response from category_lookup: type={type(categories)}, count={len(categories) if categories else 0}")
            
            if not categories:
                logger.warning(f"No root categories found for domain {domain}")
                return []
            
            # Response is a dict where keys are catIds (int) and values are dicts with data
            if not isinstance(categories, dict):
                logger.warning(f"Unexpected response type from category_lookup: {type(categories)}")
                return []
            
            # Convert each category to RootCategoryDTO
            root_categories = []
            for cat_id, category_data in categories.items():
                try:
                    # Validate that category_data is a dictionary
                    if not isinstance(category_data, dict):
                        logger.warning(f"Invalid category data for catId {cat_id}: {type(category_data)}")
                        continue
                    
                    # Extract and validate required fields
                    cat_id_int = int(cat_id) if isinstance(cat_id, (int, str)) else 0
                    name = category_data.get('name', '')
                    context_free_name = category_data.get('contextFreeName', '')
                    domain_id = category_data.get('domainId', 0)
                    parent = category_data.get('parent', 0)
                    children = category_data.get('children', [])
                    product_count = category_data.get('productCount', 0)
                    highest_rank = category_data.get('highestRank', 0)
                    lowest_rank = category_data.get('lowestRank', 0)
                    matched = category_data.get('matched', False)
                    
                    # Ensure children is a list
                    if not isinstance(children, list):
                        children = []
                    
                    # Create DTO
                    root_category = RootCategoryDTO(
                        cat_id=cat_id_int,
                        name=str(name) if name else '',
                        context_free_name=str(context_free_name) if context_free_name else '',
                        domain_id=int(domain_id) if domain_id else 0,
                        parent=int(parent) if parent is not None else 0,
                        children=[int(c) for c in children if isinstance(c, (int, str)) and str(c).isdigit()],
                        product_count=int(product_count) if product_count else 0,
                        highest_rank=int(highest_rank) if highest_rank else 0,
                        lowest_rank=int(lowest_rank) if lowest_rank else 0,
                        matched=bool(matched) if matched is not None else False
                    )
                    
                    root_categories.append(root_category)
                    
                except (ValueError, TypeError, KeyError) as e:
                    logger.warning(f"Error processing category {cat_id}: {e}")
                    continue
            
            logger.info(f"Found {len(root_categories)} valid root categories for domain {domain}")
            return root_categories
            
        except Exception as e:
            error_msg = str(e)
            import traceback
            logger.error(f"Error getting root categories for domain {domain}: {error_msg}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            
            # Provide more specific error messages based on error type
            if "REQUEST_REJECTED" in error_msg:
                logger.error("Request was rejected by Keepa API. Verify your token and subscription.")
            elif "domain" in error_msg.lower():
                logger.error(f"Error with domain '{domain}'. Verify it's valid (e.g., 'MX', 'US', 'UK', 'DE')")
            elif "not yet available" in error_msg.lower() or "no match found" in error_msg.lower():
                logger.warning(f"No root categories available for domain {domain}")
            
            return []
    
    def get_category_children(self, category_id: int, domain: str = 'MX') -> List[RootCategoryDTO]:
        """
        Gets the child categories of a specific category
        
        Args:
            category_id: ID of the parent category to get children from
            domain: Amazon domain ('MX', 'US', 'UK', etc.). Default: 'MX' (Mexico)
            
        Returns:
            List of RootCategoryDTO with the child categories found
        """
        try:
            logger.info(f"Getting child categories for category ID {category_id} in domain: {domain}")
            
            # Validate category_id
            if not category_id or category_id <= 0:
                logger.error(f"Invalid category_id: {category_id}. Must be a positive integer")
                return []
            
            # Query child categories using category_lookup with specific category_id
            logger.debug(f"Calling api.category_lookup with category_id={category_id}, domain='{domain}'")
            category_response = self.api.category_lookup(category_id, domain=domain)
            
            logger.debug(f"Response from category_lookup: type={type(category_response)}, count={len(category_response) if category_response else 0}")
            
            if not category_response:
                logger.warning(f"No category found for ID {category_id} in domain {domain}")
                return []
            
            # Response is a dict where keys are catIds (int) and values are dicts with data
            if not isinstance(category_response, dict):
                logger.warning(f"Unexpected response type from category_lookup: {type(category_response)}")
                return []
            
            # Get the parent category data
            parent_category = category_response.get(category_id)
            if not parent_category:
                logger.warning(f"Category {category_id} not found in response")
                return []
            
            # Extract children IDs from parent category
            children_ids = parent_category.get('children', [])
            if not children_ids or not isinstance(children_ids, list):
                logger.info(f"Category {category_id} has no child categories")
                return []
            
            # Get detailed information for each child category
            child_categories = []
            for child_id in children_ids:
                try:
                    child_data = category_response.get(child_id)
                    if not child_data or not isinstance(child_data, dict):
                        # If child not in response, query it separately
                        logger.debug(f"Child category {child_id} not in response, querying separately")
                        child_response = self.api.category_lookup(child_id, domain=domain)
                        if child_response and isinstance(child_response, dict):
                            child_data = child_response.get(child_id)
                        
                        if not child_data:
                            logger.warning(f"Could not retrieve data for child category {child_id}")
                            continue
                    
                    # Extract and validate required fields
                    cat_id_int = int(child_id) if isinstance(child_id, (int, str)) else 0
                    name = child_data.get('name', '')
                    context_free_name = child_data.get('contextFreeName', '')
                    domain_id = child_data.get('domainId', 0)
                    parent = child_data.get('parent', category_id)
                    children = child_data.get('children', [])
                    product_count = child_data.get('productCount', 0)
                    highest_rank = child_data.get('highestRank', 0)
                    lowest_rank = child_data.get('lowestRank', 0)
                    matched = child_data.get('matched', False)
                    
                    # Ensure children is a list
                    if not isinstance(children, list):
                        children = []
                    
                    # Create DTO
                    child_category = RootCategoryDTO(
                        cat_id=cat_id_int,
                        name=str(name) if name else '',
                        context_free_name=str(context_free_name) if context_free_name else '',
                        domain_id=int(domain_id) if domain_id else 0,
                        parent=int(parent) if parent is not None else category_id,
                        children=[int(c) for c in children if isinstance(c, (int, str)) and str(c).isdigit()],
                        product_count=int(product_count) if product_count else 0,
                        highest_rank=int(highest_rank) if highest_rank else 0,
                        lowest_rank=int(lowest_rank) if lowest_rank else 0,
                        matched=bool(matched) if matched is not None else False
                    )
                    
                    child_categories.append(child_category)
                    
                except (ValueError, TypeError, KeyError) as e:
                    logger.warning(f"Error processing child category {child_id}: {e}")
                    continue
            
            logger.info(f"Found {len(child_categories)} child categories for category {category_id} in domain {domain}")
            return child_categories
            
        except Exception as e:
            error_msg = str(e)
            import traceback
            logger.error(f"Error getting child categories for category {category_id} in domain {domain}: {error_msg}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            
            # Provide more specific error messages based on error type
            if "REQUEST_REJECTED" in error_msg:
                logger.error("Request was rejected by Keepa API. Verify your token and subscription.")
            elif "domain" in error_msg.lower():
                logger.error(f"Error with domain '{domain}'. Verify it's valid (e.g., 'MX', 'US', 'UK', 'DE')")
            elif "not yet available" in error_msg.lower() or "no match found" in error_msg.lower():
                logger.warning(f"No child categories available for category {category_id} in domain {domain}")
            elif "INVALID_CATEGORY" in error_msg or "CATEGORY_NOT_FOUND" in error_msg:
                logger.error(f"Invalid or not found category: {category_id}")
            
            return []
