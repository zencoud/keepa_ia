from django_components import component


@component.register("empty_state")
class EmptyState(component.Component):
    template_name = "empty_state/empty_state.html"

