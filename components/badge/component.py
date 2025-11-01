from django_components import component


@component.register("badge")
class Badge(component.Component):
    """
    Componente para mostrar badges/etiquetas.
    
    Props:
    - text: Texto a mostrar
    - variant: Estilo del badge (primary, success, warning, danger)
    """
    template_name = "badge/badge.html"
    
    def get_context_data(self, text=None, variant='primary'):
        return {
            'text': text,
            'variant': variant,
        }

