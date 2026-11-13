from django.urls import path

from . import views

urlpatterns = [
    path("organization/branding", views.BrandingView.as_view(), name="branding"),
    path("organization/branding/files", views.BrandingFileView.as_view(), name="branding-files"),
    path("documents/preview", views.PreviewView.as_view(), name="document-preview"),
    path("documents/designs", views.DesignsView.as_view(), name="document-designs"),
]
