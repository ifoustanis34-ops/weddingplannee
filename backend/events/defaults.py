"""Standard task list created with every space (complement §11). Editable data, not code."""

from __future__ import annotations

from core.tenant import require_current_organization

from .models import TaskTemplateItem

# (title, days before the wedding)
STANDARD_TASKS: list[tuple[str, int]] = [
    ("Rendez-vous de lancement", 180),
    ("Valider le budget global", 170),
    ("Réserver la salle", 160),
    ("Choisir le traiteur et organiser la dégustation", 120),
    ("Réserver photographe et vidéaste", 120),
    ("Réserver DJ ou orchestre", 100),
    ("Définir la décoration et la palette", 90),
    ("Envoyer les invitations", 60),
    ("Finaliser la liste des invités", 30),
    ("Établir le plan de table", 10),
    ("Briefing équipe jour J", 2),
    ("Répétition de la cérémonie", 1),
]


def ensure_standard_tasks() -> int:
    """Create the standard list in the active organization if it has none. Returns the count."""
    if TaskTemplateItem.objects.exists():
        return 0
    # bulk_create skips save(): the organization is set explicitly (RLS refuses it otherwise).
    organization = require_current_organization()
    TaskTemplateItem.objects.bulk_create(
        TaskTemplateItem(
            organization=organization, title=title, days_before=days, position=position
        )
        for position, (title, days) in enumerate(STANDARD_TASKS)
    )
    return len(STANDARD_TASKS)
