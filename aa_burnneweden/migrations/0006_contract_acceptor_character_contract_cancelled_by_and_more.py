import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("aa_burnneweden", "0005_contract_discord_dm_sent_and_more"),
        ("eveonline", "0014_auto_20210105_1413"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="contract",
            name="acceptor_character",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="burner_contracts_accepted_char",
                to="eveonline.evecharacter",
            ),
        ),
        migrations.AddField(
            model_name="contract",
            name="cancelled_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="burner_contracts_cancelled",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="contract",
            name="date_cancelled",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
