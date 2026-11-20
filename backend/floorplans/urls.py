from django.urls import path

from . import views

urlpatterns = [
    path("floor-plans", views.FloorPlanListView.as_view(), name="floorplan-list"),
    path("floor-plans/<uuid:pk>", views.FloorPlanDetailView.as_view(), name="floorplan-detail"),
]
