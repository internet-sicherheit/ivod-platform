from django.core.management.base import BaseCommand, CommandError
from ...models import User
from django.db.models import Q
from datetime import timedelta, time, datetime
from django.conf import settings

class Command(BaseCommand):
    help = "Cleanup stale and unused entries in the database"

    def handle(self, *args, **options):

        user_unverified_timeout = datetime.now() - settings.TOKEN_MAX_LIFETIME + timedelta(minutes=5)
        users_to_delete = User.objects.filter(Q(is_verified=False) & Q(creation_time__lte=user_unverified_timeout))
        for user in users_to_delete:
            print(f"Deleting user {user}")
            user.delete()
        print("All stale users deleted")