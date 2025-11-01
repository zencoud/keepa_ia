from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from products.models import Product
from products.keepa_service import KeepaService
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Obtiene información de productos desde Keepa API para testing'

    def add_arguments(self, parser):
        parser.add_argument(
            'asins',
            nargs='+',
            type=str,
            help='ASIN(s) del producto a consultar (separados por espacio)'
        )
        parser.add_argument(
            '--username',
            type=str,
            default=None,
            help='Username del usuario que consultará el producto (por defecto usa el primer superuser)'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Forzar actualización aunque el producto ya exista'
        )

    def handle(self, *args, **options):
        asins = options['asins']
        username = options.get('username')
        force = options.get('force', False)
        
        # Obtener usuario
        if username:
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                raise CommandError(f'Usuario "{username}" no encontrado')
        else:
            # Usar el primer superuser
            user = User.objects.filter(is_superuser=True).first()
            if not user:
                raise CommandError('No se encontró ningún superusuario. Crea uno o especifica un username con --username')
        
        self.stdout.write(self.style.SUCCESS(f'Usuario: {user.username}'))
        self.stdout.write(self.style.SUCCESS(f'ASINs a consultar: {", ".join(asins)}'))
        self.stdout.write('')
        
        # Inicializar servicio de Keepa
        try:
            keepa_service = KeepaService()
        except Exception as e:
            raise CommandError(f'Error inicializando Keepa API: {e}')
        
        success_count = 0
        error_count = 0
        
        for asin in asins:
            asin = asin.strip().upper()
            
            self.stdout.write(f'\n{"-" * 80}')
            self.stdout.write(f'Procesando ASIN: {asin}')
            self.stdout.write(f'{"-" * 80}')
            
            # Validar formato de ASIN
            if len(asin) != 10 or not asin.isalnum():
                self.stdout.write(
                    self.style.ERROR(f'  ✗ ASIN inválido: {asin} (debe tener 10 caracteres alfanuméricos)')
                )
                error_count += 1
                continue
            
            # Verificar si ya existe
            existing_product = Product.objects.filter(asin=asin).first()
            if existing_product and not force:
                self.stdout.write(
                    self.style.WARNING(f'  ⚠ Producto ya existe en la base de datos')
                )
                self.stdout.write(f'    Título: {existing_product.title}')
                self.stdout.write(f'    Última actualización: {existing_product.last_updated}')
                self.stdout.write(f'    Usa --force para actualizar')
                continue
            
            # Consultar producto
            try:
                self.stdout.write('  Consultando Keepa API...')
                product_data = keepa_service.query_product(asin)
                
                if not product_data:
                    self.stdout.write(
                        self.style.ERROR(f'  ✗ No se pudo obtener datos del producto')
                    )
                    error_count += 1
                    continue
                
                # Mostrar datos obtenidos
                self.stdout.write(self.style.SUCCESS(f'  ✓ Datos obtenidos exitosamente'))
                self.stdout.write(f'    Título: {product_data.get("title", "N/A")}')
                self.stdout.write(f'    Marca: {product_data.get("brand", "N/A")}')
                self.stdout.write(f'    Rating: {product_data.get("rating", "N/A")}')
                self.stdout.write(f'    Reviews: {product_data.get("review_count", "N/A")}')
                self.stdout.write(f'    Sales Rank: {product_data.get("sales_rank_current", "N/A")}')
                
                # Mostrar precios
                price_new = product_data.get('current_price_new')
                price_amazon = product_data.get('current_price_amazon')
                price_used = product_data.get('current_price_used')
                
                self.stdout.write('    Precios:')
                if price_new:
                    self.stdout.write(f'      Nuevo: ${price_new / 100:.2f}')
                if price_amazon:
                    self.stdout.write(f'      Amazon: ${price_amazon / 100:.2f}')
                if price_used:
                    self.stdout.write(f'      Usado: ${price_used / 100:.2f}')
                
                # Mostrar categorías
                categories = product_data.get('categories', [])
                if categories:
                    self.stdout.write(f'    Categorías: {", ".join(categories[:3])}{"..." if len(categories) > 3 else ""}')
                
                # Guardar o actualizar en la base de datos
                if existing_product:
                    self.stdout.write('  Actualizando producto existente...')
                    existing_product.title = product_data['title']
                    existing_product.brand = product_data.get('brand')
                    existing_product.image_url = product_data.get('image_url')
                    existing_product.color = product_data.get('color')
                    existing_product.binding = product_data.get('binding')
                    existing_product.availability_amazon = product_data.get('availability_amazon', 0)
                    existing_product.categories = product_data.get('categories', [])
                    existing_product.category_tree = product_data.get('category_tree', [])
                    existing_product.current_price_new = product_data.get('current_price_new')
                    existing_product.current_price_amazon = product_data.get('current_price_amazon')
                    existing_product.current_price_used = product_data.get('current_price_used')
                    existing_product.sales_rank_current = product_data.get('sales_rank_current')
                    existing_product.rating = product_data.get('rating')
                    existing_product.review_count = product_data.get('review_count')
                    existing_product.price_history = product_data.get('price_history', {})
                    existing_product.rating_history = product_data.get('rating_history', {})
                    existing_product.sales_rank_history = product_data.get('sales_rank_history', {})
                    existing_product.reviews_data = product_data.get('reviews_data', {})
                    existing_product.save()
                    
                    self.stdout.write(self.style.SUCCESS(f'  ✓ Producto actualizado exitosamente'))
                else:
                    self.stdout.write('  Guardando en base de datos...')
                    Product.objects.create(
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
                    
                    self.stdout.write(self.style.SUCCESS(f'  ✓ Producto guardado exitosamente'))
                
                success_count += 1
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'  ✗ Error: {str(e)}')
                )
                logger.exception(f"Error procesando ASIN {asin}")
                error_count += 1
        
        # Resumen final
        self.stdout.write(f'\n{"-" * 80}')
        self.stdout.write(self.style.SUCCESS(f'RESUMEN'))
        self.stdout.write(f'{"-" * 80}')
        self.stdout.write(f'Total ASINs procesados: {len(asins)}')
        self.stdout.write(self.style.SUCCESS(f'  Exitosos: {success_count}'))
        if error_count > 0:
            self.stdout.write(self.style.ERROR(f'  Errores: {error_count}'))
        self.stdout.write('')
        
        if success_count > 0:
            self.stdout.write(self.style.SUCCESS('✓ Comando completado exitosamente'))
        else:
            self.stdout.write(self.style.ERROR('✗ No se pudo procesar ningún producto'))

