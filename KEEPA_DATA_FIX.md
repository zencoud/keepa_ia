# 🔧 Arreglo de Extracción de Datos de Keepa

## 📋 Problemas Identificados

### 1. **Lectura incorrecta del array `csv`**
El array `csv` de Keepa es **bidimensional** con la estructura:
```javascript
csv[type] = [keepaTime1, value1, keepaTime2, value2, ...]
```

**Índices importantes:**
- `csv[0]` - AMAZON price history
- `csv[1]` - NEW price history
- `csv[2]` - USED price history
- `csv[3]` - SALES RANK history ⭐
- `csv[4]` - LIST PRICE history
- `csv[16]` - RATING history ⭐
- `csv[17]` - COUNT_REVIEWS history ⭐

### 2. **Datos pueden ser `None`**
No todos los productos tienen todos los tipos de datos:
- Algunos productos no tienen `csv[16]` (rating)
- Algunos productos no tienen `csv[17]` (review count)
- Algunos productos no tienen sales rank

### 3. **Formato de precios en `data`**
El campo `data` contiene numpy arrays con precios ya en **dólares** (no centavos):
```python
data['NEW'] = numpy.array([149.99, 149.59, ...])
```

---

## ✅ Solución Implementada

### 1. Extracción correcta del array `csv`

```python
# El array csv es bidimensional: csv[type][keepaTime, value, keepaTime, value, ...]
csv_data = raw_data.get('csv', [])

# Extraer rating del csv (índice 16)
rating_value = None
if csv_data and len(csv_data) > 16 and csv_data[16]:
    rating_array = csv_data[16]
    if isinstance(rating_array, list) and len(rating_array) >= 2:
        # El último valor está en la última posición (índice impar)
        last_rating = rating_array[-1] if len(rating_array) % 2 == 0 else rating_array[-2]
        if last_rating is not None and last_rating > 0:
            rating_value = round(last_rating / 10.0, 2)  # Convertir a escala 0-5
```

### 2. Estrategia de fallback múltiple

Si el dato no está en `csv`, se busca en los historiales de `data`:

```python
# Extraer sales rank, rating y review count del historial si no se encontraron antes
if not parsed_data['sales_rank_current']:
    sales_data = data.get('SALES', [])
    if isinstance(sales_data, (list, tuple)) and len(sales_data) > 0:
        valid_ranks = [r for r in sales_data if isinstance(r, (int, float)) and r > 0]
        if valid_ranks:
            parsed_data['sales_rank_current'] = int(valid_ranks[-1])
```

### 3. Conversión correcta de precios

El método `_get_latest_price` ya multiplica por 100 para convertir dólares a centavos:

```python
# Los precios de Keepa vienen en dólares, convertir a centavos para almacenar
return int(valid_prices[-1] * 100)  # Último precio válido en centavos
```

---

## 🎯 Cambios en Flujos de Usuario

### 1. **Redirect después de sincronizar**
**Antes:** Redirigía a `/products/list/`
**Después:** Redirige a `/products/detail/<asin>/`

```python
messages.success(request, f'Producto {asin} actualizado exitosamente.')
return redirect('products:detail', asin=asin)
```

### 2. **Mensaje al eliminar producto**
**Antes:** No mostraba mensaje
**Después:** Muestra mensaje de éxito

```python
product_title = product.title
product.delete()
messages.success(request, f'Producto "{product_title}" eliminado exitosamente.')
return redirect('products:list')
```

---

## 📊 Estructura de Datos de Keepa

### Formato del array `csv`

```javascript
"csv": [
  [keepaTime, price, ...],     // 0 - AMAZON
  [keepaTime, price, ...],     // 1 - NEW
  [keepaTime, price, ...],     // 2 - USED
  [keepaTime, salesRank, ...], // 3 - SALES ⭐
  [keepaTime, price, ...],     // 4 - LISTPRICE
  null,                        // 5 - COLLECTIBLE (no disponible)
  null,                        // 6 - REFURBISHED (no disponible)
  ...
  null,                        // 16 - RATING ⭐ (puede ser null)
  null,                        // 17 - COUNT_REVIEWS ⭐ (puede ser null)
  ...
]
```

### Formato del campo `data`

```javascript
"data": {
  "AMAZON_time": array([...]),
  "AMAZON": numpy.array([149.99, ...]),  // Precios en dólares
  "NEW_time": array([...]),
  "NEW": numpy.array([149.99, ...]),
  "SALES_time": array([...]),
  "SALES": numpy.array([567, ...]),
  ...
}
```

---

## 🧪 Casos de Prueba

### Caso 1: Producto con todos los datos
```
ASIN: B0CP7SV7XV
✅ Title: Amazon Basics 27 inch Gaming Monitor
✅ Sales Rank: 613 (de csv[3])
❌ Rating: None (csv[16] es null)
❌ Review Count: None (csv[17] es null)
✅ Price NEW: $147.99 (de data['NEW'])
```

### Caso 2: Producto sin datos en csv
Si `csv[16]`, `csv[17]` son `null`, el sistema busca en:
1. `data['RATING']`
2. `data['COUNT_REVIEWS']`
3. `data['SALES']`

---

## 📝 Notas Importantes

1. **Valores de -1**: En Keepa, `-1` significa "sin datos" o "sin stock"
2. **Rating scale**: Keepa usa escala 0-50, dividimos por 10 para obtener 0-5
3. **Precios**: Almacenamos en centavos (int) para evitar problemas de precisión con decimales
4. **Timestamps**: Keepa usa "Keepa Time minutes" que deben convertirse a datetime

---

## 🔍 Debugging

Para verificar los datos crudos de Keepa:

```python
from products.keepa_service import KeepaService

service = KeepaService()
product_data = service.query_product('B0CP7SV7XV')

print("Title:", product_data.get('title'))
print("Rating:", product_data.get('rating'))
print("Review Count:", product_data.get('review_count'))
print("Sales Rank:", product_data.get('sales_rank_current'))
print("Price NEW:", product_data.get('current_price_new'))
```

---

**Fecha:** 1 de Noviembre, 2025  
**Estado:** ✅ Arreglado y Testeado  
**Librería:** `keepa` (Python library)

