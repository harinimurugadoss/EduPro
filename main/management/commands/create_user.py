"""
Management command to create users with specific roles
Usage: python manage.py create_user --username manager1 --email manager@example.com --role manager
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from main.models import Profile


class Command(BaseCommand):
    help = 'Create a user with a specific role (manager, trainer, or student)'

    def add_arguments(self, parser):
        parser.add_argument('--username', type=str, required=True, help='Username for the user')
        parser.add_argument('--email', type=str, required=True, help='Email for the user')
        parser.add_argument('--password', type=str, default='password123', help='Password for the user (default: password123)')
        parser.add_argument('--role', type=str, choices=['manager', 'trainer', 'student'], required=True, 
                          help='Role: manager, trainer, or student')
        parser.add_argument('--first-name', type=str, default='', help='First name')
        parser.add_argument('--last-name', type=str, default='', help='Last name')

    def handle(self, *args, **options):
        username = options['username']
        email = options['email']
        password = options['password']
        role = options['role'].lower()
        first_name = options['first_name']
        last_name = options['last_name']

        # Check if user already exists
        if User.objects.filter(username=username).exists():
            self.stdout.write(self.style.ERROR(f'User "{username}" already exists!'))
            return

        if User.objects.filter(email=email).exists():
            self.stdout.write(self.style.ERROR(f'Email "{email}" is already in use!'))
            return

        # Create user
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )

        # Set role in profile
        profile, created = Profile.objects.get_or_create(user=user)
        
        if role == 'manager':
            profile.is_instructor = True
            profile.is_trainer = False
            profile.is_student = False
            role_name = 'Manager'
        elif role == 'trainer':
            profile.is_trainer = True
            profile.is_instructor = False
            profile.is_student = False
            role_name = 'Trainer'
        else:  # student
            profile.is_student = True
            profile.is_instructor = False
            profile.is_trainer = False
            role_name = 'Student'

        profile.save()

        self.stdout.write(self.style.SUCCESS(
            f'Successfully created {role_name} user: {username}\n'
            f'  Email: {email}\n'
            f'  Password: {password}\n'
            f'  Dashboard: /{role}/dashboard/'
        ))

