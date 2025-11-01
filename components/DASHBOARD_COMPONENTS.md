# Componentes del Dashboard - Documentación

## Dashboard Card Component

### Descripción
Componente reutilizable para crear tarjetas de estadísticas en el dashboard con estilo glassmorphism.

### Ubicación
- **Component**: `components/dashboard_card/component.py`
- **Template**: `components/templates/dashboard_card/dashboard_card.html`

### Props Disponibles

| Prop | Tipo | Descripción | Requerido |
|------|------|-------------|-----------|
| `title` | String | Título de la card | No |
| `icon_svg` | String (HTML) | SVG del icono para el título | No |
| `badge` | String (HTML) | Badge adicional en el header (ej: contador) | No |
| `action_url` | String | URL para el botón de acción | No |
| `action_text` | String | Texto del botón de acción | No |
| `action_class` | String | Clase CSS para el botón (default: `btn-primary`) | No |

### Slots

- **`default`**: Contenido principal de la card. Se renderiza en el área de contenido.

### Ejemplo de Uso

```django
{% component "dashboard_card" 
    title="Productos" 
    icon_svg='<svg class="w-6 h-6 text-keepa-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" /></svg>'
    action_url="{% url 'products:list' %}"
    action_text="Ver Todos los Productos"
%}
    {% fill "default" %}
        <div class="flex items-center justify-between">
            <span class="text-slate-300">Total consultados</span>
            <span class="text-2xl font-bold text-keepa-blue-300">{{ total_products }}</span>
        </div>
        <div class="flex items-center justify-between">
            <span class="text-slate-300">Últimos 7 días</span>
            <span class="text-xl font-semibold text-white">{{ recent_products }}</span>
        </div>
    {% endfill %}
{% endcomponent %}
```

### Ejemplo con Badge

```django
{% component "dashboard_card" 
    title="Notificaciones"
    badge='{% if unread_notifications > 0 %}<span class="inline-flex items-center justify-center min-w-[1.5rem] h-6 px-2 text-xs font-bold leading-none text-white bg-gradient-to-r from-red-600 to-red-700 rounded-[40px] shadow-lg">{{ unread_notifications }}</span>{% endif %}'
    action_url="{% url 'products:notifications' %}"
    action_text="Ver Notificaciones"
    action_class="btn-secondary"
%}
    {% fill "default" %}
        <!-- Contenido aquí -->
    {% endfill %}
{% endcomponent %}
```

### Características de Estilo

- **Border-radius**: 40px (consistente con Glass 2025)
- **Glassmorphism**: Aplica `glass-card` y `glass-card-hover` automáticamente
- **Espaciado**: Padding de `p-6`
- **Colores**: Texto blanco por defecto para fondo oscuro

### Notas

- El componente usa el sistema de slots de Django Components
- El icono debe ser HTML válido (usar `|safe` si viene de variable)
- El badge debe ser HTML válido si se proporciona
- Los botones usan las clases de botón definidas en `styles.css` (btn-primary, btn-secondary, etc.)

