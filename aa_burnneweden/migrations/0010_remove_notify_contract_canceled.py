from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("aa_burnneweden", "0009_contract_stale_notifications"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="discordnotificationpreference",
            name="notify_contract_canceled",
        ),
    ]
