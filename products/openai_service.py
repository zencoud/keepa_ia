import openai
import logging
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

