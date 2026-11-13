# « Mariages » module (feedback 13/11/2026): off by default; spaces that already have weddings
# keep it on so nothing they use disappears.

from django.db import migrations, models


def keep_for_existing_weddings(apps, schema_editor):  # type: ignore[no-untyped-def]
    Organization = apps.get_model("organizations", "Organization")
    with schema_editor.connection.cursor() as cursor:
        for organization in Organization.objects.all():
            # The wedding table is under row-level security: look inside each space.
            cursor.execute("SELECT set_config('app.current_org', %s, true)", [str(organization.pk)])
            cursor.execute(
                "SELECT EXISTS (SELECT 1 FROM events_wedding WHERE organization_id = %s)",
                [str(organization.pk)],
            )
            if cursor.fetchone()[0]:
                Organization.objects.filter(pk=organization.pk).update(weddings_enabled=True)
        # Back to « no space » for the rest of the migration.
        cursor.execute("RESET app.current_org")


class Migration(migrations.Migration):

    dependencies = [
        ("organizations", "0006_invoice_sequences"),
        ("events", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="organization",
            name="weddings_enabled",
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(keep_for_existing_weddings, migrations.RunPython.noop),
    ]
