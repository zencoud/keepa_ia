from django_components import component


@component.register("alert")
class Alert(component.Component):
    """
    Componente para mostrar mensajes de alerta/notificación.
    
    Props:
    - variant: Tipo de alerta (success, error, warning, info)
    - message: Mensaje a mostrar
    - icon: HTML del icono (opcional)
    """
    template_name = "alert/alert.html"
    
    def get_context_data(self, variant=None, message=None, icon=None):
        return {
            'variant': variant,
            'message': message,
            'icon': icon,
        }

