from django.apps import AppConfig


class AaBurnNewEdenConfig(AppConfig):
    name = "aa_burnneweden"
    verbose_name = "Burn New Eden"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        from . import signals  # noqa: F401 — connect signal handlers
        self._inject_esi_scope()

    @staticmethod
    def _inject_esi_scope():
        from django.conf import settings
        scope = "esi-contracts.read_corporation_contracts.v1"
        scopes = getattr(settings, "ESI_SSO_SCOPES", None)
        if isinstance(scopes, list) and scope not in scopes:
            scopes.append(scope)
