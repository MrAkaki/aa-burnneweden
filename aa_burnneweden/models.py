from django.contrib.auth.models import User
from django.db import models
from django.utils.translation import gettext_lazy as _

from allianceauth.eveonline.models import EveCharacter, EveCorporationInfo

from .managers import ContractManager

DELETE_ESI_STATUSES = ("cancelled", "deleted", "reversed")
REJECT_ESI_STATUSES = ("rejected", "expired")


class OwnerCorporation(models.Model):
    corporation = models.OneToOneField(
        EveCorporationInfo,
        on_delete=models.CASCADE,
        related_name="burner_owner",
    )
    character = models.ForeignKey(
        EveCharacter,
        on_delete=models.SET_NULL,
        null=True,
        help_text="Character whose ESI token is used to pull contracts.",
    )
    is_active = models.BooleanField(default=True)
    last_updated = models.DateTimeField(null=True, blank=True)

    class Meta:
        default_permissions = ()
        verbose_name = "Owner Corporation"

    def __str__(self):
        return self.corporation.corporation_name


class Contract(models.Model):
    STATUSES = [
        ("open", _("Open")),
        ("running", _("Running")),
        ("completed", _("Completed")),
        ("cancelled", _("Cancelled")),
        ("rejected", _("Rejected")),
    ]

    owner_corporation = models.ForeignKey(
        OwnerCorporation,
        on_delete=models.CASCADE,
        related_name="contracts",
    )
    contract_id = models.IntegerField()
    issuer_character = models.ForeignKey(
        EveCharacter,
        on_delete=models.SET_NULL,
        null=True,
        related_name="burner_contracts_issued",
    )
    issuer_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="burner_contracts_issued",
    )
    title = models.CharField(max_length=255, blank=True)
    price = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    reward = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    volume = models.FloatField(default=0)
    date_issued = models.DateTimeField()
    date_expired = models.DateTimeField()
    date_started = models.DateTimeField(null=True, blank=True)
    date_completed = models.DateTimeField(null=True, blank=True)
    date_rejected = models.DateTimeField(null=True, blank=True)
    date_cancelled = models.DateTimeField(null=True, blank=True)
    esi_status = models.CharField(max_length=32)
    acceptor_character = models.ForeignKey(
        EveCharacter,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="burner_contracts_accepted_char",
    )
    accepted_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="burner_contracts_accepted",
    )
    assigned_runner = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="burner_contracts_assigned",
    )
    completed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="burner_contracts_completed",
    )
    rejected_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="burner_contracts_rejected",
    )
    cancelled_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="burner_contracts_cancelled",
    )
    staff_notes = models.TextField(blank=True)
    discord_dm_sent = models.BooleanField(default=False)

    objects = ContractManager()

    class Meta:
        unique_together = ("owner_corporation", "contract_id")
        default_permissions = ()
        permissions = (
            ("basic_access", "Can access the Burn New Eden app"),
            ("puller_access", "Puller: can view own submitted contracts"),
            ("runner_access", "Runner: can view and accept open contracts"),
            ("staff_access", "Staff: can manage all contracts"),
            ("admin_access", "Admin: full access including configuration"),
        )

    @property
    def status(self):
        if self.date_rejected:
            return "rejected"
        if self.date_completed:
            return "completed"
        if self.date_cancelled:
            return "cancelled"
        if self.date_started:
            return "running"
        return "open"

    @property
    def issuer_display(self):
        if self.issuer_character_id:
            return self.issuer_character.character_name
        if self.issuer_user_id:
            return self.issuer_user.username
        return "-"

    @property
    def contract_value(self):
        """Signed ISK value: positive = reward (runner earns), negative = price (runner pays)."""
        if self.reward:
            return self.reward
        if self.price:
            return -self.price
        return self.reward  # both zero, return 0

    @property
    def issuer_on_aa(self):
        """True when the issuer is a registered AA user."""
        return bool(self.issuer_user_id)

    @property
    def issuer_main_name(self):
        """Display name for the issuer: main char name if on AA, else EVE char name."""
        if self.issuer_user_id:
            try:
                main = self.issuer_user.profile.main_character
                if main:
                    return main.character_name
            except Exception:
                pass
            return self.issuer_user.username
        if self.issuer_character_id:
            return self.issuer_character.character_name
        return "-"

    @property
    def acceptor_display(self):
        """Character name or username for whoever accepted the contract."""
        if self.accepted_by_id:
            try:
                main = self.accepted_by.profile.main_character
                if main:
                    return main.character_name
            except Exception:
                pass
            return self.accepted_by.username
        if self.acceptor_character_id:
            return self.acceptor_character.character_name
        return "-"

    @property
    def runner_main_name(self):
        """Display name for the effective runner (assigned > accepted): main char name or username fallback."""
        user = self.assigned_runner or self.accepted_by
        if user:
            try:
                main = user.profile.main_character
                if main:
                    return main.character_name
            except Exception:
                pass
            return user.username
        if self.acceptor_character_id:
            return self.acceptor_character.character_name
        return "-"

    def __str__(self):
        return f"Contract #{self.contract_id} ({self.status})"


class DiscordNotificationPreference(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="burner_discord_prefs",
    )

    # Runner opt-ins
    notify_contract_created = models.BooleanField(default=False)
    notify_contract_started = models.BooleanField(default=False)
    notify_contract_rejected = models.BooleanField(default=False)
    notify_contract_completed = models.BooleanField(default=False)

    # Puller opt-in
    notify_new_open_contracts = models.BooleanField(default=False)

    class Meta:
        default_permissions = ()
        verbose_name = "Discord Notification Preference"

    def __str__(self):
        return f"Discord prefs for {self.user}"


class ContractItem(models.Model):
    contract = models.ForeignKey(
        Contract,
        on_delete=models.CASCADE,
        related_name="items",
    )
    type_id = models.IntegerField()
    type_name = models.CharField(max_length=255, blank=True)
    quantity = models.IntegerField()
    is_included = models.BooleanField(
        default=True,
        help_text="True = item is in the contract; False = item is requested.",
    )
    is_singleton = models.BooleanField(default=False)

    class Meta:
        default_permissions = ()

    def __str__(self):
        direction = "included" if self.is_included else "wanted"
        return f"{self.quantity}x {self.type_name or self.type_id} ({direction})"
