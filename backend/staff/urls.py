from django.urls import path

from . import payslips, views

urlpatterns = [
    path("staff", views.StaffListView.as_view(), name="staff-list"),
    path("staff/stats", views.StaffStatsView.as_view(), name="staff-stats"),
    path("staff/planning", views.StaffPlanningView.as_view(), name="staff-planning"),
    path("staff/badges", views.StaffBadgesView.as_view(), name="staff-badges"),
    path(
        "staff/badges/preview",
        views.StaffBadgePreviewView.as_view(),
        name="staff-badge-preview",
    ),
    path("staff/<uuid:pk>", views.StaffDetailView.as_view(), name="staff-detail"),
    path("staff/<uuid:pk>/photo", views.StaffPhotoView.as_view(), name="staff-photo"),
    path("staff/<uuid:pk>/account", views.StaffAccountView.as_view(), name="staff-account"),
    path("assignments", views.AssignmentListView.as_view(), name="assignment-list"),
    path("assignments/<uuid:pk>", views.AssignmentDetailView.as_view(), name="assignment-detail"),
    path(
        "assignments/<uuid:pk>/check-in",
        views.CheckInView.as_view(action="in"),
        name="assignment-check-in",
    ),
    path(
        "assignments/<uuid:pk>/check-out",
        views.CheckInView.as_view(action="out"),
        name="assignment-check-out",
    ),
    path(
        "assignments/<uuid:pk>/absent",
        views.CheckInView.as_view(action="absent"),
        name="assignment-absent",
    ),
    path("staff-tasks", views.TaskListView.as_view(), name="staff-task-list"),
    path("staff-tasks/<uuid:pk>", views.TaskDetailView.as_view(), name="staff-task-detail"),
    path("staff-tasks/<uuid:pk>/photo", views.TaskPhotoView.as_view(), name="staff-task-photo"),
    path(
        "staff-tasks/<uuid:pk>/validate",
        views.TaskReviewView.as_view(action="validate"),
        name="staff-task-validate",
    ),
    path(
        "staff-tasks/<uuid:pk>/reject",
        views.TaskReviewView.as_view(action="reject"),
        name="staff-task-reject",
    ),
    path("me/missions", views.MyMissionsView.as_view(), name="my-missions"),
    path("me/overview", views.MyOverviewView.as_view(), name="my-overview"),
    path("public/badges/<str:token>", views.PublicBadgeView.as_view(), name="public-badge"),
    path("pay/day", views.DaySheetView.as_view(), name="pay-day"),
    path("pay/day/sheet", views.DayPaySheetView.as_view(), name="pay-day-sheet"),
    path("staff-payments", views.StaffPaymentListView.as_view(), name="staff-payment-list"),
    path("pay-periods", views.PayPeriodListView.as_view(), name="pay-period-list"),
    path(
        "pay-periods/<uuid:pk>/refresh",
        views.PayPeriodActionView.as_view(action="refresh"),
        name="pay-period-refresh",
    ),
    path(
        "pay-periods/<uuid:pk>/validate",
        views.PayPeriodActionView.as_view(action="validate"),
        name="pay-period-validate",
    ),
    path("pay-lines/<uuid:pk>", views.PayLineView.as_view(), name="pay-line-detail"),
    path("pay-lines/<uuid:pk>/pay", views.PayLinePayView.as_view(), name="pay-line-pay"),
    path(
        "pay-lines/<uuid:pk>/statement",
        payslips.PayslipView.as_view(),
        name="pay-line-statement",
    ),
    path(
        "pay-periods/<uuid:pk>/payslips",
        payslips.PeriodPayslipsView.as_view(),
        name="pay-period-payslips",
    ),
    path(
        "staff-payments/<uuid:pk>/slip",
        payslips.PaymentSlipView.as_view(),
        name="staff-payment-slip",
    ),
    path("pay/day/slips", payslips.DaySlipsView.as_view(), name="pay-day-slips"),
    path("pay/settings", payslips.PayrollSettingsView.as_view(), name="pay-settings"),
    path("staff/<uuid:pk>/salary", payslips.SalaryView.as_view(), name="staff-salary"),
]
