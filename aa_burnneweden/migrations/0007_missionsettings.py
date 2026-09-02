from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("aa_burnneweden", "0006_contract_acceptor_character_contract_cancelled_by_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="MissionSettings",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "price_per_mission",
                    models.DecimalField(
                        decimal_places=2,
                        default=25000000,
                        help_text="ISK charged per mission. Contract ISK value is floor-divided by this to derive mission count.",
                        max_digits=20,
                    ),
                ),
            ],
            options={
                "verbose_name": "Mission Settings",
                "verbose_name_plural": "Mission Settings",
                "default_permissions": (),
            },
        ),
    ]
