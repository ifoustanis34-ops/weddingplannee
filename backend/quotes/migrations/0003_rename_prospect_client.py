from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("crm", "0002_prospect_to_client"),
        ("quotes", "0002_document_fields_and_partners"),
    ]

    operations = [
        migrations.RemoveConstraint(model_name="quote", name="quote_has_client_unless_template"),
        migrations.RenameField(model_name="quote", old_name="prospect", new_name="client"),
        migrations.AddConstraint(
            model_name="quote",
            constraint=models.CheckConstraint(
                condition=models.Q(is_template=True) | models.Q(client__isnull=False),
                name="quote_has_client_unless_template",
            ),
        ),
    ]
