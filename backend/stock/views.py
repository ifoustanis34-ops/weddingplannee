from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from django.db.models import Q, QuerySet, Sum
from django.http import HttpResponse
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import generics, status
from rest_framework.parsers import MultiPartParser
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Membership
from core.exceptions import BusinessError
from core.pagination import DefaultCursorPagination
from core.permissions import IsTenantMember

from . import availability, imports, labels, partners, selectors, services
from .models import (
    Inventory,
    Item,
    ItemCategory,
    ItemUnit,
    Maintenance,
    Pack,
    PartnerSupply,
    StockMovement,
)
from .permissions import StockPermission, can_see_costs, role_of
from .serializers import (
    CancelSerializer,
    CloseMaintenanceSerializer,
    CountSerializer,
    InventorySerializer,
    ItemCategorySerializer,
    ItemSerializer,
    ItemUnitSerializer,
    MaintenanceSerializer,
    MovementInputSerializer,
    MovementSerializer,
    PackSerializer,
    PartnerSupplySerializer,
)

PERMISSIONS = [IsTenantMember, StockPermission]
Role = Membership.Role
MAX_GRID_DAYS = 62
MAX_PERIOD_DAYS = 366


class StockView:
    """Every stock view: the storekeeper reaches them (§12), the role rules apply after."""

    permission_classes: Any = PERMISSIONS
    open_to_field_roles = True


def _date(request: Request, name: str, default: date | None = None) -> date | None:
    raw = request.query_params.get(name)
    if not raw:
        return default
    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise BusinessError("invalid", "Date illisible (AAAA-MM-JJ).", {name: ["Date"]}) from exc


def _period(request: Request) -> tuple[date, date]:
    today = services.today()
    start = _date(request, "from", today) or today
    end = _date(request, "to", start) or start
    if end < start:
        raise BusinessError("invalid", "La fin doit suivre le début.", {"to": ["Avant le début."]})
    if (end - start).days > MAX_PERIOD_DAYS:
        raise BusinessError("invalid", "Un an au maximum.", {"to": ["Période trop longue."]})
    return start, end


# --- Categories ---------------------------------------------------------------------------------


class CategoryListView(StockView, generics.ListCreateAPIView[ItemCategory]):
    serializer_class = ItemCategorySerializer
    pagination_class = None

    def get_queryset(self) -> QuerySet[ItemCategory]:
        if getattr(self, "swagger_fake_view", False):
            return ItemCategory.all_tenants.none()
        return ItemCategory.objects.all()

    def perform_create(self, serializer: ItemCategorySerializer) -> None:  # type: ignore[override]
        serializer.save(created_by=self.request.user)


class CategoryDetailView(StockView, generics.RetrieveUpdateAPIView[ItemCategory]):
    serializer_class = ItemCategorySerializer
    http_method_names = ["get", "patch"]

    def get_queryset(self) -> QuerySet[ItemCategory]:
        if getattr(self, "swagger_fake_view", False):
            return ItemCategory.all_tenants.none()
        return ItemCategory.objects.all()


# --- Items --------------------------------------------------------------------------------------


