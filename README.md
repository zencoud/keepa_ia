# Keepa IA - Sistema de Análisis de Precios de Amazon

Sistema web desarrollado con Django para análisis y seguimiento de precios de productos de Amazon mediante la API de Keepa.

---

## ⚡ Patrón de Mensajes Flash (POST-REDIRECT-GET)

Este proyecto usa el patrón **POST-REDIRECT-GET (PRG)** para mensajes flash, similar a Laravel:

### ❌ NO hacer esto:
```python
if error:
    messages.error(request, 'Error message')
    return render(request, 'template.html')  # ❌ El mensaje persiste al recargar
```

### ✅ SIEMPRE hacer esto:
```python
if error:
    messages.error(request, 'Error message')
    return redirect('view_name')  # ✅ El mensaje se muestra una vez y desaparece
```

### Renderizar mensajes en templates:
```django
{% load messages_tags %}
{% render_flash_messages %}
```

**Este patrón asegura que:**
- ✅ Los mensajes solo se muestran una vez
- ✅ No aparecen al recargar la página (F5)
- ✅ Se comportan como los flash messages de Laravel

---

## 🎨 Línea de Estilo: Glass 2025

### Filosofía de Diseño

**Glass 2025** es una línea de diseño moderno que combina **glassmorphism** con un enfoque minimalista y elegante, creando interfaces limpias y contemporáneas.

### Principios Fundamentales

