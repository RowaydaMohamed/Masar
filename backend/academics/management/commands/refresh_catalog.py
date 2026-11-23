from django.core.management.base import BaseCommand
from django.db import transaction

from .seed_data import Command as SeedDataCommand


class Command(BaseCommand):
    help = "Safely refresh the academic catalog only."

    @transaction.atomic
    def handle(self, *args, **options):
        seeder = SeedDataCommand()
        seeder.seed_catalog()

        self.stdout.write(
            self.style.SUCCESS("Catalog refreshed successfully.")
        )