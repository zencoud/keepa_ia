from django_components import component


@component.register("empty_state")
class EmptyState(component.Component):
    """
    Componente para mostrar estado vacío.
    
    Props:
    - icon: Icono a mostrar (emoji o SVG)
    - title: Título del estado vacío
    - message: Mensaje descriptivo
    - action_url: URL del botón de acción (opcional)
    - action_text: Texto del botón de acción (opcional)
    """
    template_name = "empty_state/empty_state.html"
    
    def get_context_data(self, icon=None, title=None, message=None, 
                         action_url=None, action_text=None):
        return {
            'icon': icon,
            'title': title,
            'message': message,
            'action_url': action_url,
            'action_text': action_text,
        }

