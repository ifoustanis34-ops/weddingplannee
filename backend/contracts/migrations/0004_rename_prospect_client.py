from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("crm", "0002_prospect_to_client"),
        ("contracts", "0003_payment"),
    ]

    operations = [
        migrations.RenameField(model_name="contract", old_name="prospect", new_name="client"),
    ]
