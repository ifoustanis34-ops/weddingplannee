from django.urls import path

from .views import (
    InvitationDetailView,
    InvitationListView,
    MemberDetailView,
    MemberListView,
    MemberPasswordView,
    OrganizationView,
    PlanChangeView,
    PlanListView,
)

urlpatterns = [
    path("organization", OrganizationView.as_view(), name="organization"),
    path("organization/members", MemberListView.as_view(), name="organization-members"),
    path("organization/members/<uuid:pk>", MemberDetailView.as_view(), name="organization-member"),
    path(
        "organization/members/<uuid:pk>/password",
        MemberPasswordView.as_view(),
        name="organization-member-password",
    ),
    path("organization/invitations", InvitationListView.as_view(), name="organization-invitations"),
    path(
        "organization/invitations/<uuid:pk>",
        InvitationDetailView.as_view(),
        name="organization-invitation",
    ),
    path("organization/plan", PlanChangeView.as_view(), name="organization-plan"),
    path("plans", PlanListView.as_view(), name="plans"),
]
