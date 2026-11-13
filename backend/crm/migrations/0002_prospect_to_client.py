"""Prospection and reminders removed (docs/specs/reservations-stock.md §2).

Backed up before running (``backups/db-avant-S1-*.dump``). Order matters:
1. the reminders tables (they point to prospects, quotes and contracts) are dropped;
2. confirmed prospects stay active clients, the others are archived (never deleted);
3. pipeline fields and the interaction history go; ``Prospect`` becomes ``Client``.
"""

from django.db import migrations, models

DROP_REMINDERS = """
DROP TABLE IF EXISTS reminders_reminderjob CASCADE;
DROP TABLE IF EXISTS reminders_reminderrule CASCADE;
DELETE FROM auth_permission WHERE content_type_id IN
  (SELECT id FROM django_content_type WHERE app_label = 'reminders');
DELETE FROM django_content_type WHERE app_label = 'reminders';
DELETE FROM django_migrations WHERE app = 'reminders';
"""


def prospects_to_clients(apps, schema_editor):  # type: ignore[no-untyped-def]
    Prospect = apps.get_model("crm", "Prospect")
    # Data migration: every organization at once (RLS bypass, as the admin does).
    schema_editor.execute("SET LOCAL app.bypass_rls = 'on'")
    for prospect in Prospect._base_manager.all().iterator():
        prospect.is_archived = prospect.status != "won"
        prospect.notes = prospect.needs or ""
        prospect.save(update_fields=["is_archived", "notes"])


class Migration(migrations.Migration):
    atomic = True

    # Every migration that still points to ``crm.Prospect`` runs before the rename.
    dependencies = [
        ("crm", "0001_initial"),
        ("contracts", "0003_payment"),
        ("events", "0003_task_alert"),
        ("quotes", "0002_document_fields_and_partners"),
    ]

    operations = [
        migrations.RunSQL(DROP_REMINDERS, migrations.RunSQL.noop),
        migrations.RemoveConstraint(model_name="prospect", name="prospect_budget_positive"),
        migrations.RemoveIndex(model_name="prospect", name="crm_prospec_organiz_7bf81b_idx"),
        migrations.RemoveIndex(model_name="prospect", name="crm_prospec_organiz_d45371_idx"),
        migrations.AddField(
            model_name="prospect",
            name="company",
            field=models.CharField(blank=True, max_length=160),
        ),
        migrations.AddField(
            model_name="prospect",
            name="phone_alt",
            field=models.CharField(blank=True, max_length=32),
        ),
        migrations.AddField(
            model_name="prospect", name="address", field=models.TextField(blank=True)
        ),
        migrations.AddField(
            model_name="prospect", name="notes", field=models.TextField(blank=True)
        ),
        migrations.AddField(
            model_name="prospect", name="preferences", field=models.TextField(blank=True)
        ),
        migrations.AddField(
            model_name="prospect",
            name="is_archived",
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(prospects_to_clients, migrations.RunPython.noop),
        migrations.RemoveField(model_name="prospect", name="source"),
        migrations.RemoveField(model_name="prospect", name="status"),
        migrations.RemoveField(model_name="prospect", name="budget"),
        migrations.RemoveField(model_name="prospect", name="wedding_date"),
        migrations.RemoveField(model_name="prospect", name="guest_count"),
        migrations.RemoveField(model_name="prospect", name="needs"),
        migrations.RemoveField(model_name="prospect", name="lost_reason"),
        migrations.RemoveField(model_name="prospect", name="owner"),
        migrations.RemoveField(model_name="prospect", name="next_follow_up_at"),
        migrations.RemoveField(model_name="prospect", name="status_changed_at"),
        migrations.DeleteModel(name="Interaction"),
        migrations.RenameModel(old_name="Prospect", new_name="Client"),
        migrations.AlterModelOptions(
            name="client", options={"base_manager_name": "all_tenants", "ordering": ["name"]}
        ),
        migrations.RenameIndex(
            model_name="client",
            new_name="crm_client_phone_idx",
            old_name="crm_prospec_organiz_ca36eb_idx",
        ),
        migrations.RenameIndex(
            model_name="client",
            new_name="crm_client_email_idx",
            old_name="crm_prospec_organiz_429e2b_idx",
        ),
        migrations.RenameIndex(
            model_name="client", new_name="crm_client_name_trgm", old_name="crm_prospect_name_trgm"
        ),
    ]
