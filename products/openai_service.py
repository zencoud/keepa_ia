import openai
import logging
import re
from django.conf import settings
from typing import Dict, Any, Optional
from datetime import datetime
import json

logger = logging.getLogger(__name__)


class OpenAIService:
    """Servicio para interactuar con la API de OpenAI"""
    
    def __init__(self):
        """Inicializa el cliente de OpenAI con la API key"""
        self.api_key = settings.OPENAI_API_KEY
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY no está configurada en settings")
        
        self.client = openai.OpenAI(api_key=self.api_key)
    
    def generate_price_summary(self, product_data: Dict[str, Any]) -> Optional[str]:
        """
        Genera un resumen inteligente del historial de precios usando OpenAI
        
        Args:
            product_data: Dict con información del producto incluyendo price_history
            
        Returns:
            String con el resumen generado o None si hay error
        """
        try:
            # Extraer datos relevantes
            title = product_data.get('title', 'Producto')
            price_history = product_data.get('price_history', {})
            current_price_new = product_data.get('current_price_new')
            current_price_amazon = product_data.get('current_price_amazon')
            rating = product_data.get('rating')
            review_count = product_data.get('review_count')
            sales_rank = product_data.get('sales_rank_current')
            
            # Verificar que haya datos de precios
            if not price_history or all(not prices.get('prices') for prices in price_history.values()):
                logger.warning("No hay suficiente historial de precios para generar resumen")
                return None
            
            # Preparar datos de precios para el prompt
            price_data_summary = self._prepare_price_data_for_prompt(price_history)
            
            # Construir el prompt
            prompt = self._build_prompt(
                title=title,
                price_data_summary=price_data_summary,
                current_price_new=current_price_new,
                current_price_amazon=current_price_amazon,
                rating=rating,
                review_count=review_count,
                sales_rank=sales_rank
            )
            
            logger.info(f"Generando resumen de IA para producto: {title[:50]}...")
            
            # Llamar a OpenAI API
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Eres un analista de precios de Amazon experto y amigable. "
                            "Tu trabajo es ayudar a los usuarios a entender los patrones de precios "
                            "y tomar decisiones inteligentes de compra. Habla de forma natural y conversacional, "
                            "como si fueras su asesor personal de compras. Usa insights inteligentes, "
                            "identifica tendencias, y da recomendaciones estratégicas. "
                            "Puedes usar emojis sutilmente (máximo 2-3) para hacer el texto más visual. "
                            "Sé conciso pero informativo (3-5 oraciones)."
                        )
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.7,
                max_tokens=300,
                top_p=0.9,
            )
            
            summary = response.choices[0].message.content.strip()
            logger.info("Resumen de IA generado exitosamente")
            
            return summary
            
        except Exception as e:
            logger.error(f"Error generando resumen con OpenAI: {e}")
            return None
    
    def _prepare_price_data_for_prompt(self, price_history: Dict[str, Any]) -> str:
        """
        Prepara un resumen de los datos de precios para incluir en el prompt
        
        Args:
            price_history: Dict con el historial de precios
            
        Returns:
            String con resumen de precios formateado
        """
        summary_parts = []
        
        for price_type in ['NEW', 'AMAZON', 'USED']:
            if price_type in price_history:
                price_data = price_history[price_type]
                prices = price_data.get('prices', [])
                times = price_data.get('formatted_times', [])
                
                if prices and len(prices) > 0:
                    # Convertir de centavos a dólares
                    prices_dollars = [p / 100 for p in prices if p > 0]
                    
                    if prices_dollars:
                        min_price = min(prices_dollars)
                        max_price = max(prices_dollars)
                        avg_price = sum(prices_dollars) / len(prices_dollars)
                        current_price = prices_dollars[-1]
                        
                        # Calcular tendencia (comparar primeros 30% vs últimos 30%)
                        n = len(prices_dollars)
                        if n >= 6:
                            early_avg = sum(prices_dollars[:n//3]) / (n//3)
                            recent_avg = sum(prices_dollars[-n//3:]) / (n//3)
                            change_pct = ((recent_avg - early_avg) / early_avg) * 100
                            trend = "subió" if change_pct > 5 else "bajó" if change_pct < -5 else "se mantuvo estable"
                        else:
                            trend = "datos limitados"
                        
                        type_label = {
                            'NEW': 'Nuevo',
                            'AMAZON': 'Amazon',
                            'USED': 'Usado'
                        }.get(price_type, price_type)
                        
                        summary_parts.append(
                            f"{type_label}: ${current_price:.2f} actual, "
                            f"promedio ${avg_price:.2f}, rango ${min_price:.2f}-${max_price:.2f}, "
                            f"tendencia: {trend}"
                        )
        
        return "\n".join(summary_parts) if summary_parts else "Datos de precios limitados"
    
    def _build_prompt(
        self,
        title: str,
        price_data_summary: str,
        current_price_new: Optional[int],
        current_price_amazon: Optional[int],
        rating: Optional[float],
        review_count: Optional[int],
        sales_rank: Optional[int]
    ) -> str:
        """
        Construye el prompt para OpenAI
        
        Args:
            title: Título del producto
            price_data_summary: Resumen de datos de precios
            current_price_new: Precio actual nuevo (en centavos)
            current_price_amazon: Precio actual Amazon (en centavos)
            rating: Calificación del producto
            review_count: Número de reseñas
            sales_rank: Sales rank actual
            
        Returns:
            String con el prompt completo
        """
        # Construir información del producto
        product_info = f"Producto: {title}\n\n"
        
        # Agregar precios actuales
        if current_price_new:
            product_info += f"Precio actual (Nuevo): ${current_price_new / 100:.2f}\n"
        if current_price_amazon:
            product_info += f"Precio actual (Amazon): ${current_price_amazon / 100:.2f}\n"
        
        # Agregar métricas adicionales
        if rating:
            product_info += f"Calificación: {rating:.1f} estrellas\n"
        if review_count:
            product_info += f"Reseñas: {review_count:,}\n"
        if sales_rank:
            product_info += f"Sales Rank: #{sales_rank:,}\n"
        
        product_info += f"\nHistorial de Precios:\n{price_data_summary}\n"
        
        prompt = (
            f"{product_info}\n"
            "Analiza el historial de precios y genera un resumen amigable y conversacional. "
            "Incluye: precio promedio, tendencias identificadas, cambios significativos, "
            "y una recomendación estratégica sobre cuándo comprar. "
            "Habla como un analista experto dando consejos a un amigo. "
            "Mantén el tono natural y profesional."
        )
        
        return prompt
    
    def chat_with_product(
        self, 
        user_message: str,
        conversation_history: list,
        product_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Chat conversacional con contexto completo de Keepa
        
        Args:
            user_message: Pregunta del usuario
            conversation_history: Lista de mensajes previos [{"role": "user/assistant", "content": "..."}]
            product_data: Datos COMPLETOS del producto (con todos los histories)
            
        Returns:
            Respuesta de la IA
        """
        try:
            # Construir system prompt con contexto completo
            system_prompt = self._build_chat_system_prompt(product_data)
            
            # Construir lista de mensajes completa
            messages = [
                {"role": "system", "content": system_prompt}
            ]
            
            # Agregar historial de conversación (limitado a últimos 10 mensajes)
            if conversation_history:
                messages.extend(conversation_history[-10:])
            
            # Agregar mensaje actual del usuario
            messages.append({"role": "user", "content": user_message})
            
            logger.info(f"Generando respuesta de chat con {len(messages)} mensajes")
            
            # Llamar a OpenAI API con temperatura más alta para conversación
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                temperature=0.8,  # Más creativo para chat
                max_tokens=500,  # Aumentado para respuestas con análisis temporal
                top_p=0.9,
            )
            
            answer = response.choices[0].message.content.strip()
            logger.info("Respuesta de chat generada exitosamente")
            
            return answer
            
        except Exception as e:
            logger.error(f"Error en chat con OpenAI: {e}")
            return "Lo siento, tuve un problema generando la respuesta. Por favor intenta de nuevo."
    
    def _build_chat_system_prompt(self, product_data: Optional[Dict[str, Any]] = None) -> str:
        """
        Construye el system prompt para el chat con TODOS los datos de Keepa
        
        Args:
            product_data: Datos completos del producto o None si no hay producto
            
        Returns:
            String con el system prompt completo
        """
        base_prompt = (
            "Eres Keepa AI, un asistente experto en análisis de precios de Amazon. "
            "Tu trabajo es ayudar a los usuarios a tomar decisiones inteligentes de compra "
            "basándote en datos históricos de Keepa.\n\n"
        )
        
        if not product_data:
            # Modo general sin producto específico
            return base_prompt + (
                "Actualmente no hay un producto específico seleccionado. "
                "Puedes responder preguntas generales sobre Amazon, precios, o ayudar "
                "al usuario a navegar. Sé amigable y ofrece tu ayuda."
            )
        
        # Construir contexto completo del producto
        product_context = "DATOS COMPLETOS DEL PRODUCTO:\n"
        product_context += "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        # Información básica
        product_context += "📦 PRODUCTO\n"
        product_context += f"- Título: {product_data.get('title', 'N/A')}\n"
        product_context += f"- ASIN: {product_data.get('asin', 'N/A')}\n"
        if product_data.get('brand'):
            product_context += f"- Marca: {product_data.get('brand')}\n"
        if product_data.get('categories'):
            cats = ', '.join(product_data.get('categories', [])[:3])
            product_context += f"- Categorías: {cats}\n"
        
        # Precios
        product_context += "\n💵 PRECIOS\n"
        if product_data.get('current_price_new'):
            product_context += f"- Precio actual (Nuevo): ${product_data.get('current_price_new') / 100:.2f}\n"
        if product_data.get('current_price_amazon'):
            product_context += f"- Precio actual (Amazon): ${product_data.get('current_price_amazon') / 100:.2f}\n"
        if product_data.get('current_price_used'):
            product_context += f"- Precio actual (Usado): ${product_data.get('current_price_used') / 100:.2f}\n"
        
        # Analizar historial de precios si existe
        price_history = product_data.get('price_history', {})
        if price_history and price_history.get('NEW', {}).get('prices'):
            prices = [p / 100 for p in price_history['NEW']['prices']]
            if prices:
                product_context += f"- Precio promedio histórico: ${sum(prices) / len(prices):.2f}\n"
                product_context += f"- Rango histórico: ${min(prices):.2f} - ${max(prices):.2f}\n"
        
        # Sales Rank (ventas y popularidad)
        product_context += "\n📈 VENTAS & POPULARIDAD\n"
        if product_data.get('sales_rank_current'):
            product_context += f"- Sales Rank actual: #{product_data.get('sales_rank_current'):,}\n"
        
        sales_rank_history = product_data.get('sales_rank_history', {})
        if sales_rank_history and sales_rank_history.get('values'):
            values = sales_rank_history['values']
            if len(values) >= 2:
                # Comparar primero vs último para tendencia
                early = sum(values[:len(values)//3]) / (len(values)//3) if len(values) >= 3 else values[0]
                recent = sum(values[-len(values)//3:]) / (len(values)//3) if len(values) >= 3 else values[-1]
                if early > recent * 1.1:
                    trend = "mejorando significativamente (rank bajando = más ventas)"
                elif early < recent * 0.9:
                    trend = "empeorando (rank subiendo = menos ventas)"
                else:
                    trend = "estable"
                product_context += f"- Tendencia de ventas: {trend}\n"
        
        # Rating y reseñas
        product_context += "\n⭐ REPUTACIÓN & CALIDAD\n"
        if product_data.get('rating'):
            product_context += f"- Rating actual: {product_data.get('rating'):.1f} estrellas\n"
        if product_data.get('review_count'):
            product_context += f"- Total de reseñas: {product_data.get('review_count'):,}\n"
        
        rating_history = product_data.get('rating_history', {})
        if rating_history and rating_history.get('values'):
            values = rating_history['values']
            if len(values) >= 2:
                early = sum(values[:len(values)//3]) / (len(values)//3) if len(values) >= 3 else values[0]
                recent = sum(values[-len(values)//3:]) / (len(values)//3) if len(values) >= 3 else values[-1]
                if recent > early + 0.2:
                    trend = "mejorando (calidad en alza)"
                elif recent < early - 0.2:
                    trend = "empeorando (calidad en baja)"
                else:
                    trend = "estable"
                product_context += f"- Tendencia de calidad: {trend}\n"
        
        reviews_data = product_data.get('reviews_data', {})
        if reviews_data and reviews_data.get('rating_distribution'):
            dist = reviews_data['rating_distribution']
            total = sum(dist.values())
            if total > 0:
                positive = (dist.get(5, 0) + dist.get(4, 0)) / total * 100
                product_context += f"- Reviews positivas (4-5★): {positive:.0f}%\n"
        
        # 📊 DATOS HISTÓRICOS DETALLADOS (con fechas)
        product_context += "\n\n📊 HISTORIAL DETALLADO (Últimos datos disponibles):\n"
        product_context += "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        
        # Historial de PRECIOS con fechas
        if price_history:
            for price_type in ['NEW', 'AMAZON', 'USED']:
                if price_type in price_history:
                    data = price_history[price_type]
                    prices = data.get('prices', [])
                    times = data.get('formatted_times', [])
                    
                    if prices and times and len(prices) == len(times):
                        # Tomar últimos 15 puntos (aprox 3-6 meses dependiendo frecuencia)
                        recent_count = min(15, len(prices))
                        recent_prices = prices[-recent_count:]
                        recent_times = times[-recent_count:]
                        
                        type_label = {'NEW': 'Nuevo', 'AMAZON': 'Amazon', 'USED': 'Usado'}.get(price_type, price_type)
                        product_context += f"\n🏷️ Precios ({type_label}) - Últimos {recent_count} registros:\n"
                        
                        for i in range(len(recent_prices)):
                            if recent_prices[i] > 0:
                                price_usd = recent_prices[i] / 100
                                product_context += f"  • {recent_times[i]}: ${price_usd:.2f}\n"
        
        # Historial de SALES RANK con fechas
        if sales_rank_history and sales_rank_history.get('values') and sales_rank_history.get('formatted_times'):
            values = sales_rank_history['values']
            times = sales_rank_history['formatted_times']
            
            if len(values) == len(times) and len(values) > 0:
                recent_count = min(15, len(values))
                recent_values = values[-recent_count:]
                recent_times = times[-recent_count:]
                
                product_context += f"\n📊 Sales Rank - Últimos {recent_count} registros:\n"
                for i in range(len(recent_values)):
                    if recent_values[i] > 0:
                        product_context += f"  • {recent_times[i]}: #{recent_values[i]:,}\n"
        
        # Historial de RATING con fechas
        if rating_history and rating_history.get('values') and rating_history.get('formatted_times'):
            values = rating_history['values']
            times = rating_history['formatted_times']
            
            if len(values) == len(times) and len(values) > 0:
                recent_count = min(10, len(values))
                recent_values = values[-recent_count:]
                recent_times = times[-recent_count:]
                
                product_context += f"\n⭐ Rating - Últimos {recent_count} registros:\n"
                for i in range(len(recent_values)):
                    if recent_values[i] > 0:
                        product_context += f"  • {recent_times[i]}: {recent_values[i]:.1f} estrellas\n"
        
        # Instrucciones para la IA
        instructions = (
            "\n\n📋 INSTRUCCIONES:\n"
            "- Tienes acceso a DATOS HISTÓRICOS COMPLETOS con FECHAS ESPECÍFICAS\n"
            "- Cuando te pidan análisis temporal (ej: últimos 3 meses), usa las fechas del historial\n"
            "- Identifica tendencias, picos, caídas y patrones temporales\n"
            "- Cita fechas y valores específicos cuando sea relevante\n"
            "- Sé conversacional y amigable, como un asesor personal\n"
            "- Da recomendaciones honestas basadas en los datos temporales\n"
            "- Responde en 3-5 oraciones (conciso pero completo)\n"
            "- Puedes usar emojis sutilmente (1-2 máximo)\n"
        )
        
        return base_prompt + product_context + instructions
    
    def detect_document_intent(self, user_message: str) -> Optional[Dict[str, str]]:
        """
        Detecta si el usuario quiere generar un documento usando IA (PASO 1)
        
        Args:
            user_message: Mensaje del usuario
            
        Returns:
            Dict con 'intent' ('document' o None) y 'format' ('pdf', 'csv', etc. o None)
            O None si no hay intención de documento
        """
        try:
            prompt = f"""
Analiza el siguiente mensaje del usuario y determina si quiere generar un documento/archivo/reporte/exportar datos.

Mensaje del usuario: "{user_message}"

PATRONES DE DETECCIÓN AMPLIADOS:
- Generación: "genera", "crear", "hazme", "dame", "exporta", "descarga"
- Formatos: "pdf", "excel", "csv", "txt", "json", "markdown", "documento", "reporte", "informe", "archivo"
- Análisis: "análisis completo", "reporte detallado", "informe de", "documento con todos los datos"
- Exportación: "exportar", "descargar", "guardar como", "obtener archivo"

Responde SOLO con un JSON válido en este formato:
{{
    "intent": "document" o null,
    "format": "pdf" o "xlsx" o "csv" o "txt" o "json" o "md" o null,
    "specific_request": "descripción breve de lo que pidió específicamente"
}}

Ejemplos EXPANDIDOS:
- "genera un pdf" → {{"intent": "document", "format": "pdf", "specific_request": "generar pdf"}}
- "quiero un excel con los precios" → {{"intent": "document", "format": "xlsx", "specific_request": "excel con precios"}}
- "descarga el análisis" → {{"intent": "document", "format": null, "specific_request": "descargar análisis"}}
- "hazme un reporte completo" → {{"intent": "document", "format": null, "specific_request": "reporte completo"}}
- "exporta todos los datos" → {{"intent": "document", "format": null, "specific_request": "exportar todos los datos"}}
- "dame un informe con todo el historial" → {{"intent": "document", "format": null, "specific_request": "informe con historial completo"}}
- "crear documento con análisis" → {{"intent": "document", "format": null, "specific_request": "documento con análisis"}}
- "¿cuál es el precio?" → {{"intent": null, "format": null, "specific_request": "pregunta sobre precio"}}
- "¿cómo está el producto?" → {{"intent": null, "format": null, "specific_request": "pregunta general"}}

IMPORTANTE: Responde SOLO con el JSON, sin texto adicional.
"""
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",  # Modelo pequeño y rápido para detección
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Eres un clasificador de intenciones experto. Analiza mensajes y determina si el usuario "
                            "quiere generar, exportar, descargar o crear un documento/archivo/reporte. "
                            "Detecta patrones como: genera, crea, exporta, descarga, dame, hazme, reporte, informe, análisis, documento. "
                            "Responde siempre con JSON válido."
                        )
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.2,  # Muy baja temperatura para detección consistente
                max_tokens=150,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content.strip())
            
            # Manejar casos donde OpenAI retorna "null" como string o el valor null real
            intent_value = result.get('intent')
            if intent_value == 'null' or intent_value is None or (isinstance(intent_value, str) and intent_value.lower() == 'null'):
                logger.info(f"[PASO 1] No se detectó intención de documento: {result}")
                return None
            
            # Si detecta intención de documento, retornar el resultado
            if intent_value == 'document':
                # Limpiar format si es null
                if result.get('format') in [None, 'null', '']:
                    result['format'] = None
                logger.info(f"[PASO 1] ✓ Intención de documento detectada: {result}")
                return result
            
            logger.info(f"[PASO 1] No se detectó intención de documento: {result}")
            return None
            
        except Exception as e:
            logger.error(f"[PASO 1] Error detectando intención de documento: {e}")
            # En caso de error, fallback a detección manual básica
            return None
    
    def confirm_document_generation(self, user_message: str, product_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Segundo filtro: Valida la intención con contexto del producto y confirma qué datos incluir (PASO 2)
        
        Args:
            user_message: Mensaje del usuario
            product_data: Datos completos del producto para contexto
            
        Returns:
            Dict con confirmación y campos a incluir, o None si no se confirma
            {
                "confirmed": True,
                "include_fields": {
                    "basic_info": True,
                    "price_history": True/False,
                    "rating_history": True/False,
                    "sales_rank_history": True/False,
                    "reviews_data": True/False
                },
                "user_focus": "descripción de lo que el usuario quiere ver"
            }
        """
        try:
            # Preparar resumen del producto disponible
            product_summary = f"""
PRODUCTO DISPONIBLE:
- Título: {product_data.get('title', 'N/A')[:100]}
- ASIN: {product_data.get('asin', 'N/A')}
- Marca: {product_data.get('brand', 'N/A')}
- Precio actual: ${product_data.get('current_price_new', 0) / 100:.2f}
- Rating: {product_data.get('rating', 0):.1f}⭐ ({product_data.get('review_count', 0):,} reseñas)

DATOS HISTÓRICOS DISPONIBLES:
- Historial de precios: {'✓ Disponible' if product_data.get('price_history') else '✗ No disponible'}
- Historial de calificaciones: {'✓ Disponible' if product_data.get('rating_history') else '✗ No disponible'}
- Historial de sales rank: {'✓ Disponible' if product_data.get('sales_rank_history') else '✗ No disponible'}
- Datos de reseñas: {'✓ Disponible' if product_data.get('reviews_data') else '✗ No disponible'}
"""
            
            prompt = f"""
Contexto: Un usuario está viendo un producto en Keepa IA y ha hecho una solicitud.

{product_summary}

Solicitud del usuario: "{user_message}"

Analiza si el usuario REALMENTE quiere generar un documento con los datos de este producto.
Si confirmas que SÍ, determina qué información debe incluirse.

REGLA IMPORTANTE: Si el usuario pide "todo", "completo", "análisis completo", o "todos los datos",
incluye TODOS los historiales disponibles sin excepción.

Responde SOLO con un JSON válido en este formato:
{{
    "confirmed": true o false,
    "include_fields": {{
        "basic_info": true,
        "price_history": true o false,
        "rating_history": true o false,
        "sales_rank_history": true o false,
        "reviews_data": true o false
    }},
    "user_focus": "breve descripción del enfoque del usuario"
}}

Ejemplos:
- "genera pdf completo" → {{"confirmed": true, "include_fields": {{"basic_info": true, "price_history": true, "rating_history": true, "sales_rank_history": true, "reviews_data": true}}, "user_focus": "documento completo con todos los datos"}}
- "solo los precios en excel" → {{"confirmed": true, "include_fields": {{"basic_info": true, "price_history": true, "rating_history": false, "sales_rank_history": false, "reviews_data": false}}, "user_focus": "historial de precios"}}
- "¿cuánto cuesta?" → {{"confirmed": false, "include_fields": {{}}, "user_focus": "solo pregunta sobre precio"}}

IMPORTANTE: Responde SOLO con el JSON, sin texto adicional.
"""
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",  # Modelo mini para validación rápida
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Eres un validador experto. Tu trabajo es confirmar si el usuario quiere generar un documento "
                            "y determinar exactamente qué información debe incluirse. "
                            "Si el usuario pide 'todo', 'completo' o 'análisis completo', SIEMPRE incluye todos los historiales. "
                            "Responde siempre con JSON válido."
                        )
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.2,  # Baja temperatura para consistencia
                max_tokens=250,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content.strip())
            
            # Verificar confirmación
            if not result.get('confirmed', False):
                logger.info(f"[PASO 2] Generación de documento NO confirmada: {result.get('user_focus', 'N/A')}")
                return None
            
            logger.info(f"[PASO 2] ✓ Generación confirmada. Campos a incluir: {result.get('include_fields', {})}")
            logger.info(f"[PASO 2] Enfoque del usuario: {result.get('user_focus', 'N/A')}")
            
            return result
            
        except Exception as e:
            logger.error(f"[PASO 2] Error confirmando generación de documento: {e}")
            # En caso de error, asumir que se confirma con todos los datos
            return {
                "confirmed": True,
                "include_fields": {
                    "basic_info": True,
                    "price_history": True,
                    "rating_history": True,
                    "sales_rank_history": True,
                    "reviews_data": True
                },
                "user_focus": "documento completo (fallback por error)"
            }
    
    def generate_document_content(self, product_data: Dict[str, Any], document_type: str = "general", user_request: str = None) -> str:
        """
        Genera contenido flexible en Markdown según la solicitud del usuario
        
        Args:
            product_data: Datos completos del producto
            document_type: Tipo de documento (legacy, ahora se usa user_request principalmente)
            user_request: Solicitud específica del usuario que determina qué incluir
            
        Returns:
            String con contenido en Markdown
        """
        try:
            # Construir prompt flexible basado en la solicitud del usuario
            prompt = self._build_flexible_document_prompt(product_data, user_request)
            
            logger.info(f"[PASO 3] Generando contenido flexible para documento. Solicitud: {user_request}")
            logger.info(f"[PASO 3] Tamaño del prompt: {len(prompt)} caracteres")
            
            # Llamar a OpenAI con respuesta en Markdown (PASO 3)
            # Detectar si necesita más tokens (historiales completos)
            asks_for_full_history = user_request and any(word in user_request.lower() for word in ['historial', 'histórico', 'historia', 'completo', 'todos', 'todas', 'todo', 'completa'])
            # Aumentar significativamente max_tokens para historiales completos
            max_tokens = 8000 if asks_for_full_history else 4000
            
            logger.info(f"[PASO 3] Generando contenido Markdown con max_tokens={max_tokens} (historial completo: {asks_for_full_history})")
            logger.info(f"[PASO 3] Llamando a OpenAI API con modelo gpt-4o...")
            
            response = self.client.chat.completions.create(
                model="gpt-4o",  # Modelo con mayor capacidad para generar contenido extenso
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Eres un generador de contenido Markdown experto que trabaja con datos de Amazon/Keepa. "
                            "COMPRENDES que NO puedes generar archivos PDF/Excel/CSV directamente (eres una IA de lenguaje), "
                            "por lo que tu trabajo es generar contenido estructurado en Markdown que será convertido técnicamente.\n\n"
                            "REGLAS CRÍTICAS:\n"
                            "1. Genera EXACTAMENTE lo que el usuario pidió, nada más, nada menos\n"
                            "2. Si pide una tabla, COPIA TODA la tabla del contexto con TODAS las filas\n"
                            "3. Si pide 'historial completo' o 'todos los datos', incluye TODOS los registros disponibles\n"
                            "4. NO resumas, NO limites filas, NO omitas datos\n"
                            "5. NO inventes datos - usa SOLO los del contexto proporcionado\n"
                            "6. NO incluyas delimitadores de código (```markdown o ```)\n"
                            "7. Usa formato Markdown puro: tablas (| |), títulos (# ##), listas (-, *)\n"
                            "8. Termina siempre con: '---\\n*Generado por Keepa AI*'\n\n"
                            "IMPORTANTE: Si el contexto tiene una tabla con 500 filas, DEBES copiar las 500 filas completas."
                        )
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.2,  # Muy determinista para copiar datos exactos
                max_tokens=max_tokens,
            )
            
            markdown_content = response.choices[0].message.content.strip()
            logger.info(f"[PASO 3] Respuesta recibida de OpenAI: {len(markdown_content)} caracteres")
            
            # Limpiar bloques de código Markdown que OpenAI a veces agrega
            markdown_content = self._clean_markdown_content(markdown_content)
            logger.info(f"[PASO 3] Contenido limpiado: {len(markdown_content)} caracteres")
            
            logger.info("[PASO 3] ✓ Contenido Markdown generado exitosamente")
            return markdown_content
            
        except Exception as e:
            logger.error(f"[PASO 3] Error generando contenido de documento: {e}")
            logger.error(f"[PASO 3] Tipo de error: {type(e).__name__}")
            logger.error(f"[PASO 3] User request: {user_request}")
            import traceback
            logger.error(f"[PASO 3] Traceback completo:\n{traceback.format_exc()}")
            # Retornar contenido básico en Markdown
            return self._get_fallback_markdown(product_data, user_request)
    
    def _clean_markdown_content(self, content: str) -> str:
        """
        Limpia el contenido Markdown removiendo bloques de código y delimitadores
        
        Args:
            content: Contenido Markdown crudo
            
        Returns:
            Contenido Markdown limpio
        """
        # Remover bloques de código markdown (```markdown ... ```)
        content = re.sub(r'```markdown\s*\n', '', content, flags=re.IGNORECASE)
        content = re.sub(r'```md\s*\n', '', content, flags=re.IGNORECASE)
        content = re.sub(r'```\s*$', '', content, flags=re.MULTILINE)
        content = re.sub(r'^```\s*\n', '', content, flags=re.MULTILINE)
        
        # Remover bloques de código genéricos si quedan
        lines = content.split('\n')
        cleaned_lines = []
        skip_next = False
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            # Detectar inicio de bloque de código
            if stripped.startswith('```') and ('markdown' in stripped.lower() or 'md' in stripped.lower() or len(stripped) == 3):
                skip_next = True
                continue
            
            # Detectar fin de bloque de código
            if skip_next and stripped == '```':
                skip_next = False
                continue
            
            if not skip_next:
                cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines).strip()
    
    def _build_flexible_document_prompt(self, product_data: Dict[str, Any], user_request: str = None) -> str:
        """
        Construye un prompt flexible que adapta el contenido según la solicitud del usuario
        
        Args:
            product_data: Datos completos del producto
            user_request: Solicitud específica del usuario
            
        Returns:
            String con el prompt flexible
        """
        # Obtener datos básicos
        title = product_data.get('title', 'Producto')
        asin = product_data.get('asin', 'N/A')
        brand = product_data.get('brand', 'N/A')
        current_price_new = product_data.get('current_price_new', 0) / 100 if product_data.get('current_price_new') else None
        current_price_amazon = product_data.get('current_price_amazon', 0) / 100 if product_data.get('current_price_amazon') else None
        current_price_used = product_data.get('current_price_used', 0) / 100 if product_data.get('current_price_used') else None
        rating = product_data.get('rating', 0)
        review_count = product_data.get('review_count', 0)
        sales_rank_current = product_data.get('sales_rank_current')
        
        # Obtener TODOS los campos adicionales
        binding = product_data.get('binding', 'N/A')
        color = product_data.get('color', 'N/A')
        availability_amazon = product_data.get('availability_amazon', 0)
        categories = product_data.get('categories', [])
        category_tree = product_data.get('category_tree', [])
        image_url = product_data.get('image_url', 'N/A')
        last_updated = product_data.get('last_updated', 'N/A')
        created_at = product_data.get('created_at', 'N/A')
        queried_by = product_data.get('queried_by', 'N/A')
        
        # Construir contexto completo de datos disponibles - ABSOLUTAMENTE TODOS
        context = f"""
# DATOS COMPLETOS DEL PRODUCTO:

## Información Básica
- **Título**: {title}
- **ASIN**: {asin}
- **Marca**: {brand}
- **Categoría/Binding**: {binding}
- **Color**: {color}
- **Disponibilidad en Amazon**: {"✓ Disponible" if availability_amazon == 1 else "✗ No disponible"}
- **Imagen**: {image_url}

        ## Categorías
{f"- Categorías: {', '.join(str(c) for c in categories[:5])}" if categories else "- Sin categorías"}
{f"- Árbol de categorías: {' > '.join(str(c) if isinstance(c, str) else str(c.get('name', c)) if isinstance(c, dict) else str(c) for c in category_tree[:3])}" if category_tree else ""}

## Precios Actuales
"""
        
        if current_price_new:
            context += f"- **Nuevo**: ${current_price_new:.2f}\n"
        if current_price_amazon:
            context += f"- **Amazon**: ${current_price_amazon:.2f}\n"
        if current_price_used:
            context += f"- **Usado**: ${current_price_used:.2f}\n"
        
        context += f"""
## Reputación
- **Rating**: {rating:.1f} estrellas
- **Total de Reseñas**: {review_count:,}
"""
        
        if sales_rank_current:
            context += f"- **Sales Rank Actual**: #{sales_rank_current:,}\n"
        
        context += f"""
## Metadata
- **Última actualización**: {last_updated}
- **Fecha de consulta**: {created_at}
- **Consultado por**: {queried_by}
"""
        
        # Historial de precios con fechas
        price_history = product_data.get('price_history', {})
        logger.info(f"Price history disponible: {bool(price_history)}, Tipos: {list(price_history.keys()) if price_history else 'N/A'}")
        if price_history:
            context += "\n## Historial de Precios\n"
            
            for price_type in ['NEW', 'AMAZON', 'USED']:
                if price_type in price_history:
                    data = price_history[price_type]
                    prices = data.get('prices', [])
                    times = data.get('formatted_times', [])
                    
                    if prices and len(prices) > 0:
                        type_label = {'NEW': 'Nuevo', 'AMAZON': 'Amazon', 'USED': 'Usado'}.get(price_type, price_type)
                        prices_usd = [p / 100 for p in prices if p > 0]
                        
                        if prices_usd:
                            min_price = min(prices_usd)
                            max_price = max(prices_usd)
                            avg_price = sum(prices_usd) / len(prices_usd)
                            
                            context += f"\n### Precios {type_label}\n"
                            context += f"- Rango: ${min_price:.2f} - ${max_price:.2f}\n"
                            context += f"- Promedio: ${avg_price:.2f}\n"
                            
                            # Si tiene fechas, incluir todas (útil para historiales)
                            if times and len(times) == len(prices):
                                # Si pide historial, incluir TODOS los precios en formato tabla
                                asks_for_history = user_request and any(word in user_request.lower() for word in ['historial', 'histórico', 'historia', 'completo', 'todos', 'precios'])
                                display_count = len(prices) if asks_for_history else min(50, len(prices))
                                start_idx = len(prices) - display_count
                                
                                if asks_for_history:
                                    # Formato tabla para historial completo
                                    valid_prices = [i for i in range(start_idx, len(prices)) if prices[i] > 0]
                                    context += f"\n**Historial completo de precios {type_label} ({len(valid_prices)} registros):**\n\n"
                                    context += "| Fecha | Precio |\n"
                                    context += "|-------|--------|\n"
                                    logger.info(f"Incluyendo {len(valid_prices)} precios {type_label} en formato tabla para historial completo")
                                    for i in range(start_idx, len(prices)):
                                        if prices[i] > 0:
                                            context += f"| {times[i]} | ${prices[i] / 100:.2f} |\n"
                                else:
                                    # Formato lista para vista resumida
                                    context += f"\n**Últimos precios ({display_count} registros):**\n\n"
                                    for i in range(start_idx, len(prices)):
                                        if prices[i] > 0:
                                            context += f"- {times[i]}: ${prices[i] / 100:.2f}\n"
        
        # Sales Rank History
        sales_rank_history = product_data.get('sales_rank_history', {})
        if sales_rank_history and sales_rank_history.get('values'):
            values = sales_rank_history['values']
            times = sales_rank_history.get('formatted_times', [])
            
            if values and len(values) > 0:
                context += "\n## Historial de Sales Rank (Ventas)\n"
                context += f"- Total de registros: {len(values)}\n"
                if times and len(times) == len(values):
                    # Si pide historial completo, incluir TODOS los datos en formato tabla
                    asks_for_history = user_request and any(word in user_request.lower() for word in ['historial', 'histórico', 'historia', 'completo', 'todos', 'ventas', 'sales'])
                    display_count = len(values) if asks_for_history else min(20, len(values))
                    start_idx = len(values) - display_count
                    
                    if asks_for_history:
                        # Formato tabla para historial completo
                        context += f"\n**Historial completo de ventas ({len(values)} registros):**\n\n"
                        context += "| Fecha | Sales Rank |\n"
                        context += "|-------|------------|\n"
                        for i in range(start_idx, len(values)):
                            if values[i] > 0:
                                context += f"| {times[i]} | #{values[i]:,} |\n"
                    else:
                        # Formato lista para vista resumida
                        context += f"\n**Últimos registros ({display_count}):**\n\n"
                        for i in range(start_idx, len(values)):
                            if values[i] > 0:
                                context += f"- {times[i]}: #{values[i]:,}\n"
        
        # Rating History
        rating_history = product_data.get('rating_history', {})
        if rating_history and rating_history.get('values'):
            values = rating_history['values']
            times = rating_history.get('formatted_times', [])
            
            if values and len(values) > 0:
                context += "\n## Historial de Ratings\n"
                if times and len(times) == len(values):
                    context += "\n**Últimos registros:**\n\n"
                    display_count = min(15, len(values))
                    start_idx = len(values) - display_count
                    for i in range(start_idx, len(values)):
                        if values[i] > 0:
                            context += f"- {times[i]}: {values[i]:.1f} estrellas\n"
        
        # Construir instrucción según solicitud del usuario
        if user_request:
            # Detectar si pide historial completo
            asks_for_history = any(word in user_request.lower() for word in ['historial', 'histórico', 'historia', 'completo', 'todos', 'todas'])
            
            # Contar registros disponibles
            price_count = len(price_history.get('NEW', {}).get('prices', [])) if price_history else 0
            sales_count = len(sales_rank_history.get('values', [])) if sales_rank_history else 0
            
            instruction = f"""
# SOLICITUD DEL USUARIO:

"{user_request}"

# TU TAREA:

Genera EXACTAMENTE lo que pidió el usuario. COPIA DIRECTAMENTE las tablas del contexto arriba.

**REGLAS CRÍTICAS:**
1. Si pidió "historial de precios" → Busca arriba la sección "## Historial de Precios" y COPIA TODA la tabla que está ahí
2. Si pidió "historial de ventas" → Busca arriba la sección "## Historial de Sales Rank" y COPIA TODA la tabla que está ahí
3. Si pidió "dos tablas" → Busca y copia ambas tablas completas del contexto
4. Si pidió "últimos 3 meses" → Filtra solo esos 3 meses de las tablas del contexto
5. NO inventes datos, NO crees nuevas tablas, NO resumas
6. **COPIA LITERALMENTE** las tablas del contexto arriba

**{"⚠️ CRÍTICO: El usuario pidió HISTORIAL COMPLETO. Arriba en el contexto hay tablas con TODOS los datos. DEBES COPIAR esas tablas completas. NO las reescribas, NO las limites, NO las resumas. Si ves una tabla arriba con {price_count} precios, copia TODAS las {price_count} filas. Si ves una tabla con {sales_count} ventas, copia TODAS las {sales_count} filas." if asks_for_history else ""}**

**PASOS:**
1. Busca en el contexto arriba la sección relevante (Historial de Precios o Historial de Ventas)
2. Localiza la tabla con formato: | Fecha | Precio | o | Fecha | Sales Rank |
3. COPIA toda esa tabla línea por línea
4. Pega el título (# ...)
5. Pega la tabla completa
6. Repite si pidió dos tablas
7. Agrega: ---\\n*Generado por Keepa AI*

**EJEMPLO DE LO QUE DEBES HACER:**

Si arriba en el contexto ves:
```
## Historial de Precios
| Fecha | Precio |
|-------|--------|
| 2024-11-01 | $99.99 |
| 2024-10-31 | $98.50 |
... (500 filas más)
```

Y el usuario pide "historial de precios", tu respuesta debe ser:

# Historial de Precios

| Fecha | Precio |
|-------|--------|
| 2024-11-01 | $99.99 |
| 2024-10-31 | $98.50 |
... (las 500 filas completas del contexto)

---
*Generado por Keepa AI*
"""
        else:
            instruction = """
# TU TAREA:

El usuario pidió un documento general. Genera un resumen conciso con:
- Precios actuales
- Rating y reseñas
- Tendencia de ventas

Usa tablas y sé breve.
"""
        
        # Agregar explicación de limitación de IA al inicio
        ai_limitation_notice = """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# PASO 3: GENERACIÓN DE CONTENIDO EN MARKDOWN

## ⚠️ IMPORTANTE - ENTENDIENDO TUS LIMITACIONES COMO IA:

**LIMITACIÓN TÉCNICA**: Como modelo de lenguaje IA, NO puedes generar archivos PDF, Excel, CSV u otros formatos binarios directamente.

**TU ROL**: Generar contenido estructurado en formato Markdown que será convertido automáticamente al formato solicitado por un sistema técnico especializado.

**TU TRABAJO**: Proporcionar contenido en Markdown limpio y bien estructurado usando TODOS los datos disponibles.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        
        prompt = f"""
{ai_limitation_notice}

{context}

{instruction}

**RECORDATORIO FINAL:** 
- Espero el contenido en formato Markdown puro (será convertido automáticamente al formato final)
- NO incluyas delimitadores de código (```markdown o ```)
- NO inventes datos - usa SOLO los datos del contexto arriba
- Si pidieron historial completo, DEBES copiar TODAS las filas de las tablas del contexto
- Formato: # Título → Tabla/Lista → ---\\n*Generado por Keepa AI*
"""
        
        return prompt
    
    def _build_document_prompt(self, product_data: Dict[str, Any], document_type: str, user_request: str = None) -> str:
        """
        Construye el prompt para generar contenido de documento
        
        Args:
            product_data: Datos del producto
            document_type: Tipo de documento
            user_request: Solicitud específica del usuario
            
        Returns:
            String con el prompt
        """
        # Obtener datos básicos
        title = product_data.get('title', 'Producto')
        asin = product_data.get('asin', 'N/A')
        current_price = product_data.get('current_price_new', 0) / 100
        rating = product_data.get('rating', 0)
        review_count = product_data.get('review_count', 0)
        
        # Analizar historial de precios
        price_history = product_data.get('price_history', {})
        price_summary = ""
        price_detail = ""
        
        # Detectar si el usuario pidió específicamente historial de precios
        user_wants_history = user_request and any(word in user_request.lower() for word in ['historial', 'histórico', 'historia', 'precios', 'precio', 'historical', 'history'])
        
        if price_history and price_history.get('NEW', {}).get('prices'):
            prices = [p / 100 for p in price_history['NEW']['prices']]
            times = price_history.get('NEW', {}).get('formatted_times', [])
            
            if prices:
                min_price = min(prices)
                max_price = max(prices)
                avg_price = sum(prices) / len(prices)
                price_summary = f"Rango: ${min_price:.2f} - ${max_price:.2f}, Promedio: ${avg_price:.2f}"
                
                # Si tiene fechas y el usuario quiere historial, incluir TODOS los datos disponibles
                if times and len(times) == len(prices):
                    if user_wants_history:
                        # Incluir TODOS los registros si pidió historial
                        price_detail = "\n\nHISTORIAL COMPLETO DE PRECIOS (con fechas):\n"
                        for i in range(len(prices)):
                            price_detail += f"- {times[i]}: ${prices[i]:.2f}\n"
                    else:
                        # Solo últimos 15 registros si no pidió historial específico
                        recent_count = min(15, len(prices))
                        price_detail = "\n\nHistorial reciente de precios:\n"
                        for i in range(len(prices) - recent_count, len(prices)):
                            price_detail += f"- {times[i]}: ${prices[i]:.2f}\n"
        
        # Personalizar el prompt según la solicitud del usuario
        if user_request:
            request_instruction = f"\n\n⚠️ SOLICITUD ESPECÍFICA DEL USUARIO: {user_request}\n"
            if user_wants_history:
                request_instruction += "⚠️ ATENCIÓN: El usuario pidió específicamente el HISTORIAL DE PRECIOS.\n"
                request_instruction += "⚠️ OBLIGATORIO: Debes incluir TODOS los datos históricos con fechas en el campo 'historical_data'.\n"
                request_instruction += "⚠️ El campo 'historical_data' debe contener una lista detallada de fechas y precios del historial proporcionado arriba.\n"
            request_instruction += "IMPORTANTE: Adapta el análisis para responder específicamente a esta solicitud. "
            request_instruction += "Usa las fechas y valores del historial proporcionado cuando sea relevante."
        else:
            request_instruction = "\n\nGenera un análisis general y completo del producto."
        
        prompt = f"""
Genera un análisis completo y estructurado en formato JSON para el siguiente producto:
{request_instruction}

PRODUCTO: {title}
ASIN: {asin}
Precio Actual: ${current_price:.2f}
Rating: {rating:.1f} estrellas ({review_count:,} reseñas)
{f"Historial de Precios: {price_summary}" if price_summary else ""}
{price_detail if price_detail else ""}

Genera un JSON con la siguiente estructura EXACTA:
{{
    "executive_summary": "Resumen ejecutivo de 2-3 oraciones con los puntos clave del análisis (adapta según la solicitud del usuario)",
    "price_analysis": {{
        "average_price": "Precio promedio en formato $XX.XX",
        "min_price": "Precio mínimo en formato $XX.XX",
        "max_price": "Precio máximo en formato $XX.XX",
        "trend": "Tendencia de precios (ej: 'Precios estables', 'Tendencia al alza', 'Tendencia a la baja')",
        "value_assessment": "Evaluación si el precio actual es bueno, normal o alto",
        "historical_data": "{'OBLIGATORIO: Si el usuario pidió historial de precios, DEBES incluir aquí TODAS las fechas y precios del historial proporcionado arriba en formato: Fecha: Precio, Fecha: Precio, etc. Copia EXACTAMENTE las fechas y precios del HISTORIAL COMPLETO DE PRECIOS que se te proporcionó. Si NO pidió historial, deja este campo como null o vacío.' if user_wants_history else 'Si el usuario solicitó historial temporal, incluye aquí un texto detallado con las fechas y precios específicos. Si no solicitó historial, deja este campo como null o vacío.'}"
    }},
    "reputation_analysis": {{
        "quality_score": "Evaluación de calidad basada en rating (Excelente/Buena/Regular/Mala)",
        "positive_reviews": "Porcentaje o descripción de reviews positivas",
        "confidence_level": "Nivel de confianza en el producto (Alto/Medio/Bajo)"
    }},
    "recommendation": "Recomendación final clara y accionable de 2-3 oraciones sobre si comprar ahora, esperar, o evitar el producto (adapta según la solicitud)",
    "additional_notes": "Si el usuario pidió información específica adicional (ej: análisis de ventas, etc.), incluye aquí detalles adicionales. Si pidió historial de precios, este campo puede estar vacío."
}}

REGLAS CRÍTICAS:
- Si el usuario pidió "historial de precios" o similar, el campo "historical_data" DEBE contener TODAS las fechas y precios del historial proporcionado arriba
- Copia EXACTAMENTE las fechas y precios del "HISTORIAL COMPLETO DE PRECIOS" que está en el contexto
- Formato sugerido para historical_data: lista de líneas como "Fecha: $XX.XX\\nFecha: $XX.XX" o formato tabla
- Responde SOLO con el JSON válido, sin texto adicional
- Si el usuario pidió datos históricos, NO los omitas - son OBLIGATORIOS
"""
        
        return prompt
    
    def _get_fallback_markdown(self, product_data: Dict[str, Any], user_request: str = None) -> str:
        """
        Genera contenido básico en Markdown como fallback
        
        Args:
            product_data: Datos del producto
            user_request: Solicitud del usuario
            
        Returns:
            String con Markdown básico
        """
        logger.warning(f"[FALLBACK] Generando contenido básico de fallback para request: {user_request}")
        
        title = product_data.get('title', 'Producto')
        asin = product_data.get('asin', 'N/A')
        current_price_raw = product_data.get('current_price_new', 0)
        current_price = (current_price_raw / 100) if current_price_raw else 0.0
        rating = product_data.get('rating', 0) or 0
        review_count = product_data.get('review_count', 0) or 0
        
        markdown = f"""# Análisis de Producto - Keepa AI

## Información del Producto

- **Título**: {title}
- **ASIN**: {asin}
- **Precio Actual**: ${current_price:.2f}
- **Rating**: {rating:.1f} estrellas
- **Total de Reseñas**: {review_count:,}

## Nota

Este es un análisis básico automático. Para un análisis más detallado, por favor intenta de nuevo.
"""
        
        return markdown
    
    def _get_fallback_content(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Genera contenido básico de respaldo si OpenAI falla
        
        Args:
            product_data: Datos del producto
            
        Returns:
            Dict con contenido básico
        """
        current_price = product_data.get('current_price_new', 0) / 100
        rating = product_data.get('rating', 0)
        
        return {
            "executive_summary": f"Análisis automático del producto. Precio actual: ${current_price:.2f}, Rating: {rating:.1f} estrellas.",
            "price_analysis": {
                "average_price": f"${current_price:.2f}",
                "min_price": "Datos no disponibles",
                "max_price": "Datos no disponibles",
                "trend": "Datos insuficientes",
                "value_assessment": "Análisis no disponible"
            },
            "reputation_analysis": {
                "quality_score": "Buena" if rating >= 4.0 else "Regular",
                "positive_reviews": f"{rating:.1f}/5.0 estrellas",
                "confidence_level": "Medio"
            },
            "recommendation": "Consulta más información antes de realizar la compra."
        }

