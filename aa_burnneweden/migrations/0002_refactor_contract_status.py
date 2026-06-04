import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("aa_burnneweden", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Remove the boolean flag — status is now derived from date fields
        migrations.RemoveField(
            model_name="contract",
            name="staff_override",
        ),
        # Remove the stored status — now a @property on the model
        migrations.RemoveField(
            model_name="contract",
            name="internal_status",
        ),
        # Rename date_accepted → date_started (runner accepted in-game)
        migrations.RenameField(
            model_name="contract",
            old_name="date_accepted",
            new_name="date_started",
        ),
        # Add date field for web-side rejection
        migrations.AddField(
            model_name="contract",
            name="date_rejected",
            field=models.DateTimeField(blank=True, null=True),
        ),
        # Who completed it (audit only, not displayed)
        migrations.AddField(
            model_name="contract",
            name="completed_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="burner_contracts_completed",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        # Who rejected it (audit only, not displayed)
        migrations.AddField(
            model_name="contract",
            name="rejected_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="burner_contracts_rejected",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
