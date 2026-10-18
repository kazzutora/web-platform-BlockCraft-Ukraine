import factory
from allauth.account.models import EmailAddress

from apps.accounts.models import User

PASSWORD = "Creeper-Aww-Man-2026"


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
        skip_postgeneration_save = True

    email = factory.Sequence(lambda n: f"player{n}@example.com")
    nickname = factory.Sequence(lambda n: f"player_{n}")
    password = factory.PostGenerationMethodCall("set_password", PASSWORD)

    @factory.post_generation
    def verified(self, create: bool, extracted: bool | None, **kwargs) -> None:
        """Users have a verified primary email unless `verified=False` is passed."""
        if create and extracted is not False:
            EmailAddress.objects.create(user=self, email=self.email, verified=True, primary=True)
        if create:
            self.save()
