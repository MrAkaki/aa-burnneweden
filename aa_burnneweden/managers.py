from django.db import models

CANCELLED_ESI_STATUSES = ("cancelled", "deleted", "reversed")


class ContractQuerySet(models.QuerySet):
    def open(self):
        return self.filter(
            date_started__isnull=True,
            date_completed__isnull=True,
            date_rejected__isnull=True,
        ).exclude(esi_status__in=CANCELLED_ESI_STATUSES)

    def accepted(self):
        return self.filter(
            date_started__isnull=False,
            date_completed__isnull=True,
            date_rejected__isnull=True,
        ).exclude(esi_status__in=CANCELLED_ESI_STATUSES)

    def completed(self):
        return self.filter(date_completed__isnull=False)

    def rejected(self):
        return self.filter(date_rejected__isnull=False)

    def cancelled(self):
        return self.filter(
            esi_status__in=CANCELLED_ESI_STATUSES,
            date_completed__isnull=True,
            date_rejected__isnull=True,
        )

    def active(self):
        return self.filter(
            date_completed__isnull=True,
            date_rejected__isnull=True,
        ).exclude(esi_status__in=CANCELLED_ESI_STATUSES)

    def for_puller(self, user):
        return self.filter(issuer_user=user)

    def for_runner(self, user):
        open_q = (
            models.Q(date_started__isnull=True)
            & models.Q(date_completed__isnull=True)
            & models.Q(date_rejected__isnull=True)
            & ~models.Q(esi_status__in=CANCELLED_ESI_STATUSES)
        )
        return self.filter(open_q | models.Q(accepted_by=user) | models.Q(assigned_runner=user))

    def with_status(self, status_value):
        if status_value == "open":
            return self.open()
        if status_value == "accepted":
            return self.accepted()
        if status_value == "completed":
            return self.completed()
        if status_value == "rejected":
            return self.rejected()
        if status_value == "cancelled":
            return self.cancelled()
        return self


class ContractManager(models.Manager):
    def get_queryset(self):
        return ContractQuerySet(self.model, using=self._db)

    def open(self):
        return self.get_queryset().open()

    def accepted(self):
        return self.get_queryset().accepted()

    def for_puller(self, user):
        return self.get_queryset().for_puller(user)

    def for_runner(self, user):
        return self.get_queryset().for_runner(user)

    def active(self):
        return self.get_queryset().active()
