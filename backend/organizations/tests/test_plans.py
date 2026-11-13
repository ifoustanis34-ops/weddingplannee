from __future__ import annotations

from rest_framework.test import APIClient

from organizations.models import SubscriptionPlan


def test_plans_are_public_and_priced_from_the_database(db: None) -> None:
    response = APIClient().get("/api/v1/plans")

    assert response.status_code == 200
    plans = response.json()
    assert [plan["code"] for plan in plans] == ["essentiel", "pro", "agence"]
    assert [plan["monthly_price"] for plan in plans] == [15000, 35000, 75000]
    assert plans[2]["max_users"] is None


def test_a_price_change_in_the_database_is_served_as_is(db: None) -> None:
    SubscriptionPlan.objects.filter(code="pro").update(monthly_price=39000)
    SubscriptionPlan.objects.filter(code="agence").update(is_active=False)

    plans = APIClient().get("/api/v1/plans").json()

    assert [(plan["code"], plan["monthly_price"]) for plan in plans] == [
        ("essentiel", 15000),
        ("pro", 39000),
    ]
