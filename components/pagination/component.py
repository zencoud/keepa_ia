from django_components import component
from urllib.parse import urlencode


@component.register("pagination")
class Pagination(component.Component):
    """
    Componente para paginación estilo Laravel.
    
    Props:
    - page_obj: Objeto de página de Django Paginator
    - extra_params: Dict con parámetros adicionales para mantener en la URL (ej: {'category_id': '123', 'category_search': 'laptops'})
    """
    template_name = "pagination/pagination.html"
    
    def get_context_data(self, page_obj=None, extra_params=None):
        # Construir URLs con parámetros adicionales
        base_params = {}
        if extra_params:
            # Filtrar valores None y vacíos
            base_params = {k: v for k, v in extra_params.items() if v is not None and v != ''}
        
        # Construir URLs para cada botón de paginación
        urls = {}
        if page_obj and hasattr(page_obj, 'paginator'):
            # Primera página
            params_first = base_params.copy()
            params_first['page'] = 1
            urls['first'] = '?' + urlencode(params_first)
            
            # Página anterior
            if page_obj.has_previous():
                params_prev = base_params.copy()
                params_prev['page'] = page_obj.previous_page_number()
                urls['previous'] = '?' + urlencode(params_prev)
            
            # Página siguiente
            if page_obj.has_next():
                params_next = base_params.copy()
                params_next['page'] = page_obj.next_page_number()
                urls['next'] = '?' + urlencode(params_next)
            
            # Última página
            params_last = base_params.copy()
            params_last['page'] = page_obj.paginator.num_pages
            urls['last'] = '?' + urlencode(params_last)
        
        return {
            'page_obj': page_obj,
            'urls': urls,
        }

