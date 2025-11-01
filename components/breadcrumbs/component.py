from django_components import component


@component.register("breadcrumbs")
class Breadcrumbs(component.Component):
    """
    Componente para breadcrumbs de navegación.
    
    Props:
    - items: Lista de diccionarios con 'text' y 'url' (opcional en el último)
    
    Ejemplo de uso:
    {% component "breadcrumbs" items=breadcrumb_items %}{% endcomponent %}
    
    Donde breadcrumb_items es:
    [
        {'text': 'Inicio', 'url': '/'},
        {'text': 'Productos', 'url': '/products/list/'},
        {'text': 'Detalle'}  # Último item sin URL
    ]
    """
    template_name = "breadcrumbs/breadcrumbs.html"
    
    def get_context_data(self, items=None):
        return {
            'items': items or [],
        }

