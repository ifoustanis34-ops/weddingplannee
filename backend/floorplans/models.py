"""« Croquis » (feedback 20/11/2026): the plan of a venue drawn to scale.

The planner enters the length and the width of the place in metres, then places chairs, tables,
stage, dance floor… on it. The elements are kept as a JSON list (positions in metres from the
top-left corner): a plan is always read and saved whole.
"""

from __future__ import annotations

from django.db import models

from core.models import TenantModel


class FloorPlan(TenantModel):
    name = models.CharField(max_length=160)
    venue = models.CharField(max_length=160, blank=True)
    # Metres: the length runs left to right, the width top to bottom.
    length = models.DecimalField(max_digits=6, decimal_places=2)
    width = models.DecimalField(max_digits=6, decimal_places=2)
    # [{id, type, x, y, w, h, rotation, label, seats}] — see serializers.ELEMENT_TYPES.
    elements = models.JSONField(default=list, blank=True)
    notes = models.TextField(blank=True)
    # {floor, walls, light, height}: how the room looks in 3D (serializers.AMBIANCE).
    ambiance = models.JSONField(default=dict, blank=True)

    class Meta(TenantModel.Meta):
        ordering = ["-updated_at"]

    def __str__(self) -> str:
        return self.name
