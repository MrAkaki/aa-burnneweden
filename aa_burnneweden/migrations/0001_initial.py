import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("eveonline", "0014_auto_20210105_1413"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="OwnerCorporation",
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
                ("is_active", models.BooleanField(default=True)),
                ("last_updated", models.DateTimeField(blank=True, null=True)),
                (
                    "character",
                    models.ForeignKey(
                        help_text="Character whose ESI token is used to pull contracts.",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="eveonline.evecharacter",
                    ),
                ),
                (
                    "corporation",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="burner_owner",
                        to="eveonline.evecorporationinfo",
                    ),
                ),
            ],
            options={
                "verbose_name": "Owner Corporation",
                "default_permissions": (),
            },
        ),
        migrations.CreateModel(
            name="Contract",
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
                ("contract_id", models.IntegerField()),
                ("title", models.CharField(blank=True, max_length=255)),
                (
                    "price",
                    models.DecimalField(decimal_places=2, default=0, max_digits=20),
                ),
                (
                    "reward",
                    models.DecimalField(decimal_places=2, default=0, max_digits=20),
                ),
                ("volume", models.FloatField(default=0)),
                ("date_issued", models.DateTimeField()),
                ("date_expired", models.DateTimeField()),
                ("date_accepted", models.DateTimeField(blank=True, null=True)),
                ("date_completed", models.DateTimeField(blank=True, null=True)),
                ("esi_status", models.CharField(max_length=32)),
                (
                    "internal_status",
                    models.CharField(
                        choices=[
                            ("open", "Open"),
                            ("accepted", "Accepted"),
                            ("completed", "Completed"),
                            ("cancelled", "Cancelled"),
                            ("rejected", "Rejected"),
                        ],
                        default="open",
                        max_length=16,
                    ),
                ),
                (
                    "staff_override",
                    models.BooleanField(
                        default=False,
                        help_text="When True, ESI sync will not overwrite internal_status.",
                    ),
                ),
                ("staff_notes", models.TextField(blank=True)),
                (
                    "accepted_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="burner_contracts_accepted",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "assigned_runner",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="burner_contracts_assigned",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "issuer_character",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="burner_contracts_issued",
                        to="eveonline.evecharacter",
                    ),
                ),
                (
                    "issuer_user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="burner_contracts_issued",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "owner_corporation",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="contracts",
                        to="aa_burnneweden.ownercorporation",
                    ),
                ),
            ],
            options={
                "default_permissions": (),
                "permissions": (
                    ("basic_access", "Can access the Burners app"),
                    ("puller_access", "Puller: can view own submitted contracts"),
                    ("runner_access", "Runner: can view and accept open contracts"),
                    ("staff_access", "Staff: can manage all contracts"),
                    ("admin_access", "Admin: full access including configuration"),
                ),
            },
        ),
        migrations.AddConstraint(
            model_name="contract",
            constraint=models.UniqueConstraint(
                fields=("owner_corporation", "contract_id"),
                name="unique_contract_per_corp",
            ),
        ),
        migrations.CreateModel(
            name="ContractItem",
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
                ("type_id", models.IntegerField()),
                ("type_name", models.CharField(blank=True, max_length=255)),
                ("quantity", models.IntegerField()),
                (
                    "is_included",
                    models.BooleanField(
                        default=True,
                        help_text="True = item is in the contract; False = item is requested.",
                    ),
                ),
                ("is_singleton", models.BooleanField(default=False)),
                (
                    "contract",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="items",
                        to="aa_burnneweden.contract",
                    ),
                ),
            ],
            options={
                "default_permissions": (),
            },
        ),
    ]
