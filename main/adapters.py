from allauth.account.adapter import DefaultAccountAdapter
from django.conf import settings
from .models import Profile


class CustomAccountAdapter(DefaultAccountAdapter):
    """
    Custom adapter to redirect users based on their role after login
    """
    def get_login_redirect_url(self, request):
        """
        Override to redirect based on user role
        """
        if request.user.is_authenticated:
            try:
                profile = Profile.objects.get(user=request.user)
                role = profile.get_role()
                
                if role == 'Manager':
                    return '/manager/dashboard/'
                elif role == 'Trainer':
                    return '/trainer/dashboard/'
                else:
                    return '/student/dashboard/'
            except Profile.DoesNotExist:
                # Create profile if it doesn't exist
                Profile.objects.create(user=request.user, is_student=True)
                return '/student/dashboard/'
        
        return super().get_login_redirect_url(request)

