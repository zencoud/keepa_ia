"""
Template tags para manejar mensajes flash de Django
similar a cómo Laravel maneja los mensajes flash.
Los mensajes se consumen automáticamente cuando se itera sobre ellos.

IMPORTANTE: Los mensajes se consumen (eliminan de la sesión) al convertir
el iterador de get_messages() a lista. Esto asegura que solo se muestren
una vez y no aparezcan al recargar la página.
"""
from django import template
from django.contrib.messages import get_messages

register = template.Library()


@register.inclusion_tag('products/flash_messages.html', takes_context=True)
def render_flash_messages(context):
    """
    Renderiza todos los mensajes flash y los consume automáticamente.
    Similar a @if(session('flash_message')) en Laravel.
    
    Los mensajes se consumen inmediatamente al convertir el iterador
    a lista, asegurando que solo se muestren una vez y se eliminen
    de la sesión antes de que el usuario pueda recargar la página.
    """
    request = context.get('request')
    if not request:
        return {'messages': []}
    
    # get_messages() retorna un iterador que se consume al iterar sobre él.
    # Al convertir a lista, los mensajes se consumen inmediatamente y se
    # eliminan de la sesión. Esto asegura que no aparezcan al recargar.
    messages_iter = get_messages(request)
    
    # Convertir a lista consume los mensajes inmediatamente.
    # El template renderiza la lista, pero los mensajes ya no están en la sesión.
    messages_list = list(messages_iter)
    
    return {
        'messages': messages_list,
        'request': request
    }

