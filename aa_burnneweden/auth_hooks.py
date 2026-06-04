from django.utils.translation import gettext_lazy as _

from allianceauth import hooks
from allianceauth.services.hooks import MenuItemHook, UrlHook

from . import urls

REQUIRED_SCOPES = ["esi-contracts.read_corporation_contracts.v1"]


class BurnNewEdenMenuItem(MenuItemHook):
    def __init__(self):
        super().__init__(
            _("Burn New Eden"),
            "fas fa-fire fa-fw",
            "aa_burnneweden:index",
            navactive=["aa_burnneweden:"],
        )

    def render(self, request):
        if request.user.has_perm("aa_burnneweden.basic_access"):
            return super().render(request)
        return ""


@hooks.register("menu_item_hook")
def register_menu():
    return BurnNewEdenMenuItem()


@hooks.register("url_hook")
def register_urls():
    return UrlHook(urls, "aa_burnneweden", r"^burnneweden/")
