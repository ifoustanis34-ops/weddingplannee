from django.urls import path

from . import views

urlpatterns = [
    path("weddings", views.WeddingListView.as_view(), name="wedding-list"),
    path("weddings/<uuid:pk>", views.WeddingDetailView.as_view(), name="wedding-detail"),
    path("weddings/<uuid:pk>/tasks", views.TaskListView.as_view(), name="wedding-tasks"),
    path(
        "weddings/<uuid:pk>/standard-tasks",
        views.StandardTasksView.as_view(),
        name="wedding-standard-tasks",
    ),
    path("tasks/<uuid:pk>", views.TaskDetailView.as_view(), name="task-detail"),
    path("tasks/<uuid:pk>/done", views.TaskDoneView.as_view(), name="task-done"),
    path("calendar", views.CalendarView.as_view(), name="calendar"),
]
