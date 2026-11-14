from django.urls import path

from . import views

urlpatterns = [
    path("item-categories", views.CategoryListView.as_view(), name="item-categories"),
    path("item-categories/<uuid:pk>", views.CategoryDetailView.as_view(), name="item-category"),
    path("items", views.ItemListView.as_view(), name="item-list"),
    path("items/<uuid:pk>", views.ItemDetailView.as_view(), name="item-detail"),
    path("items/<uuid:pk>/photo", views.ItemPhotoView.as_view(), name="item-photo"),
    path("items/<uuid:pk>/activity", views.ItemActivityView.as_view(), name="item-activity"),
    path("items/<uuid:pk>/labels", views.ItemLabelsView.as_view(), name="item-labels"),
    path("items/<uuid:pk>/units", views.UnitListView.as_view(), name="item-units"),
    path("units/<uuid:pk>", views.UnitDetailView.as_view(), name="unit-detail"),
    path("packs", views.PackListView.as_view(), name="pack-list"),
    path("packs/<uuid:pk>", views.PackDetailView.as_view(), name="pack-detail"),
    path("availability", views.AvailabilityView.as_view(), name="availability"),
    path("availability/grid", views.AvailabilityGridView.as_view(), name="availability-grid"),
    path("stock-movements", views.MovementListView.as_view(), name="movement-list"),
    path(
        "stock-movements/<uuid:pk>/cancel",
        views.MovementCancelView.as_view(),
        name="movement-cancel",
    ),
    path("maintenance", views.MaintenanceListView.as_view(), name="maintenance-list"),
    path(
        "maintenance/<uuid:pk>/close",
        views.MaintenanceCloseView.as_view(),
        name="maintenance-close",
    ),
    path("inventories", views.InventoryListView.as_view(), name="inventory-list"),
    path("inventories/<uuid:pk>", views.InventoryDetailView.as_view(), name="inventory-detail"),
    path(
        "inventories/<uuid:pk>/validate",
        views.InventoryValidateView.as_view(),
        name="inventory-validate",
    ),
    path("stock/stats", views.StockStatsView.as_view(), name="stock-stats"),
    path("partner-supplies", views.PartnerSupplyListView.as_view(), name="partner-supplies"),
    path(
        "partner-supplies/<uuid:pk>",
        views.PartnerSupplyDetailView.as_view(),
        name="partner-supply",
    ),
    path("stock/import", views.StockImportView.as_view(), name="stock-import"),
    path("stock/import/template", views.StockImportTemplateView.as_view(), name="stock-template"),
]
