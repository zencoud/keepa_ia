from django_components import component


@component.register("pagination")
class Pagination(component.Component):
    template_name = "pagination/pagination.html"

