from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("crm", "0002_prospect_to_client"),
        ("events", "0003_task_alert"),
    ]

    operations = [
        migrations.RenameField(model_name="wedding", old_name="prospect", new_name="client"),
    ]
