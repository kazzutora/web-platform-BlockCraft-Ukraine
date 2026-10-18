from allauth.account.adapter import DefaultAccountAdapter

# Nicknames allow only [a-zA-Z0-9_]: generated names (social sign-up) drop everything else
NICKNAME_DISALLOWED = r"[^a-zA-Z0-9_]"


class AccountAdapter(DefaultAccountAdapter):
    def generate_unique_username(self, txts, regex=None):
        return super().generate_unique_username(txts, regex=regex or NICKNAME_DISALLOWED)
