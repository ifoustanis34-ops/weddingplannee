"""Who hears about what (feedback 17/11/2026: « tout le flux doit notifier », like WhatsApp).

The business services call these helpers once their change is made; each writes the inbox rows
(unread count, app icon badge) and sends the push after the commit. The person who acted is
never notified of their own action. Never an amount to roles that do not see money.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from . import push

MANAGERS = ("owner", "planner")


def _people(roles: Iterable[str], *, actor: Any, also: Iterable[Any] = ()) -> list[str]:
    users = set(push.members_with_roles(roles, exclude=getattr(actor, "pk", actor)))
    actor_id = str(getattr(actor, "pk", actor) or "")
    users |= {str(u) for u in also if u and str(u) != actor_id}
    return sorted(users)


def reservation(
    reservation: Any,
    *,
    title: str,
    body: str = "",
    actor: Any,
    roles: Iterable[str] = MANAGERS,
) -> None:
    """A step of a reservation: the managers (and its responsible person) hear about it."""
    who = f"{reservation.number} · {reservation.title}"
    push.notify(
        _people(roles, actor=actor, also=[reservation.owner_id]),
        title=title,
        body=f"{who}{' — ' + body if body else ''}",
        url=f"/reservations?reservation={reservation.pk}",
        kind="reservation",
        tag=f"reservation-{reservation.pk}",
    )


def attendance(assignment: Any, *, title: str, actor: Any) -> None:
    """A late arrival or an absence: the owner and the planners can react at once."""
    push.notify(
        _people(MANAGERS, actor=actor),
        title=title,
        body=f"{assignment.staff.full_name} · {assignment.reservation.title}",
        url="/presences",
        kind="attendance",
        tag=f"attendance-{assignment.pk}",
    )


def to_person(user_id: Any, *, title: str, body: str, url: str, kind: str, tag: str) -> None:
    """A message for one person (their task validated, their day paid…)."""
    if user_id:
        push.notify([user_id], title=title, body=body, url=url, kind=kind, tag=tag)


def quote_answer(quote: Any, *, accepted: bool) -> None:
    """The client answered the proposal online: the managers hear it right away."""
    client = getattr(getattr(quote, "client", None), "name", "") or ""
    push.notify(
        _people(MANAGERS, actor=None),
        title="Devis accepté par le client" if accepted else "Devis refusé par le client",
        body=f"{quote.number}{' · ' + client if client else ''}",
        url=f"/devis/{quote.pk}",
        kind="quote",
        tag=f"quote-{quote.pk}",
    )
