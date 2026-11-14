from django.urls import path

from . import views

urlpatterns = [
    path("platform/overview", views.OverviewView.as_view(), name="platform-overview"),
    path("platform/agencies", views.AgencyListView.as_view(), name="platform-agencies"),
    path("platform/agencies/<uuid:pk>", views.AgencyDetailView.as_view(), name="platform-agency"),
    path(
        "platform/agencies/<uuid:pk>/members",
        views.AgencyMembersView.as_view(),
        name="platform-agency-members",
    ),
    path("platform/users", views.AccountListView.as_view(), name="platform-users"),
    path("platform/users/<uuid:pk>", views.AccountDetailView.as_view(), name="platform-user"),
    path(
        "platform/users/<uuid:pk>/password",
        views.AccountPasswordView.as_view(),
        name="platform-user-password",
    ),
    path(
        "platform/users/<uuid:pk>/memberships",
        views.AccountMembershipsView.as_view(),
        name="platform-user-memberships",
    ),
    path(
        "platform/memberships/<uuid:pk>",
        views.MembershipDetailView.as_view(),
        name="platform-membership",
    ),
    path("platform/journal", views.JournalView.as_view(), name="platform-journal"),
]
