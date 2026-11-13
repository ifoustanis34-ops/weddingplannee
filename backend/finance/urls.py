from django.urls import path

from . import billing, views

urlpatterns = [
    path("expenses", views.ExpenseListView.as_view(), name="expense-list"),
    path("expenses/<uuid:pk>", views.ExpenseDetailView.as_view(), name="expense-detail"),
    path("expense-categories", views.ExpenseCategoryListView.as_view(), name="expense-categories"),
    path(
        "expense-categories/<uuid:pk>",
        views.ExpenseCategoryDetailView.as_view(),
        name="expense-category-detail",
    ),
    path(
        "expenses/<uuid:pk>/receipt", billing.ExpenseReceiptView.as_view(), name="expense-receipt"
    ),
    path("invoices", billing.InvoiceListView.as_view(), name="invoice-list"),
    path("invoices/<uuid:pk>", billing.InvoiceDetailView.as_view(), name="invoice-detail"),
    path("invoices/<uuid:pk>/pdf", billing.InvoicePdfView.as_view(), name="invoice-pdf"),
    path("invoices/<uuid:pk>/credit", billing.InvoiceCreditView.as_view(), name="invoice-credit"),
    path("credit-notes", billing.CreditNoteListView.as_view(), name="credit-note-list"),
    path("credit-notes/<uuid:pk>/pdf", billing.CreditNotePdfView.as_view(), name="credit-note-pdf"),
    path("revenues", billing.RevenueListView.as_view(), name="revenue-list"),
    path(
        "finance/profitability", billing.ProfitabilityView.as_view(), name="finance-profitability"
    ),
    path("reports/<slug:kind>", billing.ReportView.as_view(), name="report"),
    path("finance/treasury", billing.TreasuryView.as_view(), name="finance-treasury"),
    path("finance/summary", views.FinanceSummaryView.as_view(), name="finance-summary"),
    path("finance/export", views.FinanceExportView.as_view(), name="finance-export"),
    path("dashboard/summary", views.DashboardView.as_view(), name="dashboard-summary"),
]
