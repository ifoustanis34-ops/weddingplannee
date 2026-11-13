from __future__ import annotations

from typing import Any

from django.db.models import QuerySet
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import generics, serializers, status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Membership
from core.permissions import IsTenantMember, roles_allowed
from finance.permissions import role_of
from finance.visibility import can_see_balances

from . import calendar, selectors, services
from .models import Task, Wedding
from .permissions import CALENDAR_ROLES, WEDDING_PERMISSIONS
from .serializers import CalendarQuerySerializer, TaskSerializer, WeddingSerializer


class WeddingListView(generics.ListCreateAPIView[Wedding]):
    """« Mariages » (complement §11): cards with progress; « Nouveau mariage »."""

    serializer_class = WeddingSerializer
    permission_classes = WEDDING_PERMISSIONS
    pagination_class = None

    def get_queryset(self) -> QuerySet[Wedding]:
        if getattr(self, "swagger_fake_view", False):
            return Wedding.all_tenants.none()
        weddings = selectors.weddings_with_metrics()
        if self.request.query_params.get("status") != "all":
            weddings = weddings.exclude(status=Wedding.Status.CANCELLED)
        return weddings

    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        serializer = WeddingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        standard = data.pop("standard_tasks", False)
        wedding = services.create_wedding(data, standard_tasks=standard, user=request.user)  # type: ignore[arg-type]
        fresh = selectors.weddings_with_metrics().get(pk=wedding.pk)
        return Response(WeddingSerializer(fresh).data, status=status.HTTP_201_CREATED)


class WeddingDetailView(generics.RetrieveUpdateDestroyAPIView[Wedding]):
    serializer_class = WeddingSerializer
    permission_classes = WEDDING_PERMISSIONS
    http_method_names = ["get", "patch", "delete"]

    def get_queryset(self) -> QuerySet[Wedding]:
        if getattr(self, "swagger_fake_view", False):
            return Wedding.all_tenants.none()
        return selectors.weddings_with_metrics()

    def update(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        super().update(request, *args, **kwargs)
        return Response(WeddingSerializer(self.get_queryset().get(pk=kwargs["pk"])).data)

    def perform_destroy(self, instance: Wedding) -> None:
        services.delete_wedding(instance)


class StandardTasksView(APIView):
    """Append the agency's standard list to an existing wedding."""

    permission_classes = WEDDING_PERMISSIONS

    @extend_schema(request=None, responses={201: TaskSerializer(many=True)})
    def post(self, request: Request, pk: str) -> Response:
        wedding = get_object_or_404(Wedding.objects.all(), pk=pk)
        tasks = services.add_standard_tasks(wedding, user=request.user)  # type: ignore[arg-type]
        return Response(TaskSerializer(tasks, many=True).data, status=status.HTTP_201_CREATED)


class TaskListView(generics.ListCreateAPIView[Task]):
    serializer_class = TaskSerializer
    permission_classes = WEDDING_PERMISSIONS
    pagination_class = None

    def wedding(self) -> Wedding:
        wedding: Wedding = get_object_or_404(Wedding.objects.all(), pk=self.kwargs["pk"])
        return wedding

    def get_queryset(self) -> QuerySet[Task]:
        if getattr(self, "swagger_fake_view", False):
            return Task.all_tenants.none()
        return Task.objects.filter(wedding=self.wedding()).select_related("assignee")

    def perform_create(self, serializer: TaskSerializer) -> None:  # type: ignore[override]
        serializer.save(wedding=self.wedding(), created_by=self.request.user)


class TaskDetailView(generics.RetrieveUpdateDestroyAPIView[Task]):
    serializer_class = TaskSerializer
    permission_classes = WEDDING_PERMISSIONS
    http_method_names = ["get", "patch", "delete"]

    def get_queryset(self) -> QuerySet[Task]:
        if getattr(self, "swagger_fake_view", False):
            return Task.all_tenants.none()
        return Task.objects.select_related("assignee")


class TaskDoneView(APIView):
    """Tick or untick a task (« faite » = green box, struck-through title)."""

    permission_classes = WEDDING_PERMISSIONS

    @extend_schema(
        request=inline_serializer("TaskDone", {"done": serializers.BooleanField()}),
        responses=TaskSerializer,
    )
    def post(self, request: Request, pk: str) -> Response:
        task = get_object_or_404(Task.objects.select_related("assignee"), pk=pk)
        done = bool(request.data.get("done", True))
        return Response(TaskSerializer(services.set_task_done(task, done)).data)


class CalendarView(APIView):
    """Centralized calendar (reservations-stock.md §4.3): reservation steps, weddings, tasks,
    maintenance and expected payments. The storekeeper reads it too (deliveries and returns),
    never with amounts."""

    permission_classes = [IsTenantMember, roles_allowed(*CALENDAR_ROLES)]
    open_to_field_roles = True

    @extend_schema(
        parameters=[
            OpenApiParameter("from", str, required=True),
            OpenApiParameter("to", str, required=True),
            OpenApiParameter("member", str),
            OpenApiParameter("kinds", str, description="event,delivery,setup,… (virgules)"),
            OpenApiParameter("statuses", str, description="Statuts de réservation (virgules)"),
        ],
        responses=inline_serializer(
            "CalendarItem",
            {
                "kind": serializers.ChoiceField(choices=calendar.KINDS),
                "id": serializers.CharField(),
                "date": serializers.DateField(),
                "end_date": serializers.DateField(allow_null=True),
                "time": serializers.CharField(allow_null=True),
                "title": serializers.CharField(),
                "subtitle": serializers.CharField(),
                "status": serializers.CharField(allow_null=True),
                "team": serializers.ListField(child=serializers.CharField()),
                "owner": serializers.CharField(allow_null=True),
                "vehicle": serializers.CharField(),
                "wedding": serializers.UUIDField(allow_null=True),
                "reservation": serializers.UUIDField(allow_null=True),
                "contract": serializers.UUIDField(allow_null=True),
                "item": serializers.UUIDField(allow_null=True),
                "amount": serializers.IntegerField(allow_null=True),
                "movable": serializers.BooleanField(),
            },
            many=True,
        ),
    )
    def get(self, request: Request) -> Response:
        query = CalendarQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        data = query.validated_data
        member = data.get("member")
        role = role_of(request)
        return Response(
            calendar.build(
                data["from"],
                data["to"],
                member=str(member) if member else None,
                kinds=data.get("kinds") or None,
                statuses=data.get("statuses") or None,
                with_money=can_see_balances(role),
                movable=role in (Membership.Role.OWNER, Membership.Role.PLANNER),
            )
        )
