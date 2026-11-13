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
]
