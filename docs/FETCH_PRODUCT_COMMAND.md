# Comando fetch_product

Este comando permite obtener información de productos desde la API de Keepa para testing y desarrollo.

## Uso

```bash
python manage.py fetch_product ASIN1 ASIN2 ... [opciones]
```

## Opciones

- `--username USERNAME`: Usuario que consultará el producto (por defecto usa el primer superuser)
- `--force`: Forzar actualización aunque el producto ya exista en la base de datos

## Ejemplos

### Consultar un solo producto

```bash
python manage.py fetch_product B07X6C9RMF
```

### Consultar múltiples productos

```bash
python manage.py fetch_product B07X6C9RMF B0DJZ8SH7H
```

### Consultar producto con un usuario específico

```bash
python manage.py fetch_product B07X6C9RMF --username admin
```

### Forzar actualización de un producto existente

```bash
python manage.py fetch_product B07X6C9RMF --force
```

## ASINs de Prueba Válidos

Los siguientes ASINs son válidos para pruebas:

- `B07X6C9RMF` - Producto de prueba 1
- `B0DJZ8SH7H` - Producto de prueba 2

## Salida

El comando muestra:

- ✓ Éxito al obtener y guardar el producto
- ⚠ Advertencias (producto ya existe)
- ✗ Errores (ASIN inválido, API error, etc.)

Para cada producto exitoso muestra:

- Título
- Marca
- Rating y número de reseñas
- Sales Rank
- Precios (nuevo, Amazon, usado)
- Categorías

## Notas

- El comando requiere que `KEEPA_API_KEY` esté configurada en el archivo `.env`
- Los datos se guardan en la base de datos para su visualización en el panel
- Si el producto ya existe, usa `--force` para actualizarlo

