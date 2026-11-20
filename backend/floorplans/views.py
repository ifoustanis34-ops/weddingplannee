from __future__ import annotations

from django.db.models import Q, QuerySet
from rest_framework import generics

from events.permissions import PERMISSIONS

from .models import FloorPlan
from .serializers import FloorPlanSerializer


class FloorPlanListView(generics.ListCreateAPIView[FloorPlan]):
    """« Croquis »: every member reads (the storekeeper sets the room up); owner, planner and
    assistant draw. ``?search=`` filters on the name and the venue."""

    serializer_class = FloorPlanSerializer
    permission_classes = PERMISSIONS
    open_to_field_roles = True  # the storekeeper and team leads set the room up from it
    pagination_class = None

    def get_queryset(self) -> QuerySet[FloorPlan]:
        if getattr(self, "swagger_fake_view", False):
            return FloorPlan.all_tenants.none()
        plans = FloorPlan.objects.all()
        search = self.request.query_params.get("search", "").strip()
        if search:
            plans = plans.filter(Q(name__icontains=search) | Q(venue__icontains=search))
        return plans

    def perform_create(self, serializer: FloorPlanSerializer) -> None:  # type: ignore[override]
        serializer.save(created_by=self.request.user)


class FloorPlanDetailView(generics.RetrieveUpdateDestroyAPIView[FloorPlan]):
    serializer_class = FloorPlanSerializer
    permission_classes = PERMISSIONS
    open_to_field_roles = True  # the storekeeper and team leads set the room up from it
    http_method_names = ["get", "patch", "delete"]

    def get_queryset(self) -> QuerySet[FloorPlan]:
        if getattr(self, "swagger_fake_view", False):
            return FloorPlan.all_tenants.none()
        return FloorPlan.objects.all()
