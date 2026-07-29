from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Create default development users for common roles.'

    def handle(self, *args, **options):
        User = get_user_model()

        default_users = [
            {
                'username': 'admin',
                'email': 'admin@example.com',
                'password': 'Admin$2026!',
                'is_staff': True,
                'is_superuser': True,
            },
            {
                'username': 'staff',
                'email': 'staff@example.com',
                'password': 'Staff$2026!',
                'is_staff': True,
                'is_superuser': False,
            },
            {
                'username': 'customer',
                'email': 'customer@example.com',
                'password': 'Customer$2026!',
                'is_staff': False,
                'is_superuser': False,
            },
        ]

        for user_data in default_users:
            username = user_data['username']
            defaults = {
                'email': user_data['email'],
                'is_staff': user_data['is_staff'],
                'is_superuser': user_data['is_superuser'],
                'is_active': True,
            }
            user, created = User.objects.get_or_create(username=username, defaults=defaults)
            if created:
                user.set_password(user_data['password'])
                user.save()
                self.stdout.write(self.style.SUCCESS(
                    f"Created default user '{username}' with password '{user_data['password']}'"
                ))
            else:
                changed = False
                for flag in ('is_staff', 'is_superuser'):
                    if getattr(user, flag) != user_data[flag]:
                        setattr(user, flag, user_data[flag])
                        changed = True
                    if changed:
                        user.save()
                        self.stdout.write(self.style.WARNING(
                            f"Updated role flags for existing user '{username}'"
                        ))
                    else:
                        self.stdout.write(self.style.WARNING(
                            f"Default user '{username}' already exists. Password was not changed."
                        ))
