from django.urls import path

from . import demo, views

urlpatterns = [
    path("auth/csrf", views.CsrfView.as_view(), name="auth-csrf"),
    path("auth/signup", views.SignupView.as_view(), name="auth-signup"),
    path("auth/login", views.LoginView.as_view(), name="auth-login"),
    path("auth/refresh", views.RefreshView.as_view(), name="auth-refresh"),
    path("auth/logout", views.LogoutView.as_view(), name="auth-logout"),
    path("auth/me", views.MeView.as_view(), name="auth-me"),
    path("demo/config", demo.DemoConfigView.as_view(), name="demo-config"),
    path("demo/switch", demo.DemoSwitchView.as_view(), name="demo-switch"),
    path("auth/me/password", views.MePasswordView.as_view(), name="auth-me-password"),
    path("auth/me/tour", views.MeTourView.as_view(), name="auth-me-tour"),
    path("auth/slug-available", views.SlugAvailableView.as_view(), name="auth-slug-available"),
    path("auth/verify-email", views.VerifyEmailView.as_view(), name="auth-verify-email"),
    path(
        "auth/verify-email/resend",
        views.ResendVerificationView.as_view(),
        name="auth-verify-email-resend",
    ),
    path("auth/password-reset", views.PasswordResetView.as_view(), name="auth-password-reset"),
    path(
        "auth/password-reset/confirm",
        views.PasswordResetConfirmView.as_view(),
        name="auth-password-reset-confirm",
    ),
    path("auth/invitations/<str:token>", views.InvitationView.as_view(), name="auth-invitation"),
    path(
        "auth/invitations/<str:token>/accept",
        views.AcceptInvitationView.as_view(),
        name="auth-invitation-accept",
    ),
]