1. **Glassmorphism**: Efectos de vidrio esmerilado con `backdrop-blur` y transparencias
2. **Border-radius Prolongado**: Bordes muy redondeados (`rounded-2xl` para cards, `rounded-xl` para botones) que mejoran el efecto glass
3. **Minimalismo**: Diseño limpio sin elementos innecesarios
4. **Iconografía**: Uso exclusivo de **Heroicons** (https://heroicons.com/) - NO usar emojis
5. **Espaciado Generoso**: Breathing room entre elementos
6. **Micro-interacciones**: Transiciones suaves y hover effects sutiles

### Componentes de Estilo

#### Glass Cards
```html
<!-- Card básica con efecto glass -->
<div class="glass-card">
  Contenido
</div>

<!-- Card con efecto hover -->
<div class="glass-card glass-card-hover">
  Contenido interactivo
</div>
```

**Características (Optimizado para fondo oscuro):**
- `bg-white/10`: Fondo blanco con 10% de opacidad (transparente)
- `backdrop-blur-xl`: Desenfoque de fondo pronunciado (efecto glass)
- `border border-white/20`: Borde sutil blanco semitransparente
- `ring-1 ring-white/10`: Anillo de sombra blanca muy sutil
- `shadow-xl shadow-black/20`: Sombra oscura para profundidad
- `rounded-2xl`: Border-radius prolongado para mejor efecto glassmorphism ⭐

#### Botones
```html
<!-- Primario -->
<button class="btn-primary">Acción Principal</button>

<!-- Secundario -->
<button class="btn-secondary">Acción Secundaria</button>

<!-- Peligro -->
<button class="btn-danger">Eliminar</button>

<!-- Éxito -->
<button class="btn-success">Confirmar</button>
```

**Características:**
- Border-radius prolongado: `rounded-xl` para consistencia con glassmorphism
- Gradientes con sombras para profundidad
- Efectos hover suaves con escalado

#### Navbar (Glass Header)
```html
<header class="navbar sticky top-0 z-50">
  <!-- Contenido del header -->
</header>
```

**Características:**
- Efecto glass con `bg-white/10 backdrop-blur-xl` (optimizado para fondo oscuro)
- Sticky positioning
- Z-index alto para superposición
- Bordes y sombras sutiles con transparencias

#### Iconos - Heroicons

**IMPORTANTE**: Usar exclusivamente iconos de Heroicons. NO usar emojis.

```html
<!-- Ejemplo: Icono de búsqueda (outline) -->
<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
</svg>

<!-- Ejemplo: Icono de búsqueda (solid) -->
<svg class="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
  <path fill-rule="evenodd" d="M10.5 3.75a6.75 6.75 0 100 13.5 6.75 6.75 0 000-13.5zM2.25 10.5a8.25 8.25 0 1114.59 5.28l4.69 4.69a.75.75 0 11-1.06 1.06l-4.69-4.69A8.25 8.25 0 012.25 10.5z" clip-rule="evenodd" />
</svg>
```

**Guía de uso:**
- Ir a https://heroicons.com/
- Copiar el SVG del icono (outline, solid, mini, o micro según necesidad)
- Ajustar tamaño con clases Tailwind: `w-4 h-4`, `w-5 h-5`, `w-6 h-6`, etc.
- Usar `fill="currentColor"` o `stroke="currentColor"` para heredar color del texto

#### Colores Keepa

```css
/* Azul Keepa */
keepa-blue-50 hasta keepa-blue-900

/* Verde Keepa */
keepa-green-50 hasta keepa-green-900
```

#### Utilidades

```html
<!-- Texto con gradiente -->
<span class="text-gradient">Texto con Gradiente</span>

<!-- Fondo glass con gradiente -->
<div class="bg-gradient-glass">Contenido</div>
```

### Referencias para Prompts Futuros

**Línea de Estilo:**
- "Implementar usando la línea de estilo Glass 2025"
- "Aplicar glassmorphism con las clases estándar del proyecto"
- "Usar exclusivamente iconos de Heroicons, no emojis"
- "Mantener consistencia con el sistema de diseño Glass 2025"

**Ejemplo de prompt:**
```
Crea un nuevo componente siguiendo la línea de estilo Glass 2025:
- Usar clases glass-card para contenedores (border-radius rounded-2xl)
- Botones e inputs con rounded-xl para consistencia
- Implementar iconos de Heroicons (no emojis)
- Aplicar transiciones suaves
- Mantener el esquema de colores Keepa
- Texto blanco/claro para fondo oscuro
```

#### Border-Radius en Glass 2025

El sistema usa **border-radius prolongados** para mejorar el efecto glassmorphism:

- **Cards/Contenedores**: `rounded-2xl` (16px) - Para `.glass-card` y elementos principales
- **Botones/Inputs**: `rounded-xl` (12px) - Para `.btn-*` y `.form-input`
- **Elementos pequeños**: `rounded-lg` (8px) - Para badges y elementos secundarios

**Razón**: Los bordes más redondeados crean un efecto más suave y moderno, típico del glassmorphism, mejorando la percepción de profundidad y transparencia.

### Paleta de Colores

La paleta completa está definida en `theme/static_src/tailwind.config.js` para facilitar cambios rápidos.

#### Colores Principales

- **Keepa Blue** (Principal):
  - `600`: `#0284c7` - Botones principales ⭐
  - `700`: `#0369a1` - Hover de botones ⭐
  - Usado para: botones principales, enlaces, acentos, gradientes

- **Keepa Green** (Éxito):
  - `600`: `#059669` - Botones de éxito ⭐
  - `700`: `#047857` - Hover ⭐
  - Usado para: acciones exitosas, confirmaciones, badges de éxito

- **Keepa Orange** (Advertencia/Destacado):
  - `600`: `#ea580c` - Botones de advertencia ⭐
  - `700`: `#c2410c` - Hover ⭐
  - Usado para: alertas, elementos destacados, llamadas a la acción

- **Red** (Peligro):
  - `600`: `#dc2626` - Botones de peligro
  - `700`: `#b91c1c` - Hover
  - Usado para: acciones destructivas, errores

#### Fondo Oscuro para Glassmorphism

El diseño usa un **fondo oscuro con gradiente** para optimizar el efecto glassmorphism:
- Gradiente: `from-slate-900 via-indigo-950 to-slate-900`
- Configuración: `theme/static_src/src/styles.css` (línea 8-11)
- Para cambiar: modifica el `body` en `styles.css` y recompila Tailwind

#### Cambiar la Paleta

Para cambiar los colores del sistema:

1. Edita `theme/static_src/tailwind.config.js`
2. Modifica los valores hex en la sección `colors`
3. Recompila Tailwind:
   ```bash
   cd theme/static_src
   npm run build
   ```

**Nota**: Todos los componentes están diseñados para trabajar con el fondo oscuro. Si cambias a fondo claro, ajusta también los componentes glass en `styles.css`.

---

## 🚀 Instalación y Configuración

### Requisitos

- Python 3.13+
- Django 5.2+
- MySQL/MariaDB (o SQLite para desarrollo)
- Node.js y npm (para Tailwind CSS)

### Instalación

1. Clonar el repositorio
2. Crear y activar entorno virtual:
   ```bash
   python -m venv venv
   source venv/bin/activate  # En Windows: venv\Scripts\activate
   ```

3. Instalar dependencias:
   ```bash
   pip install -r requirements.txt
   ```

4. Configurar variables de entorno:
   ```bash
   cp env.example .env
   # Editar .env con tus configuraciones
   ```

5. Compilar CSS con Tailwind:
   ```bash
   cd theme/static_src
   npm install
   npm run build
   ```

6. Ejecutar migraciones:
   ```bash
   python manage.py migrate
   ```

7. Crear superusuario:
   ```bash
   python manage.py createsuperuser
   # O usar el comando personalizado:
   python manage.py create_default_superuser
   ```

8. Ejecutar servidor de desarrollo:
   ```bash
   python manage.py runserver
   ```

## 📁 Estructura del Proyecto

```
keepa_ia/
├── accounts/          # Autenticación de usuarios
├── products/          # Gestión de productos y alertas
├── components/        # Componentes Django reutilizables
├── theme/             # Temas y estilos (Tailwind CSS)
├── keepa_ia/          # Configuración principal Django
└── staticfiles/       # Archivos estáticos compilados
```

## 🧩 Estructura de Componentes

### Regla Fundamental: Un Solo Template por Componente

**IMPORTANTE**: Todos los templates de componentes deben estar ÚNICAMENTE en `components/templates/component_name/component_name.html`

### Estructura Correcta

```
components/
├── component_name/
│   ├── __init__.py
│   └── component.py          # template_name = "component_name/component_name.html"
│
└── templates/                # ✅ ÚNICO lugar para templates
    └── component_name/
        └── component_name.html
```

### ❌ NO Crear Archivos Duplicados

**NUNCA** crear templates en:
- ❌ `components/component_name/component_name.html`
- ❌ Cualquier otro lugar fuera de `components/templates/`

**SIEMPRE** crear templates en:
- ✅ `components/templates/component_name/component_name.html`

### Verificación

Para verificar que no hay duplicados:

```bash
find components -name "*.html" -not -path "*/templates/*" -type f
```

Este comando debe devolver **0 archivos**.

### Documentación Completa

Ver `components/COMPONENT_STRUCTURE.md` para documentación detallada sobre estructura de componentes.

## 🔧 Configuración

### Variables de Entorno Requeridas

Ver `env.example` para la lista completa de variables. Las principales son:

- `SECRET_KEY`: Clave secreta de Django
- `DEBUG`: Modo debug (True/False)
- `KEEPA_API_KEY`: API Key de Keepa
- Configuración de base de datos MySQL
- Configuración de email (para notificaciones)

## 📝 Licencia

MIT License

