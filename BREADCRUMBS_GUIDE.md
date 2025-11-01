# 🧭 Guía de Breadcrumbs

## Descripción

Sistema de breadcrumbs (migas de pan) implementado para facilitar la navegación cuando el menú superior no es visible. Especialmente útil en dispositivos móviles o cuando el usuario se desplaza hacia abajo.

---

## 📦 Componente Breadcrumbs

### Ubicación
```
components/breadcrumbs/
├── __init__.py
├── component.py
└── templates/
    └── breadcrumbs/
        └── breadcrumbs.html
```

### Características
- ✅ Icono de inicio (casa) en el primer elemento
- ✅ Separadores con chevron (›)
- ✅ Último elemento sin enlace (página actual)
- ✅ Responsive con flex-wrap
- ✅ Estilo Glass 2025
- ✅ Efectos hover suaves
- ✅ Transiciones en iconos

---

## 🎯 Uso en Templates

### 1. Cargar el componente
```django
{% component "breadcrumbs" items=breadcrumbs %}{% endcomponent %}
```

### 2. Definir breadcrumbs en la vista
```python
breadcrumbs = [
    {'text': 'Inicio', 'url': '/dashboard/'},
    {'text': 'Productos', 'url': '/products/list/'},
    {'text': 'Detalle del Producto'},  # Último sin URL
]

context = {
    'breadcrumbs': breadcrumbs,
    # ... otros datos
}
```

---

## 📍 Páginas con Breadcrumbs Implementados

### 1. Dashboard
```
http://127.0.0.1:8000/dashboard/
```
**Breadcrumb:**
- Dashboard (actual)

### 2. Lista de Productos
```
http://127.0.0.1:8000/products/list/
```
**Breadcrumb:**
- Inicio → Productos (actual)

### 3. Buscar Producto
```
http://127.0.0.1:8000/products/search/
```
**Breadcrumb:**
- Inicio → Productos → Buscar Producto (actual)

### 4. Eliminar Producto
```
http://127.0.0.1:8000/products/delete/<asin>/
```
**Breadcrumb:**
- Inicio → Productos → Eliminar {ASIN} (actual)

---

## 🎨 Estructura del Breadcrumb

### Elemento con Enlace (items intermedios)
```html
<a href="{{ item.url }}" class="text-slate-300 hover:text-white">
    <!-- Icono de casa para el primer item -->
    <svg>...</svg>
    <span class="hover:underline">{{ item.text }}</span>
</a>
<!-- Separador -->
<svg>...</svg>
```

### Elemento Actual (último item)
```html
<span class="text-white font-medium" aria-current="page">
    {{ item.text }}
</span>
```

---

## 🔧 Personalización

### Cambiar el icono de inicio
Edita `components/templates/breadcrumbs/breadcrumbs.html` línea ~8:

```html
<!-- Icono actual: Casa -->
<svg class="w-4 h-4 mr-1.5 group-hover:scale-110 transition-transform" 
     fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
          d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
</svg>
```

### Cambiar el separador
Edita `components/templates/breadcrumbs/breadcrumbs.html` línea ~18:

```html
<!-- Separador actual: Chevron derecha (>) -->
<svg class="w-4 h-4 mx-2 text-slate-500" 
     fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
          d="M9 5l7 7-7 7" />
</svg>
```

### Cambiar colores
```css
/* Enlaces */
text-slate-300 hover:text-white  /* Color actual */

/* Elemento activo */
text-white font-medium  /* Color actual */

/* Separador */
text-slate-500  /* Color actual */
```

---

## 📝 Ejemplo de Implementación Completa

### Vista (views.py)
```python
@login_required
def product_detail_view(request, asin):
    product = get_object_or_404(Product, asin=asin)
    
    # Breadcrumbs
    breadcrumbs = [
        {'text': 'Inicio', 'url': '/dashboard/'},
        {'text': 'Productos', 'url': '/products/list/'},
        {'text': product.title[:30] + '...'},  # Sin URL, página actual
    ]
    
    context = {
        'product': product,
        'breadcrumbs': breadcrumbs,
    }
    
    return render(request, 'products/detail.html', context)
```

### Template (detail.html)
```django
{% extends "base.html" %}
{% load static %}

{% block content %}
{% component "header" %}{% endcomponent %}

<main class="min-h-screen pb-12">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <!-- Breadcrumbs -->
        {% component "breadcrumbs" items=breadcrumbs %}{% endcomponent %}
        
        <!-- Contenido de la página -->
        <div class="glass-card p-6">
            <h1>{{ product.title }}</h1>
            <!-- ... resto del contenido ... -->
        </div>
    </div>
</main>

{% component "footer" %}{% endcomponent %}
{% endblock %}
```

---

## 🎯 Beneficios

1. **Navegación Mejorada**
   - Los usuarios siempre saben dónde están
   - Fácil volver a páginas anteriores

2. **UX en Móviles**
   - Cuando el header se oculta al hacer scroll
   - Alternativa al menú hamburguesa

3. **SEO**
   - Estructura de navegación clara
   - Atributo `aria-current="page"` para accesibilidad

4. **Consistencia**
   - Mismo componente en toda la app
   - Estilo Glass 2025 unificado

---

## 🚀 Próximas Implementaciones Sugeridas

### Páginas pendientes:
- [ ] Detalle de Producto (`/products/detail/<asin>/`)
- [ ] Lista de Alertas (`/products/alerts/`)
- [ ] Crear Alerta (`/products/alert/create/<asin>/`)
- [ ] Eliminar Alerta (`/products/alert/delete/<id>/`)
- [ ] Centro de Notificaciones (`/products/notifications/`)

### Ejemplo para Detalle de Producto:
```python
breadcrumbs = [
    {'text': 'Inicio', 'url': '/dashboard/'},
    {'text': 'Productos', 'url': '/products/list/'},
    {'text': product.title[:50] + '...' if len(product.title) > 50 else product.title},
]
```

---

## 📱 Responsive

El breadcrumb es completamente responsive:

```html
<!-- flex-wrap permite que los items se ajusten -->
<ol class="flex items-center flex-wrap gap-2 text-sm">
    <!-- items -->
</ol>
```

**Comportamiento:**
- Desktop: Una sola línea
- Tablet: Una sola línea (texto más pequeño)
- Mobile: Puede ocupar 2+ líneas si es necesario

---

## ♿ Accesibilidad

- ✅ `<nav>` con `aria-label="Breadcrumb"`
- ✅ `<ol>` para lista ordenada semántica
- ✅ `aria-current="page"` en el último elemento
- ✅ Contraste de colores adecuado (WCAG AA)
- ✅ Iconos decorativos (no afectan screen readers)

---

**Creado:** 1 de Noviembre, 2025  
**Versión:** 1.0.0  
**Estado:** ✅ Implementado y Documentado

