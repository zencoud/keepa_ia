import keepa
import logging
from django.conf import settings
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class KeepaService:
    """Servicio para interactuar con la API de Keepa"""
    
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
            
            # Realizar la consulta
            products = self.api.query(asin)
            
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
            # Extraer rating (Keepa lo devuelve multiplicado por 10)
            raw_rating = raw_data.get('csv', [None] * 16)[16] if raw_data.get('csv') and len(raw_data.get('csv', [])) > 16 else raw_data.get('rating')
            rating_value = None
            if raw_rating is not None and raw_rating > 0:
                rating_value = round(raw_rating / 10.0, 2)  # Convertir de escala Keepa (0-50) a escala normal (0-5)
            
            # Extraer review count
            review_count_value = raw_data.get('csv', [None] * 17)[17] if raw_data.get('csv') and len(raw_data.get('csv', [])) > 17 else raw_data.get('reviewCount')
            if review_count_value is not None and review_count_value < 0:
                review_count_value = None  # -1 significa sin datos en Keepa
            
            # Extraer sales rank actual
            sales_rank_value = raw_data.get('csv', [None] * 3)[3] if raw_data.get('csv') and len(raw_data.get('csv', [])) > 3 else raw_data.get('salesRank')
            if sales_rank_value is not None and sales_rank_value < 0:
                sales_rank_value = None  # -1 significa sin datos en Keepa
            
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
                'categories': raw_data.get('categories', []),
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
