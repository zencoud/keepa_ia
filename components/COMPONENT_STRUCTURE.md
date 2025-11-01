# Estructura de Componentes - Keepa IA

## 📁 Estructura Correcta

Todos los componentes Django deben seguir esta estructura:

```
components/
├── component_name/
│   ├── __init__.py
│   └── component.py          # Define el componente con template_name
│
└── templates/
    └── component_name/
        └── component_name.html   # Template del componente (ÚNICO LUGAR)
```

## ✅ Ejemplo Correcto

### `components/alert/component.py`
```python
from django_components import component

@component.register("alert")
class Alert(component.Component):
    template_name = "alert/alert.html"  # Busca en components/templates/alert/alert.html
```

### Template: `components/templates/alert/alert.html`
```html
<!-- Template del componente alert -->
```

## ❌ Estructura Incorrecta (NO hacer esto)

```
components/
├── alert/
│   ├── component.py
│   └── alert.html          ❌ NO DEBE EXISTIR aquí
│
└── templates/
    └── alert/
        └── alert.html      ✅ Este es el correcto
```

## 🎯 Reglas Importantes

1. **Solo un template por componente**: El template debe estar ÚNICAMENTE en `components/templates/component_name/component_name.html`

2. **No duplicar templates**: Si encuentras un archivo `.html` en la carpeta del componente (`components/component_name/`), debe eliminarse.

3. **Component.py referencia relativa**: El `template_name` en `component.py` debe ser relativo a `components/templates/`, ejemplo:
   - `template_name = "alert/alert.html"` → busca `components/templates/alert/alert.html`
   - `template_name = "dashboard_card/dashboard_card.html"` → busca `components/templates/dashboard_card/dashboard_card.html`

## 🔍 Cómo Verificar

Para verificar que no hay duplicados, ejecuta:

```bash
find components -name "*.html" -not -path "*/templates/*" -type f
```

Este comando debe devolver **0 archivos**. Si encuentra alguno, debe eliminarse.

## 📝 Checklist para Nuevos Componentes

- [ ] Crear carpeta `components/nuevo_componente/`
- [ ] Crear `__init__.py` en la carpeta
- [ ] Crear `component.py` con `template_name = "nuevo_componente/nuevo_componente.html"`
- [ ] Crear template ÚNICAMENTE en `components/templates/nuevo_componente/nuevo_componente.html`
- [ ] Verificar que NO existe `components/nuevo_componente/nuevo_componente.html`

## 🛠️ Componentes Actuales

| Componente | Template Correcto | Estado |
|------------|-------------------|--------|
| alert | `templates/alert/alert.html` | ✅ Limpio |
| footer | `templates/footer/footer.html` | ✅ Limpio |
| header | `templates/header/header.html` | ✅ Limpio |
| stats_card | `templates/stats_card/stats_card.html` | ✅ Limpio |
| pagination | `templates/pagination/pagination.html` | ✅ Limpio |
| product_card | `templates/product_card/product_card.html` | ✅ Limpio |
| empty_state | `templates/empty_state/empty_state.html` | ✅ Limpio |
| card | `templates/card/card.html` | ✅ Limpio |
| badge | `templates/badge/badge.html` | ✅ Limpio |
| button | `templates/button/button.html` | ✅ Limpio |
| dashboard_card | `templates/dashboard_card/dashboard_card.html` | ✅ Limpio |

## 🗑️ Carpetas Eliminadas

- `form_input/` - Carpeta vacía sin componente definido
- `sidebar/` - Carpeta vacía sin componente definido

