import pytest

from organizations.models import Organization
from organizations.services import check_slug, suggest_slug

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    ("slug", "available"),
    [
        ("maison-elegance", True),
        ("abc", True),
        ("ab", False),
        ("a" * 33, False),
        ("-agence", False),
        ("agence-", False),
        ("agence_mariage", False),
        ("support", False),
    ],
)
def test_slug_rules(slug: str, available: bool) -> None:
    assert check_slug(slug).available is available


def test_suggestion_strips_accents_and_avoids_taken_slugs() -> None:
    Organization.objects.create(slug="maison-elegance", name="X", city="Abidjan", country="CI")

    assert suggest_slug("Maison Élégance") == "maison-elegance-2"
    assert suggest_slug("AB") == "ab-events"
    assert suggest_slug("★") == "agence"
