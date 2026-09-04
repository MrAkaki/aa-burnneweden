from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("aa_burnneweden", "0008_discordnotificationpreference_notify_contract_canceled"),
    ]

    operations = [
        migrations.AddField(
            model_name="contract",
            name="discord_stale_dm_sent",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="discordnotificationpreference",
            name="notify_contract_stale",
            field=models.BooleanField(
                default=False,
                help_text="Notify me when an open contract has been available for over 24 hours without being claimed.",
            ),
        ),
    ]
