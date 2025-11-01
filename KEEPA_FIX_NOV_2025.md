# Correcciones de Keepa API - Noviembre 2025

## 📋 Resumen de Problemas Solucionados

### 1. ✅ Historial de Sales Rank No Se Mostraba
**Problema:** El historial de ventas (sales rank) no aparecía en la sección de detalle del producto.

**Solución:**
- Agregada nueva gráfica de Sales Rank en `products/templates/products/detail.html`
- Implementada extracción correcta de datos desde la API de Keepa usando el campo `stats`
- Configuración de escala dinámica para mejor visualización (no desde 0)

### 2. ✅ Sin Información de Calificación, Reseñas y Sales Rank
**Problema:** No se obtenía información de rating, review count ni sales rank de los productos.

**Solución:**
- Actualizado `products/keepa_service.py` para extraer datos desde múltiples fuentes:
  - Primero desde `stats.current` (más confiable)
  - Fallback a `csv` array si no hay stats
  - Fallback a campos directos de raw_data
- Rating convertido correctamente de escala 0-50 a 0-5
- Review count extraído del índice 17 del array CSV
- Sales rank extraído del índice 3 del array CSV

### 3. ✅ Categorías Como Números en Lugar de Nombres
**Problema:** Las categorías aparecían como IDs numéricos en lugar de nombres legibles.

**Solución:**
- Nueva función `_extract_category_names()` en `keepa_service.py`
- Extracción de nombres desde `categoryTree` (contiene nombres completos)
- Fallback a `categories` solo si contiene strings (no IDs numéricos)
- Filtrado automático de IDs numéricos para mostrar solo nombres

### 4. ✅ Gráficas con Mala Visualización
**Problema:** Las gráficas eran muy bajas y comenzaban desde 0, dificultando ver cambios.

**Solución:**
- Altura fija de 400px para todas las gráficas
- Escala dinámica calculada automáticamente con margen de 10%
- Uso de `stepped: 'before'` para representar datos discontinuos correctamente
- Tres gráficas separadas:
  - **Historial de Precios:** Muestra precio nuevo, Amazon y usado
  - **Historial de Sales Rank:** Visualiza ranking de ventas
  - **Historial de Rating:** Muestra evolución de calificaciones

## 🔧 Cambios Técnicos

### Archivo: `products/keepa_service.py`

#### 1. Query con Parámetros Adicionales
```python
# Antes
products = self.api.query(asin)

# Ahora
products = self.api.query(asin, history=True, stats=90, rating=True)
```

#### 2. Extracción de Stats
```python
# Nuevo código para extraer desde stats
stats = raw_data.get('stats', {})
if stats:
    current_rating = stats.get('current', {})
    if current_rating and len(current_rating) > 16:
        avg_rating = current_rating[16]  # Índice 16 es RATING
        if avg_rating is not None and avg_rating > 0:
            rating_value = round(avg_rating / 10.0, 1)
```

#### 3. Nueva Función de Categorías
```python
def _extract_category_names(self, raw_data: Dict[str, Any]) -> List[str]:
    """Extrae nombres de categorías de los datos de Keepa"""
    category_names = []
    
    # Intentar extraer desde categoryTree (tiene nombres y IDs)
    category_tree = raw_data.get('categoryTree', [])
    if category_tree and isinstance(category_tree, list):
        for category in category_tree:
            if isinstance(category, dict):
                name = category.get('name', '')
                if name and name not in category_names:
                    category_names.append(name)
    
    return category_names
```

### Archivo: `products/templates/products/detail.html`

#### 1. Nuevas Gráficas
```html
<!-- Sales Rank History Chart -->
<div class="glass-card p-6">
    <h2 class="text-2xl font-bold text-white mb-4 flex items-center">
        <svg class="w-6 h-6 mr-2 text-purple-400">...</svg>
        Historial de Sales Rank
    </h2>
    <div class="bg-white/5 rounded-[40px] p-6" style="height: 400px;">
        <canvas id="salesRankChart"></canvas>
    </div>
</div>

<!-- Rating History Chart -->
<div class="glass-card p-6">
    <h2 class="text-2xl font-bold text-white mb-4 flex items-center">
        <svg class="w-6 h-6 mr-2 text-keepa-green-400">...</svg>
        Historial de Calificaciones
    </h2>
    <div class="bg-white/5 rounded-[40px] p-6" style="height: 400px;">
        <canvas id="ratingChart"></canvas>
    </div>
</div>
```

#### 2. JavaScript Mejorado
```javascript
// Cálculo de escala dinámica para precios
const allPrices = [
    ...(newPrices.prices || []).map(p => p / 100),
    ...(amazonPrices.prices || []).map(p => p / 100),
    ...(usedPrices.prices || []).map(p => p / 100)
].filter(p => p > 0);

const minPrice = Math.min(...allPrices);
const maxPrice = Math.max(...allPrices);
const priceRange = maxPrice - minPrice;
const priceMin = Math.max(0, minPrice - (priceRange * 0.1));
const priceMax = maxPrice + (priceRange * 0.1);

// Uso de stepped line para datos discontinuos
datasets: [{
    tension: 0.1,
    stepped: 'before',  // Importante para historial de precios
    borderWidth: 2
}]
```

