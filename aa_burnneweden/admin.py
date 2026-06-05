from django.contrib import admin

from .models import Contract, ContractItem, OwnerCorporation
from .tasks import sync_contracts


class ContractItemInline(admin.TabularInline):
    model = ContractItem
    extra = 0
    readonly_fields = ("type_id", "type_name", "quantity", "is_included", "is_singleton")
    can_delete = False


@admin.register(OwnerCorporation)
class OwnerCorporationAdmin(admin.ModelAdmin):
    list_display = ("corporation", "character", "is_active", "last_updated")
    list_filter = ("is_active",)
    actions = ["trigger_sync"]

    @admin.action(description="Trigger ESI sync for all active corporations")
    def trigger_sync(self, request, queryset):
        sync_contracts.delay()
        self.message_user(request, "Queued full ESI sync for all active corporations.")


@admin.register(Contract)
class ContractAdmin(admin.ModelAdmin):
    list_display = (
        "contract_id",
        "owner_corporation",
        "issuer_character",
        "issuer_user",
        "esi_status",
        "accepted_by",
        "assigned_runner",
        "date_issued",
        "date_started",
        "date_completed",
        "date_cancelled",
        "date_rejected",
    )
    list_filter = ("esi_status", "owner_corporation")
    search_fields = ("contract_id", "title", "issuer_character__character_name")
    readonly_fields = (
        "contract_id",
        "owner_corporation",
        "issuer_character",
        "issuer_user",
        "acceptor_character",
        "esi_status",
        "date_issued",
        "date_expired",
        "date_started",
        "date_completed",
        "date_cancelled",
        "date_rejected",
        "accepted_by",
        "completed_by",
        "rejected_by",
        "cancelled_by",
        "price",
        "reward",
        "volume",
        "title",
    )
    fields = (
        "contract_id",
        "owner_corporation",
        "issuer_character",
        "issuer_user",
        "acceptor_character",
        "title",
        "price",
        "reward",
        "volume",
        "date_issued",
        "date_expired",
        "date_started",
        "date_completed",
        "date_cancelled",
        "date_rejected",
        "esi_status",
        "accepted_by",
        "completed_by",
        "rejected_by",
        "cancelled_by",
        "assigned_runner",
        "staff_notes",
    )
    inlines = [ContractItemInline]
