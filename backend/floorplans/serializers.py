from __future__ import annotations

from decimal import Decimal
from typing import Any

from rest_framework import serializers

from .models import FloorPlan

# What can be placed on a plan; ``seats`` counts the chairs of a table or of a row of chairs.
ELEMENT_TYPES = {
    "chair",
    "chair_row",
    "round_table",
    "rect_table",
    "stage",
    "dance_floor",
    "buffet",
    "bar",
    "dj",
    "entrance",
    "decor",
    "pillar",
    "text",
}
MAX_ELEMENTS = 2000
MAX_SIDE = Decimal("500")  # metres: a field, not only a hall


def _number(value: Any, field: str, *, low: float, high: float) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise serializers.ValidationError(f"« {field} » doit être un nombre.")
    if not low <= value <= high:
        raise serializers.ValidationError(f"« {field} » doit être entre {low} et {high}.")
    return round(float(value), 3)


def clean_element(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise serializers.ValidationError("Chaque élément doit être un objet.")
    kind = raw.get("type")
    if kind not in ELEMENT_TYPES:
        raise serializers.ValidationError(f"Type d’élément inconnu : {kind}.")
    side = float(MAX_SIDE)
    element: dict[str, Any] = {
        "id": str(raw.get("id") or "")[:40],
        "type": kind,
        "x": _number(raw.get("x", 0), "x", low=-side, high=2 * side),
        "y": _number(raw.get("y", 0), "y", low=-side, high=2 * side),
        "w": _number(raw.get("w", 0.5), "w", low=0.05, high=side),
        "h": _number(raw.get("h", 0.5), "h", low=0.05, high=side),
        "rotation": _number(raw.get("rotation", 0), "rotation", low=-360, high=360),
        "label": str(raw.get("label") or "")[:80],
    }
    seats = raw.get("seats", 0)
    element["seats"] = int(_number(seats or 0, "seats", low=0, high=500))
    return element


class FloorPlanSerializer(serializers.ModelSerializer[FloorPlan]):
    length = serializers.DecimalField(
        max_digits=6,
        decimal_places=2,
        min_value=Decimal("1"),
        max_value=MAX_SIDE,
        coerce_to_string=False,
    )
    width = serializers.DecimalField(
        max_digits=6,
        decimal_places=2,
        min_value=Decimal("1"),
        max_value=MAX_SIDE,
        coerce_to_string=False,
    )
    chairs = serializers.SerializerMethodField()

    class Meta:
        model = FloorPlan
        fields = [
            "id",
            "name",
            "venue",
            "length",
            "width",
            "elements",
            "notes",
            "chairs",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "chairs", "created_at", "updated_at"]

    def validate_elements(self, value: Any) -> list[dict[str, Any]]:
        if not isinstance(value, list):
            raise serializers.ValidationError("Liste d’éléments attendue.")
        if len(value) > MAX_ELEMENTS:
            raise serializers.ValidationError(f"{MAX_ELEMENTS} éléments au plus par croquis.")
        return [clean_element(raw) for raw in value]

    def get_chairs(self, plan: FloorPlan) -> int:
        """Places to sit: single chairs, plus the seats of tables and rows."""
        return sum(
            1 if element.get("type") == "chair" else int(element.get("seats") or 0)
            for element in plan.elements or []
        )
