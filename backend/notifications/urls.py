from django.urls import path

from . import views

urlpatterns = [
    path("push/config", views.PushConfigView.as_view(), name="push-config"),
    path("push/subscriptions", views.SubscriptionView.as_view(), name="push-subscriptions"),
    path(
        "push/subscriptions/remove",
        views.SubscriptionRemoveView.as_view(),
        name="push-subscriptions-remove",
    ),
    path("push/test", views.PushTestView.as_view(), name="push-test"),
    path("notifications", views.NotificationListView.as_view(), name="notifications"),
    path(
        "notifications/read-all",
        views.NotificationReadAllView.as_view(),
        name="notifications-read-all",
    ),
    path(
        "notifications/<uuid:pk>/read",
        views.NotificationReadView.as_view(),
        name="notification-read",
    ),
]
