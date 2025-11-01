from django_components import component


@component.register("product_card")
class ProductCard(component.Component):
    """
    Componente para mostrar tarjeta de producto.
    
    Props:
    - title: Título del producto
    - asin: ASIN del producto
    - price: Precio del producto (formateado)
    - rating: Calificación del producto (formateado)
    - image_url: URL de la imagen del producto
    - detail_url: URL para ver el detalle
    - refresh_url: URL para actualizar el producto
    - delete_url: URL para eliminar el producto
    """
    template_name = "product_card/product_card.html"
    
    def get_context_data(self, title=None, asin=None, price=None, rating=None, 
                         image_url=None, detail_url=None, refresh_url=None, 
                         delete_url=None):
        return {
            'title': title,
            'asin': asin,
            'price': price,
            'rating': rating,
            'image_url': image_url,
            'detail_url': detail_url,
            'refresh_url': refresh_url,
            'delete_url': delete_url,
        }

