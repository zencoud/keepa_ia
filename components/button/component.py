from django_components import component


@component.register("button")
class Button(component.Component):
    template_name = "button/button.html"

