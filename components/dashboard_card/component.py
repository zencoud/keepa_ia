from django_components import component


@component.register("dashboard_card")
class DashboardCard(component.Component):
    """
    Componente de tarjeta para dashboard.
    
    Props:
    - title: Título de la card (opcional)
    - icon_svg: SVG icono para el título (opcional)
    - badge: Badge adicional en el header (opcional, ej: contador)
    - action_url: URL para el botón de acción (opcional)
    - action_text: Texto del botón de acción (opcional)
    - action_class: Clase CSS para el botón (default: btn-primary)
    
    Slots:
    - default: Contenido principal de la card
    """
    template_name = "dashboard_card/dashboard_card.html"
    
    def get_context_data(self, title=None, icon_svg=None, badge=None, 
                         action_url=None, action_text=None, action_class=None):
        return {
            'title': title,
            'icon_svg': icon_svg,
            'badge': badge,
            'action_url': action_url,
            'action_text': action_text,
            'action_class': action_class,
        }

