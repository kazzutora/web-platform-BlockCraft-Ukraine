import factory

from apps.accounts.tests.factories import UserFactory
from apps.library.models import Collection


class CollectionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Collection

    owner = factory.SubFactory(UserFactory)
    title = factory.Sequence(lambda n: f"Колекція {n}")
    visibility = Collection.Visibility.PUBLIC
