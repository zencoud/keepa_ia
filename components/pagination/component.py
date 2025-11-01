from django_components import component


@component.register("pagination")
class Pagination(component.Component):
    """
    Componente para paginación estilo Laravel.
    
    Props:
    - page_obj: Objeto de página de Django Paginator
    """
    template_name = "pagination/pagination.html"
    
    def get_context_data(self, page_obj=None):
        return {
            'page_obj': page_obj,
        }

