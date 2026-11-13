from django.db import migrations

DEFAULTS = [
    ("Mobilier", 0),
    ("Linge de table", 1),
    ("Vaisselle", 1),
    ("Décoration", 0),
    ("Structures et tentes", 0),
    ("Éclairage", 0),
    ("Sonorisation", 0),
    ("Énergie", 0),
    ("Divers", 0),
]


def seed(apps, schema_editor):  # type: ignore[no-untyped-def]
    Organization = apps.get_model("organizations", "Organization")
    ItemCategory = apps.get_model("stock", "ItemCategory")
    schema_editor.execute("SET LOCAL app.bypass_rls = 'on'")
    for organization in Organization.objects.all():
        for position, (name, days) in enumerate(DEFAULTS):
            ItemCategory.objects.get_or_create(
                organization=organization,
                name=name,
                defaults={"cleaning_days": days, "position": position},
            )


class Migration(migrations.Migration):
    dependencies = [("stock", "0001_initial"), ("organizations", "0004_organization_alert_digest")]

    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