class ItemListView(StockView, generics.ListCreateAPIView[Item]):
    """`?search=`, `?category=`, `?status=available|maintenance|out_of_service|low`,
    `?inactive=true`. Each item carries its stock of today by status."""

    serializer_class = ItemSerializer
    pagination_class = None

    def get_queryset(self) -> QuerySet[Item]:
        if getattr(self, "swagger_fake_view", False):
            return Item.all_tenants.none()
        params = self.request.query_params
        items = Item.objects.select_related("category").annotate(
            partner_total=Sum(
                "partner_supplies__quantity", filter=Q(partner_supplies__is_active=True)
            )
        )
        # « Notre matériel » / « Matériel des partenaires » (feedback 14/11/2026).
        if params.get("source") == "own":
            items = items.filter(total_quantity__gt=0)
        elif params.get("source") == "partner":
            items = items.filter(partner_total__gt=0)
        if params.get("inactive") != "true":
            items = items.filter(is_active=True)
        if params.get("category"):
            items = items.filter(category_id=params["category"])
        if params.get("search"):
            term = params["search"].strip()
            items = items.filter(Q(name__icontains=term) | Q(reference__icontains=term))
        result: QuerySet[Item] = items
        return result

    def get_serializer_context(self) -> dict[str, Any]:
        context = super().get_serializer_context()
        if not getattr(self, "swagger_fake_view", False):
            today = services.today()
            context["availability"] = availability.compute(self.get_queryset(), today, today, today)
        return context

    def list(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        items = list(self.get_queryset())
        context = self.get_serializer_context()
        state = request.query_params.get("status")
        if state:
            items = selectors.filter_by_state(items, context["availability"], state)
        return Response(ItemSerializer(items, many=True, context=context).data)

    def perform_create(self, serializer: ItemSerializer) -> None:  # type: ignore[override]
        item = services.create_item(
            dict(serializer.validated_data), user=self.request.user  # type: ignore[arg-type]
        )
        serializer.instance = item


class ItemDetailView(StockView, generics.RetrieveUpdateAPIView[Item]):
    serializer_class = ItemSerializer
    http_method_names = ["get", "patch"]

    def get_queryset(self) -> QuerySet[Item]:
        if getattr(self, "swagger_fake_view", False):
            return Item.all_tenants.none()
        return Item.objects.select_related("category")

    def get_serializer_context(self) -> dict[str, Any]:
        context = super().get_serializer_context()
        if not getattr(self, "swagger_fake_view", False) and "pk" in self.kwargs:
            today = services.today()
            context["availability"] = availability.compute(
                self.get_queryset().filter(pk=self.kwargs["pk"]), today, today, today
            )
        return context

    def perform_update(self, serializer: ItemSerializer) -> None:  # type: ignore[override]
        assert serializer.instance is not None
        services.update_item(serializer.instance, dict(serializer.validated_data))


class ItemPhotoView(StockView, APIView):
    parser_classes = [MultiPartParser]

    def _item(self, pk: str) -> Item:
        item: Item = generics.get_object_or_404(Item.objects.all(), pk=pk)
        return item

    @extend_schema(request={"multipart/form-data": OpenApiTypes.OBJECT}, responses=ItemSerializer)
    def post(self, request: Request, pk: str) -> Response:
        upload = request.FILES.get("file")
        if upload is None:
            raise BusinessError("invalid", "Choisissez une photo.", {"file": ["Obligatoire."]})
        if upload.size and upload.size > 8 * 1024 * 1024:
            raise BusinessError("invalid", "Photo trop lourde : 8 Mo maximum.", {"file": ["8 Mo"]})
        item = services.store_photo(self._item(pk), upload.read())
        return Response(ItemSerializer(item, context={"request": request}).data)

    @extend_schema(responses={204: None})
    def delete(self, request: Request, pk: str) -> Response:
        services.remove_photo(self._item(pk))
        return Response(status=status.HTTP_204_NO_CONTENT)


class ItemActivityView(StockView, APIView):
    """Item sheet (§5.5): occupancy of the next 30 days and its last movements."""

    @extend_schema(responses={200: OpenApiResponse(OpenApiTypes.OBJECT)})
    def get(self, request: Request, pk: str) -> Response:
        item = generics.get_object_or_404(Item.objects.select_related("category"), pk=pk)
        today = services.today()
        grid = availability.daily_grid([item], today, 30, today)[str(item.pk)]
        movements = item.movements.select_related("author", "unit")[:20]
        units = item.units.all()
        maintenances = item.maintenances.select_related("unit").filter(ended_at__isnull=True)
        context = {"request": request}
        return Response(
            {
                "occupancy": [
                    {
                        "date": today + timedelta(days=offset),
                        "available": value.available,
                        "total": value.total,
                    }
                    for offset, value in enumerate(grid)
                ],
                "movements": MovementSerializer(movements, many=True, context=context).data,
                "units": ItemUnitSerializer(units, many=True).data,
                "maintenances": MaintenanceSerializer(
                    maintenances, many=True, context=context
                ).data,
            }
        )


class ItemLabelsView(StockView, APIView):
    """Printable QR labels (§5.3): one per unit for numbered equipment, else `?count=` copies."""

    @extend_schema(
        parameters=[OpenApiParameter("count", int)],
        responses={(200, "application/pdf"): bytes},
    )
    def get(self, request: Request, pk: str) -> HttpResponse:
        item = generics.get_object_or_404(Item.objects.all(), pk=pk)
        try:
            count = int(request.query_params.get("count", "1"))
        except ValueError:
            count = 1
        pdf = labels.render([item], copies=max(1, min(count, 240)))
        response = HttpResponse(pdf, content_type="application/pdf")
        response["Content-Disposition"] = f'inline; filename="etiquettes-{item.reference}.pdf"'
        return response


class UnitListView(StockView, generics.ListCreateAPIView[ItemUnit]):
    serializer_class = ItemUnitSerializer
    pagination_class = None

    def get_queryset(self) -> QuerySet[ItemUnit]:
        if getattr(self, "swagger_fake_view", False):
            return ItemUnit.all_tenants.none()
        return ItemUnit.objects.filter(item_id=self.kwargs["pk"])

    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        # New units are a purchase: the owned quantity and the journal follow.
        raise BusinessError(
            "invalid", "Ajoutez des unités par un achat (mouvement « Achat »).", status_code=400
        )


class UnitDetailView(StockView, generics.RetrieveUpdateAPIView[ItemUnit]):
    """Condition, notes, back in or out of service (sold, lost, maintenance: movements)."""

    serializer_class = ItemUnitSerializer
    http_method_names = ["get", "patch"]

    def get_queryset(self) -> QuerySet[ItemUnit]:
        if getattr(self, "swagger_fake_view", False):
            return ItemUnit.all_tenants.none()
        return ItemUnit.objects.all()


# --- Packs and availability ---------------------------------------------------------------------


class PackListView(StockView, generics.ListCreateAPIView[Pack]):
    """`?from=&to=` gives how many of each pack are available over the period."""

    serializer_class = PackSerializer
    pagination_class = None

    def get_queryset(self) -> QuerySet[Pack]:
        if getattr(self, "swagger_fake_view", False):
            return Pack.all_tenants.none()
        return Pack.objects.prefetch_related("components__item")

    def get_serializer_context(self) -> dict[str, Any]:
        context = super().get_serializer_context()
        if not getattr(self, "swagger_fake_view", False):
            start, end = _period(self.request)
            context["pack_available"] = selectors.pack_counts(list(self.get_queryset()), start, end)
        return context

    def perform_create(self, serializer: PackSerializer) -> None:  # type: ignore[override]
        serializer.instance = services.save_pack(
            None, dict(serializer.validated_data), user=self.request.user  # type: ignore[arg-type]
        )


class PackDetailView(StockView, generics.RetrieveUpdateAPIView[Pack]):
    serializer_class = PackSerializer
    http_method_names = ["get", "patch"]

    def get_queryset(self) -> QuerySet[Pack]:
        if getattr(self, "swagger_fake_view", False):
            return Pack.all_tenants.none()
        return Pack.objects.prefetch_related("components__item")

    def perform_update(self, serializer: PackSerializer) -> None:  # type: ignore[override]
        assert serializer.instance is not None
        services.save_pack(
            serializer.instance,
            dict(serializer.validated_data),
            user=self.request.user,  # type: ignore[arg-type]
        )


class AvailabilityView(StockView, APIView):
    """`GET /availability?items=<id>,<id>&from=&to=` (all active items without `items`)."""

    @extend_schema(
        parameters=[
            OpenApiParameter("items", str),
            OpenApiParameter("from", OpenApiTypes.DATE),
            OpenApiParameter("to", OpenApiTypes.DATE),
        ],
        responses={200: OpenApiResponse(OpenApiTypes.OBJECT)},
    )
    def get(self, request: Request) -> Response:
        start, end = _period(request)
        items = Item.objects.filter(is_active=True)
        ids = [i for i in request.query_params.get("items", "").split(",") if i]
        if ids:
            items = items.filter(pk__in=ids)
        # ?exclude=<reservation>: its own lines do not count (editing that reservation).
        values = availability.compute(
            items.select_related("category"),
            start,
            end,
            services.today(),
            exclude_reservation=request.query_params.get("exclude") or None,
        )
        return Response(
            {
                "from": start,
                "to": end,
                "items": [
                    {
                        "item": item_id,
                        "total": v.total,
                        "available": v.available,
                        "reserved": v.reserved,
                        "out": v.out,
                        "maintenance": v.maintenance,
                        "out_of_service": v.out_of_service,
                    }
                    for item_id, v in values.items()
                ],
            }
        )


class AvailabilityGridView(StockView, APIView):
    """`GET /availability/grid?from=&days=30&category=`: articles × days, occupancy rate."""

    @extend_schema(responses={200: OpenApiResponse(OpenApiTypes.OBJECT)})
    def get(self, request: Request) -> Response:
        today = services.today()
        start = _date(request, "from", today) or today
        try:
            days = max(1, min(int(request.query_params.get("days", "30")), MAX_GRID_DAYS))
        except ValueError:
            days = 30
        items = list(Item.objects.filter(is_active=True).select_related("category"))
        if request.query_params.get("category"):
            items = [i for i in items if str(i.category_id) == request.query_params["category"]]
        return Response(selectors.grid(items, start, days, today))


# --- Movements, maintenance, inventories --------------------------------------------------------


class MovementPagination(DefaultCursorPagination):
    ordering = "-occurred_at"
    page_size = 50


class MovementListView(StockView, generics.ListCreateAPIView[StockMovement]):
    """Journal: `?item=`, `?kind=`, `?from=`, `?to=`. Manual movements by POST."""

    serializer_class = MovementSerializer
    pagination_class = MovementPagination

    def get_queryset(self) -> QuerySet[StockMovement]:
        if getattr(self, "swagger_fake_view", False):
            return StockMovement.all_tenants.none()
        params = self.request.query_params
        movements = StockMovement.objects.select_related("item", "unit", "author")
        if params.get("item"):
            movements = movements.filter(item_id=params["item"])
        if params.get("kind"):
            movements = movements.filter(kind__in=params["kind"].split(","))
        start = _date(self.request, "from")
        end = _date(self.request, "to")
        if start:
            movements = movements.filter(occurred_at__date__gte=start)
        if end:
            movements = movements.filter(occurred_at__date__lte=end)
        return movements

    @extend_schema(request=MovementInputSerializer, responses={201: MovementSerializer})
    def post(self, request: Request) -> Response:
        serializer = MovementInputSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        if data.get("unit_cost") is not None and not can_see_costs(role_of(request)):
            data["unit_cost"] = None  # the storekeeper records quantities, never amounts
        movement = services.record_movement(
            data.pop("item"),
            kind=data.pop("kind"),
            quantity=data.pop("quantity"),
            direction=int(data.pop("direction")),
            user=request.user,  # type: ignore[arg-type]
            **data,
        )
        return Response(
            MovementSerializer(movement, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class MovementCancelView(StockView, APIView):
    @extend_schema(request=CancelSerializer, responses=MovementSerializer)
    def post(self, request: Request, pk: str) -> Response:
        movement = generics.get_object_or_404(StockMovement.objects.all(), pk=pk)
        serializer = CancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.cancel_movement(
            movement,
            reason=serializer.validated_data["reason"],
            user=request.user,  # type: ignore[arg-type]
            request=request,
        )
        movement.refresh_from_db()
        return Response(MovementSerializer(movement, context={"request": request}).data)


class MaintenanceListView(StockView, generics.ListCreateAPIView[Maintenance]):
    """`?open=true` for the equipment still away."""

    serializer_class = MaintenanceSerializer
    pagination_class = None

    def get_queryset(self) -> QuerySet[Maintenance]:
        if getattr(self, "swagger_fake_view", False):
            return Maintenance.all_tenants.none()
        rows = Maintenance.objects.select_related("item", "unit")
        if self.request.query_params.get("open") == "true":
            rows = rows.filter(ended_at__isnull=True)
        return rows

    def perform_create(self, serializer: MaintenanceSerializer) -> None:  # type: ignore[override]
        data = serializer.validated_data
        serializer.instance = services.start_maintenance(
            data["item"],
            reason=data["reason"],
            quantity=data.get("quantity", 1),
            unit=data.get("unit"),
            expected_end=data.get("expected_end"),
            user=self.request.user,  # type: ignore[arg-type]
        )


class MaintenanceCloseView(StockView, APIView):
    @extend_schema(request=CloseMaintenanceSerializer, responses=MaintenanceSerializer)
    def post(self, request: Request, pk: str) -> Response:
        maintenance = generics.get_object_or_404(Maintenance.objects.all(), pk=pk)
        serializer = CloseMaintenanceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        cost = serializer.validated_data.get("cost")
        if not can_see_costs(role_of(request)):
            cost = None
        services.close_maintenance(
            maintenance,
            cost=cost,
            notes=serializer.validated_data["notes"],
            user=request.user,  # type: ignore[arg-type]
        )
        maintenance.refresh_from_db()
        return Response(MaintenanceSerializer(maintenance, context={"request": request}).data)


class InventoryListView(StockView, generics.ListCreateAPIView[Inventory]):
    serializer_class = InventorySerializer
    pagination_class = None

    def get_queryset(self) -> QuerySet[Inventory]:
        if getattr(self, "swagger_fake_view", False):
            return Inventory.all_tenants.none()
        return Inventory.objects.select_related("category", "author").prefetch_related(
            "lines__item__category"
        )

    def perform_create(self, serializer: InventorySerializer) -> None:  # type: ignore[override]
        serializer.instance = services.start_inventory(
            category=serializer.validated_data.get("category"),
            user=self.request.user,  # type: ignore[arg-type]
        )


class InventoryDetailView(StockView, generics.RetrieveAPIView[Inventory]):
    serializer_class = InventorySerializer

    def get_queryset(self) -> QuerySet[Inventory]:
        if getattr(self, "swagger_fake_view", False):
            return Inventory.all_tenants.none()
        return Inventory.objects.prefetch_related("lines__item__category")

    @extend_schema(request=CountSerializer, responses=InventorySerializer)
    def patch(self, request: Request, pk: str) -> Response:
        inventory = self.get_object()
        serializer = CountSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.count(inventory, serializer.validated_data["counts"])
        return Response(InventorySerializer(self.get_queryset().get(pk=pk)).data)


class InventoryValidateView(StockView, APIView):
    @extend_schema(request=None, responses=InventorySerializer)
    def post(self, request: Request, pk: str) -> Response:
        inventory = generics.get_object_or_404(Inventory.objects.all(), pk=pk)
        services.validate_inventory(
            inventory, user=request.user, request=request  # type: ignore[arg-type]
        )
        return Response(
            InventorySerializer(
                Inventory.objects.prefetch_related("lines__item__category").get(pk=pk)
            ).data
        )


class StockStatsView(StockView, APIView):
    """Tiles of the stock screen (§5.5); the value only for owner and accountant."""

    @extend_schema(responses={200: OpenApiResponse(OpenApiTypes.OBJECT)})
    def get(self, request: Request) -> Response:
        data = selectors.stats()
        if not can_see_costs(role_of(request)):
            data["stock_value"] = None
        return Response(data)


# --- Partner equipment (feedback 14/11/2026) ----------------------------------------------------


class PartnerSupplyListView(StockView, generics.ListCreateAPIView[PartnerSupply]):
    """`?vendor=`, `?item=`, `?search=`, `?inactive=true`. Same roles as the stock."""

    serializer_class = PartnerSupplySerializer
    pagination_class = None

    def get_queryset(self) -> QuerySet[PartnerSupply]:
        if getattr(self, "swagger_fake_view", False):
            return PartnerSupply.all_tenants.none()
        params = self.request.query_params
        supplies = PartnerSupply.objects.select_related("item__category", "vendor")
        if params.get("inactive") != "true":
            supplies = supplies.filter(is_active=True)
        if params.get("vendor"):
            supplies = supplies.filter(vendor_id=params["vendor"])
        if params.get("item"):
            supplies = supplies.filter(item_id=params["item"])
        if params.get("search"):
            term = params["search"].strip()
            supplies = supplies.filter(
                Q(item__name__icontains=term)
                | Q(item__reference__icontains=term)
                | Q(vendor__name__icontains=term)
            )
        return supplies

    def perform_create(self, serializer: PartnerSupplySerializer) -> None:  # type: ignore[override]
        serializer.instance = partners.create_supply(
            dict(serializer.validated_data), user=self.request.user  # type: ignore[arg-type]
        )


class PartnerSupplyDetailView(StockView, generics.RetrieveUpdateDestroyAPIView[PartnerSupply]):
    serializer_class = PartnerSupplySerializer
    http_method_names = ["get", "patch", "delete"]

    def get_queryset(self) -> QuerySet[PartnerSupply]:
        if getattr(self, "swagger_fake_view", False):
            return PartnerSupply.all_tenants.none()
        return PartnerSupply.objects.select_related("item__category", "vendor")

    def perform_update(self, serializer: PartnerSupplySerializer) -> None:  # type: ignore[override]
        assert serializer.instance is not None
        partners.update_supply(serializer.instance, dict(serializer.validated_data))

    @extend_schema(responses={200: OpenApiResponse(OpenApiTypes.OBJECT)})
    def delete(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        deleted = partners.delete_supply(self.get_object())
        return Response({"deleted": deleted})


class StockImportView(StockView, APIView):
    """`POST` a .xlsx / .csv with both lists (ours and the partners'); `?dry_run=true` only
    reports what would change. Owner only: the file carries prices and costs."""

    parser_classes = [MultiPartParser]

    @extend_schema(
        request={"multipart/form-data": OpenApiTypes.OBJECT},
        parameters=[OpenApiParameter("dry_run", bool)],
        responses={200: OpenApiResponse(OpenApiTypes.OBJECT)},
    )
    def post(self, request: Request) -> Response:
        if role_of(request) != Role.OWNER:
            raise BusinessError(
                "role_forbidden",
                "Seul le propriétaire importe les listes du matériel (elles portent les prix).",
                status_code=403,
            )
        upload = request.FILES.get("file")
        if upload is None:
            raise BusinessError("invalid", "Choisissez le fichier.", {"file": ["Manquant."]})
        report = imports.run(
            upload,
            user=request.user,  # type: ignore[arg-type]
            dry_run=request.query_params.get("dry_run") == "true",
        )
        return Response(report.as_dict())


class StockImportTemplateView(StockView, APIView):
    @extend_schema(responses={(200, "application/vnd.ms-excel"): bytes})
    def get(self, request: Request) -> HttpResponse:
        response = HttpResponse(
            imports.template(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = 'attachment; filename="modele-materiel-wedivo.xlsx"'
        return response
