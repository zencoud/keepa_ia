from django_components import component


@component.register("product_card")
class ProductCard(component.Component):
    template_name = "product_card/product_card.html"

