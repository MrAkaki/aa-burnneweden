from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("aa_burnneweden", "0007_missionsettings"),
    ]

    operations = [
        migrations.AddField(
            model_name="discordnotificationpreference",
            name="notify_contract_canceled",
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name="discordnotificationpreference",
            name="notify_contract_started",
            field=models.BooleanField(
                default=False,
                help_text="Notify me when a contract I submitted is accepted and started by a runner.",
            ),
        ),
        migrations.AlterField(
            model_name="discordnotificationpreference",
            name="notify_contract_completed",
            field=models.BooleanField(
                default=False,
                help_text="Notify me when a contract I submitted is completed.",
            ),
        ),
    ]
