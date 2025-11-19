from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from django.shortcuts import redirect
from .models import Profile


@receiver(user_logged_in)
def redirect_after_login(sender, request, user, **kwargs):
    """
    Signal handler to redirect users based on their role after login.
    This works with django-allauth login.
    """
    try:
        profile = Profile.objects.get(user=user)
        role = profile.get_role()
        
        if role == 'Manager':
            request.session['redirect_to'] = '/manager/dashboard/'
        elif role == 'Trainer':
            request.session['redirect_to'] = '/trainer/dashboard/'
        else:
            request.session['redirect_to'] = '/student/dashboard/'
    except Profile.DoesNotExist:
        # Create profile if it doesn't exist
        Profile.objects.create(user=user, is_student=True)
        request.session['redirect_to'] = '/student/dashboard/'

