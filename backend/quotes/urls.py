from django.urls import path

from . import public_views, views

urlpatterns = [
    path("quotes", views.QuoteListView.as_view(), name="quote-list"),
    path("quotes/summary", views.QuoteSummaryView.as_view(), name="quote-summary"),
    path("quotes/stats", views.QuoteStatsView.as_view(), name="quote-stats"),
    path("quotes/<uuid:pk>", views.QuoteDetailView.as_view(), name="quote-detail"),
    path("quotes/<uuid:pk>/send", views.SendQuoteView.as_view(), name="quote-send"),
    path("quotes/<uuid:pk>/accept", views.AcceptQuoteView.as_view(), name="quote-accept"),
    path("quotes/<uuid:pk>/refuse", views.RefuseQuoteView.as_view(), name="quote-refuse"),
    path("quotes/<uuid:pk>/duplicate", views.DuplicateQuoteView.as_view(), name="quote-duplicate"),
    path("quotes/<uuid:pk>/convert", views.ConvertQuoteView.as_view(), name="quote-convert"),
    path("quotes/<uuid:pk>/pdf", views.QuotePdfView.as_view(), name="quote-pdf"),
    path("quotes/<uuid:pk>/generate", views.GenerateQuoteView.as_view(), name="quote-generate"),
    path("public/quotes/<str:token>", public_views.PublicQuoteView.as_view(), name="public-quote"),
    path(
        "public/quotes/<str:token>/accept",
        public_views.PublicAcceptView.as_view(),
        name="public-quote-accept",
    ),
    path(
        "public/quotes/<str:token>/refuse",
        public_views.PublicRefuseView.as_view(),
        name="public-quote-refuse",
    ),
    path(
        "public/quotes/<str:token>/pdf",
        public_views.PublicPdfView.as_view(),
        name="public-quote-pdf",
    ),
    path(
        "public/quotes/<str:token>/preview",
        public_views.PublicPreviewView.as_view(),
        name="public-quote-preview",
    ),
]
