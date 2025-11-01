from django_components import component


@component.register("stats_card")
class StatsCard(component.Component):
    template_name = "stats_card/stats_card.html"

