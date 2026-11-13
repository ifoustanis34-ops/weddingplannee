from django.urls import path

from . import views

urlpatterns = [
    path("catalog/categories", views.CategoryListView.as_view(), name="catalog-categories"),
    path(
        "catalog/categories/<uuid:pk>",
        views.CategoryDetailView.as_view(),
        name="catalog-category-detail",
    ),
    path("catalog/items", views.ItemListView.as_view(), name="catalog-items"),
    path("catalog/items/<uuid:pk>", views.ItemDetailView.as_view(), name="catalog-item-detail"),
]
