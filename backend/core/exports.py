"""« Télécharger » on every screen (product request, Nov. 2026): the same button, at the same
place, gives PDF (the agency's colors), CSV and Excel of what the screen lists.

`GET /exports/{kind}?output=pdf|csv|xlsx&…the screen's filters`. Each export has the reading
rights of its screen, and amounts follow the same role rules (no balance, price, cost or pay to a
role that does not see them on screen). Every export is audited.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from django.utils import timezone

from accounts.models import Membership
from core.exceptions import BusinessError
from core.tenant import require_current_organization
from organizations.timezones import org_tz

Role = Membership.Role
SALES = frozenset({Role.OWNER, Role.PLANNER, Role.ASSISTANT, Role.ACCOUNTANT})
MAX_ROWS = 5000


def _col(key: str, label: str, kind: str = "text") -> dict[str, str]:
    return {"key": key, "label": label, "kind": kind}


def _today() -> date:
    return timezone.now().astimezone(org_tz(require_current_organization())).date()


def _local_day(moment: Any) -> date | None:
    if moment is None:
        return None
    return timezone.localtime(moment, org_tz(require_current_organization())).date()


def _balances(role: str | None) -> bool:
    from finance.visibility import can_see_balances

    return can_see_balances(role)


def _margins(role: str | None) -> bool:
    from finance.visibility import can_see_margins

    return can_see_margins(role)


# --- Builders: (params, role) → title, subtitle, columns, rows -----------------------------------


def reservations(params: Any, role: str | None) -> dict[str, Any]:
    from reservations import selectors

    rows = selectors.filter_list(selectors.with_money(), params)
    money = _balances(role)
    columns = [
        _col("number", "N°"),
        _col("client", "Client"),
        _col("title", "Événement"),
        _col("kind", "Type"),
        _col("date", "Date", "date"),
        _col("status", "Statut"),
        _col("venue", "Lieu"),
    ]
    if money:
        columns += [
            _col("total", "Montant", "money"),
            _col("paid", "Payé", "money"),
            _col("balance", "Solde", "money"),
        ]
    return {
        "title": "Réservations",
        "columns": columns,
        "rows": [
            {
                "number": r.number,
                "client": r.client.name,
                "title": r.title,
                "kind": r.get_kind_display(),
                "date": _local_day(r.event_start),
                "status": r.get_status_display(),
                "venue": r.venue,
                "total": r.total,
                "paid": r.paid,  # type: ignore[attr-defined]
                "balance": r.balance,  # type: ignore[attr-defined]
            }
            for r in rows[:MAX_ROWS]
        ],
    }


def clients(params: Any, role: str | None) -> dict[str, Any]:
    from crm import selectors

    rows = selectors.with_metrics(selectors.active_clients())
    rows = rows.filter(is_archived=params.get("archived") == "true")
    if params.get("search"):
        rows = selectors.search(rows, params["search"])
    else:
        rows = rows.order_by("name")
    money = _balances(role)
    columns = [
        _col("name", "Client"),
        _col("company", "Entreprise"),
        _col("phone", "Téléphone"),
        _col("email", "Email"),
        _col("orders", "Commandes", "number"),
        _col("last", "Dernière commande", "date"),
    ]
    if money:
        columns += [
            _col("revenue", "Chiffre d’affaires", "money"),
            _col("due", "Solde dû", "money"),
        ]
    return {
        "title": "Clients",
        "columns": columns,
        "rows": [
            {
                "name": c.name,
                "company": c.company,
                "phone": c.phone,
                "email": c.email,
                "orders": c.order_count,  # type: ignore[attr-defined]
                "last": _local_day(c.last_order_at),  # type: ignore[attr-defined]
                "revenue": c.revenue,  # type: ignore[attr-defined]
                "due": c.balance_due,  # type: ignore[attr-defined]
            }
            for c in rows[:MAX_ROWS]
        ],
    }


def quotes(params: Any, role: str | None) -> dict[str, Any]:
    from quotes import selectors
    from quotes.models import Quote

    rows = Quote.objects.filter(is_template=False).select_related("client")
    if params.get("status") and params["status"] != "all":
        rows = rows.filter(status=params["status"])
    rows = (
        selectors.search(rows, params["search"])
        if params.get("search")
        else rows.order_by("-issue_date")
    )
    return {
        "title": "Devis",
        "columns": [
            _col("number", "N°"),
            _col("client", "Client"),
            _col("date", "Date", "date"),
            _col("status", "Statut"),
            _col("total", "Montant", "money"),
        ],
        "rows": [
            {
                "number": q.number,
                "client": q.client.name if q.client else "",
                "date": q.issue_date,
                "status": q.get_status_display(),
                "total": q.total,
            }
            for q in rows[:MAX_ROWS]
        ],
    }


def items(params: Any, role: str | None) -> dict[str, Any]:
    from stock import availability
    from stock.models import Item
    from stock.permissions import can_see_prices

    rows = list(
        Item.objects.filter(is_active=True).select_related("category").order_by("reference")
    )
    if params.get("category"):
        rows = [i for i in rows if str(i.category_id) == params["category"]]
    if params.get("search"):
        term = params["search"].lower()
        rows = [i for i in rows if term in i.name.lower() or term in i.reference.lower()]
    today = _today()
    free = availability.compute(rows, today, today, today)
    prices, costs = can_see_prices(role), _margins(role)
    columns = [
        _col("reference", "Réf."),
        _col("name", "Article"),
        _col("category", "Catégorie"),
        _col("owned", "Possédé", "number"),
        _col("available", "Disponible aujourd’hui", "number"),
        _col("threshold", "Seuil", "number"),
    ]
    if prices:
        columns.append(_col("rent", "Location", "money"))
    if costs:
        columns.append(_col("cost", "Coût d’achat", "money"))
    return {
        "title": "Stock & matériel",
        "subtitle": f"Disponibilité au {today:%d/%m/%Y}",
        "columns": columns,
        "rows": [
            {
                "reference": i.reference,
                "name": i.name,
                "category": i.category.name,
                "owned": i.total_quantity,
                "available": free[str(i.pk)].available,
                "threshold": i.alert_threshold,
                "rent": i.rent_price,
                "cost": i.purchase_cost,
            }
            for i in rows
        ],
    }


def movements(params: Any, role: str | None) -> dict[str, Any]:
    from stock.models import StockMovement

    rows = StockMovement.objects.select_related("item", "author").order_by("-occurred_at")
    if params.get("item"):
        rows = rows.filter(item_id=params["item"])
    if params.get("kind"):
        rows = rows.filter(kind=params["kind"])
    return {
        "title": "Mouvements de stock",
        "columns": [
            _col("date", "Date", "date"),
            _col("reference", "Réf."),
            _col("item", "Article"),
            _col("kind", "Mouvement"),
            _col("delta", "Quantité", "number"),
            _col("reason", "Motif"),
            _col("author", "Par"),
            _col("state", "État"),
        ],
        "rows": [
            {
                "date": _local_day(m.occurred_at),
                "reference": m.item.reference,
                "item": m.item.name,
                "kind": m.get_kind_display(),
                "delta": m.delta,
                "reason": m.reason,
                "author": m.author.full_name if m.author else "",
                "state": f"Annulé : {m.cancel_reason}" if m.cancelled_at else "",
            }
            for m in rows[:MAX_ROWS]
        ],
    }


def invoices(params: Any, role: str | None) -> dict[str, Any]:
    from finance import invoicing
    from finance.models import Invoice

    rows = list(Invoice.objects.select_related("client", "reservation")[:MAX_ROWS])
    states = invoicing.states(rows)
    labels = {
        "paid": "Payée",
        "partial": "Payée en partie",
        "issued": "Émise",
        "overdue": "En retard",
        "cancelled": "Annulée par avoir",
    }
    if params.get("status"):
        rows = [i for i in rows if states[str(i.pk)].status == params["status"]]
    return {
        "title": "Factures",
        "columns": [
            _col("number", "N°"),
            _col("kind", "Type"),
            _col("client", "Client"),
            _col("reservation", "Réservation"),
            _col("issued", "Émise le", "date"),
            _col("due", "Échéance", "date"),
            _col("net", "Montant", "money"),
            _col("paid", "Payé", "money"),
            _col("balance", "Reste", "money"),
            _col("status", "Statut"),
        ],
        "rows": [
            {
                "number": i.number,
                "kind": i.get_kind_display(),
                "client": i.client.name,
                "reservation": i.reservation.number,
                "issued": i.issued_at,
                "due": i.due_at,
                "net": states[str(i.pk)].net,
                "paid": states[str(i.pk)].paid,
                "balance": states[str(i.pk)].balance,
                "status": labels[states[str(i.pk)].status],
            }
            for i in rows
        ],
    }


def _period(params: Any) -> Any:
    from finance.periods import from_params

    return from_params(params, _today())


def revenues(params: Any, role: str | None) -> dict[str, Any]:
    from finance.models import Revenue

    period = _period(params)
    rows = Revenue.objects.filter(date__range=(period.start, period.end)).select_related("client")
    if params.get("category"):
        rows = rows.filter(category=params["category"])
    return {
        "title": "Recettes",
        "period": {"start": period.start, "end": period.end},
        "columns": [
            _col("date", "Date", "date"),
            _col("client", "Client"),
            _col("category", "Catégorie"),
            _col("label", "Libellé"),
            _col("amount", "Montant", "money"),
            _col("state", "État"),
        ],
        "rows": [
            {
                "date": r.date,
                "client": r.client.name if r.client else "",
                "category": r.get_category_display(),
                "label": r.label,
                "amount": r.amount,
                "state": "Annulée" if r.is_cancelled else "",
            }
            for r in rows[:MAX_ROWS]
        ],
    }


def expenses(params: Any, role: str | None) -> dict[str, Any]:
    from finance.models import Expense

    rows = Expense.objects.select_related("category", "reservation", "wedding").order_by("-date")
    return {
        "title": "Dépenses",
        "columns": [
            _col("date", "Date", "date"),
            _col("label", "Libellé"),
            _col("category", "Catégorie"),
            _col("for", "Rattachée à"),
            _col("supplier", "Fournisseur"),
            _col("amount", "Montant", "money"),
        ],
        "rows": [
            {
                "date": e.date,
                "label": e.label,
                "category": e.category.name if e.category else "",
                "for": (
                    e.reservation.number
                    if e.reservation
                    else (e.wedding.title if e.wedding else "")
                ),
                "supplier": e.supplier,
                "amount": e.amount,
            }
            for e in rows[:MAX_ROWS]
        ],
    }


def staff(params: Any, role: str | None) -> dict[str, Any]:
    from staff.models import StaffMember
    from staff.views import PAY

    rows = StaffMember.objects.filter(is_active=params.get("active") != "false", is_deleted=False)
    pay = role in PAY
    columns = [
        _col("name", "Nom"),
        _col("position", "Poste"),
        _col("kind", "Type"),
        _col("phone", "Téléphone"),
        _col("mobile", "Mobile Money"),
    ]
    if pay:
        columns += [_col("mode", "Rémunération"), _col("rate", "Taux", "money")]
    return {
        "title": "Personnel",
        "columns": columns,
        "rows": [
            {
                "name": s.full_name,
                "position": s.position,
                "kind": s.get_kind_display(),
                "phone": s.phone,
                "mobile": s.mobile_money,
                "mode": s.get_pay_mode_display(),
                "rate": s.pay_rate,
            }
            for s in rows
        ],
    }


def tasks(params: Any, role: str | None) -> dict[str, Any]:
    from staff.models import StaffTask

    rows = StaffTask.objects.select_related("staff", "reservation").exclude(
        reservation__status="cancelled"
    )
    if params.get("status") in StaffTask.Status.values:
        rows = rows.filter(status=params["status"])
    rows = rows.order_by("staff__full_name", "reservation__event_start")
    return {
        "title": "Tâches du personnel",
        "columns": [
            _col("person", "Personne"),
            _col("position", "Poste"),
            _col("reservation", "Réservation"),
            _col("date", "Date", "date"),
            _col("task", "Tâche"),
            _col("status", "Statut"),
            _col("comment", "Commentaire"),
        ],
        "rows": [
            {
                "person": t.staff.full_name,
                "position": t.staff.position,
                "reservation": f"{t.reservation.number} · {t.reservation.title}",
                "date": _local_day(t.reservation.event_start),
                "task": t.title,
                "status": t.get_status_display(),
                "comment": t.comment,
            }
            for t in rows[:MAX_ROWS]
        ],
    }


def pay(params: Any, role: str | None) -> dict[str, Any]:
    from staff.models import PayPeriod

    period = (
        PayPeriod.objects.filter(pk=params["period"]).first()
        if params.get("period")
        else PayPeriod.objects.order_by("-start").first()
    )
    if period is None:
        raise BusinessError("not_found", "Aucune période de paie.", status_code=404)
    return {
        "title": "Paie",
        "period": {"start": period.start, "end": period.end},
        "columns": [
            _col("name", "Personne"),
            _col("position", "Poste"),
            _col("days", "Jours", "number"),
            _col("missions", "Missions", "number"),
            _col("hours", "Heures", "number"),
            _col("base", "Base", "money"),
            _col("bonuses", "Primes", "money"),
            _col("advances", "Avances", "money"),
            _col("total", "Net", "money"),
            _col("paid", "Payé le", "date"),
        ],
        "rows": [
            {
                "name": line.staff.full_name,
                "position": line.staff.position,
                "days": line.days,
                "missions": line.missions,
                "hours": float(line.hours),
                "base": line.base,
                "bonuses": line.bonuses,
                "advances": line.advances,
                "total": line.total,
                "paid": line.paid_at,
            }
            for line in period.lines.select_related("staff")
        ],
        "totals": {"total": sum(line.total for line in period.lines.all())},
    }


def calendar(params: Any, role: str | None) -> dict[str, Any]:
    from events import calendar as feed

    try:
        start = date.fromisoformat(params.get("from") or "")
        end = date.fromisoformat(params.get("to") or "")
    except ValueError:
        start = _today()
        end = start + timedelta(days=30)
    if (end - start).days > feed.MAX_DAYS or end < start:
        raise BusinessError("invalid", "Deux mois au maximum.")
    kinds = [k for k in (params.get("kinds") or "").split(",") if k in feed.KINDS] or None
    statuses = [s for s in (params.get("statuses") or "").split(",") if s] or None
    labels = {
        "event": "Événement",
        "delivery": "Livraison",
        "setup": "Installation",
        "teardown": "Démontage",
        "pickup": "Récupération",
        "return": "Retour",
        "maintenance": "Maintenance",
        "payment": "Paiement attendu",
        "task": "Tâche",
    }
    rows = feed.build(
        start,
        end,
        member=params.get("member") or None,
        kinds=kinds,
        statuses=statuses,
        with_money=_balances(role),
        movable=False,
    )
    return {
        "title": "Calendrier",
        "period": {"start": start, "end": end},
        "columns": [
            _col("date", "Date", "date"),
            _col("time", "Heure"),
            _col("kind", "Type"),
            _col("title", "Client / titre"),
            _col("subtitle", "Détail"),
            _col("team", "Équipe"),
            _col("vehicle", "Véhicule"),
        ],
        "rows": [
            {
                **row,
                "kind": labels[row["kind"]],
                "team": ", ".join(row["team"]),
                "time": row["time"] or "",
            }
            for row in rows
        ],
    }


@dataclass(frozen=True)
class Export:
    build: Callable[[Any, str | None], dict[str, Any]]
    roles: Callable[[str | None], bool]
    name: str


def _in(*roles: str) -> Callable[[str | None], bool]:
    return lambda role: role in roles


def _registry() -> dict[str, Export]:
    from events.permissions import CALENDAR_ROLES
    from reservations.permissions import READ as RESERVATION_READ
    from staff.views import PAY
    from staff.views import READ as STAFF_READ
    from stock.permissions import READ as STOCK_READ

    return {
        "reservations": Export(reservations, _in(*RESERVATION_READ), "reservations"),
        "clients": Export(clients, _in(*SALES), "clients"),
        "quotes": Export(quotes, _in(*SALES), "devis"),
        "items": Export(items, _in(*STOCK_READ), "stock"),
        "movements": Export(movements, _in(*STOCK_READ), "mouvements"),
        "invoices": Export(invoices, _balances, "factures"),
        "revenues": Export(revenues, _balances, "recettes"),
        "expenses": Export(expenses, _margins, "depenses"),
        "staff": Export(staff, _in(*STAFF_READ), "personnel"),
        "pay": Export(pay, _in(*PAY), "paie"),
        "tasks": Export(tasks, _in(*STAFF_READ), "taches"),
        "calendar": Export(calendar, _in(*CALENDAR_ROLES), "calendrier"),
    }


def export(kind: str) -> Export:
    found = _registry().get(kind)
    if found is None:
        raise BusinessError("not_found", "Export inconnu.", status_code=404)
    return found
