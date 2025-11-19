import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'EduPro.settings')
django.setup()

from django.contrib.auth.models import User
from main.models import Course

# Get a valid instructor (your admin user)
instructor_user = User.objects.filter(is_superuser=True).first()

if instructor_user is None:
    print("❌ No superuser found! Create one using:")
    print("python manage.py createsuperuser")
    exit()

courses_list = [
    "Development",
    "Web Development",
    "Game Development",
    "Software Development",
    "Design",
    "Web Design",
    "Graphic Design",
    "Game Design",
    "Illustration",
    "Animation",
    "Marketing",
    "Digital Marketing",
    "Content Marketing",
    "Affiliate Marketing",
    "Product Marketing"
]

for course in courses_list:
    obj, created = Course.objects.get_or_create(
        title=course,
        defaults={
            "description": f"This is the {course} description.",
            "instructor": instructor_user,
            "duration": "10 Hours",
            "price": 0
        }
    )
    if created:
        print(f"✅ Added: {course}")
    else:
        print(f"⚠️ Already exists: {course}")

print("✨ Done!")
