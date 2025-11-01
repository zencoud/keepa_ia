# Fix: Mensajes Flash Perpetuos (Resuelto)

## 🐛 Problema Original
Los mensajes de error persistían al recargar la página (F5), apareciendo indefinidamente.

## 🔍 Causa Raíz
Se usaba `return render()` después de agregar mensajes con `messages.error()`:

```python
# ❌ INCORRECTO - Causa mensajes perpetuos
messages.error(request, 'Error message')
return render(request, 'template.html')  # El mensaje NO se consume
```

Cuando se usa `render()` en una request POST:
1. ✅ El mensaje se agrega a la sesión
2. ✅ El template se renderiza y muestra el mensaje
3. ❌ **PERO** el mensaje NO se consume de la sesión
4. ❌ Al recargar (F5), el navegador hace un GET y el mensaje SIGUE ahí
5. ❌ El mensaje aparece indefinidamente

## ✅ Solución: Patrón POST-REDIRECT-GET (PRG)

### Patrón Implementado (similar a Laravel)
```python
# ✅ CORRECTO - Mensaje se muestra UNA sola vez
messages.error(request, 'Error message')
return redirect('view_name')  # El mensaje se consume en el siguiente GET
```

### Cómo funciona:
1. ✅ POST: Se agrega el mensaje a la sesión
2. ✅ REDIRECT: Se redirige al navegador (código HTTP 302)
3. ✅ GET: El navegador hace una nueva request GET
4. ✅ RENDER: Se renderiza el template y se consume el mensaje
5. ✅ Al recargar (F5), el mensaje YA NO está en la sesión

## 📝 Archivos Modificados

### 1. `products/views.py`
- ✅ `search_product_view()`: Todos los errores ahora redirigen con `redirect('products:search')`
- ✅ `create_alert_view()`: Todos los errores ahora redirigen con `redirect('products:create_alert', asin=asin)`

### 2. Template Tag Personalizado
- ✅ `products/templatetags/messages_tags.py`: Tag `render_flash_messages` que consume mensajes automáticamente
- ✅ `products/templates/products/flash_messages.html`: Template parcial para renderizar mensajes

### 3. Templates Actualizados
- ✅ `products/templates/products/search.html`: Usa `{% render_flash_messages %}`
- ✅ `accounts/templates/accounts/home.html`: Usa `{% render_flash_messages %}`

### 4. Configuración
- ✅ `keepa_ia/settings.py`: Configurado `MESSAGE_STORAGE` y `MESSAGE_TAGS`

### 5. Documentación
- ✅ `README.md`: Sección "⚡ Patrón de Mensajes Flash (POST-REDIRECT-GET)" agregada

## 🧪 Prueba
1. Busca un producto con ASIN inválido → Verás mensaje de error
2. Recarga la página (F5) → El mensaje NO aparece
3. ✅ Problema resuelto

## 📚 Referencia para Futuros Desarrollos

### Regla de Oro
**NUNCA usar `return render()` después de `messages.add()` o `messages.error()`**

### Pattern a seguir SIEMPRE:
```python
# En POST con error/success
if error:
    messages.error(request, 'Mensaje')
    return redirect('view_name')  # ✅ Siempre redirect

# En GET
return render(request, 'template.html')  # ✅ Solo render en GET
```

### Renderizar mensajes en templates:
```django
{% extends "base.html" %}
{% load messages_tags %}

{% block content %}
    {% render_flash_messages %}
    
    <!-- Resto del contenido -->
{% endblock %}
```

---

**Fecha:** 1 de Noviembre, 2025  
**Estado:** ✅ Resuelto