### Nuevo Comando: `fetch_product`

Comando de management para obtener productos desde Keepa API:

```bash
python manage.py fetch_product B07X6C9RMF B0DJZ8SH7H
```

**Características:**
- ✅ Consulta uno o múltiples productos
- ✅ Muestra información detallada en consola
- ✅ Opción `--force` para actualizar productos existentes
- ✅ Opción `--username` para especificar usuario
- ✅ Validación de formato ASIN
- ✅ Manejo de errores robusto

**Salida del comando:**
```
Usuario: admin
ASINs a consultar: B07X6C9RMF

--------------------------------------------------------------------------------
Procesando ASIN: B07X6C9RMF
--------------------------------------------------------------------------------
  ✓ Datos obtenidos exitosamente
    Título: Blink Mini - Compact indoor plug-in smart security camera...
    Marca: Blink
    Rating: 4.4
    Reviews: 305073
    Sales Rank: 4131
    Precios:
      Nuevo: $29.99
      Amazon: $29.99
      Usado: $24.15
    Categorías: Home & Kitchen, Storage & Organization
  ✓ Producto actualizado exitosamente
```

## 📊 Resultados

### Datos Extraídos Correctamente

#### Producto 1: B07X6C9RMF (Blink Mini Camera)
- ✅ Rating: 4.4 ⭐
- ✅ Reviews: 305,073
- ✅ Sales Rank: #4,131
- ✅ Categorías: Home & Kitchen, Storage & Organization
- ✅ Precios: $29.99 (Nuevo), $29.99 (Amazon), $24.15 (Usado)

#### Producto 2: B0DJZ8SH7H (Gawfolk Gaming Monitor)
- ✅ Rating: 4.4 ⭐
- ✅ Reviews: 1,260
- ✅ Sales Rank: #2,887
- ✅ Categorías: Electronics, Computers & Accessories, Monitors
- ✅ Precios: $94.99 (Nuevo), $90.13 (Usado)

### Visualización de Gráficas

Las tres gráficas ahora muestran:

1. **Historial de Precios**
   - Tres líneas: Precio Nuevo (azul), Amazon (naranja), Usado (verde)
   - Escala dinámica basada en rango de precios
   - Altura: 400px
   - Step line para representar datos discontinuos

2. **Historial de Sales Rank**
   - Una línea morada con área rellena
   - Escala dinámica (no desde 0)
   - Formato: #N,NNN con separadores de miles
   - Altura: 400px

3. **Historial de Rating**
   - Una línea verde con área rellena
   - Escala fija: 0-5 estrellas
   - Formato: N.N ⭐
   - Altura: 400px

## 📚 Documentación Actualizada

- ✅ `README.md` - Agregada sección de comandos de management
- ✅ `docs/FETCH_PRODUCT_COMMAND.md` - Documentación completa del comando
- ✅ `KEEPA_FIX_NOV_2025.md` - Este archivo con resumen de cambios

## 🧪 Testing

### Comandos para Testing

```bash
# Obtener un producto
python manage.py fetch_product B07X6C9RMF

# Obtener múltiples productos
python manage.py fetch_product B07X6C9RMF B0DJZ8SH7H

# Actualizar producto existente
python manage.py fetch_product B07X6C9RMF --force
```

### Verificación Manual

1. Ejecutar comando fetch_product con ASIN válido
2. Verificar en consola que se muestren:
   - Rating
   - Review count
   - Sales rank
   - Categorías (nombres, no números)
   - Precios
3. Acceder a la URL del producto en el navegador
4. Verificar que se muestren las 3 gráficas:
   - Historial de Precios
   - Historial de Sales Rank
   - Historial de Calificaciones
5. Verificar que las categorías aparezcan como nombres legibles

## 🔗 Referencias

- [Keepa API Documentation](https://keepaapi.readthedocs.io/en/latest/product_query.html#product-history-query)
- ASINs de prueba válidos:
  - `B07X6C9RMF` - Blink Mini Security Camera
  - `B0DJZ8SH7H` - Gawfolk Gaming Monitor

## 📝 Notas Técnicas

### Formato de Datos Keepa

- **Rating:** Escala 0-50 (dividir entre 10 para obtener 0-5)
- **Precios:** En dólares (multiplicar por 100 para almacenar en centavos)
- **Sales Rank:** Entero positivo (menor es mejor)
- **CSV Array:** [keepaTime, value, keepaTime, value, ...]
  - Índice 3: SALES (Sales Rank)
  - Índice 16: RATING
  - Índice 17: COUNT_REVIEWS

### Jerarquía de Extracción

1. **Primero:** `stats.current[index]` - Datos estadísticos (más confiables)
2. **Segundo:** `csv[index]` - Array CSV con histórico
3. **Tercero:** Campos directos de raw_data

Esta jerarquía asegura que siempre obtengamos los datos más precisos disponibles.

---

**Fecha de implementación:** 1 de Noviembre, 2025
**Desarrollador:** Assistant
**Estado:** ✅ Completado y probado

