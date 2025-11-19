from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from .models import Profile


def role_required(*allowed_roles):
    """
    Decorator to restrict access based on user role.
    Usage: @role_required('Manager', 'Trainer')
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                messages.error(request, 'Please login to access this page.')
                return redirect('account_login')
            
            profile, created = Profile.objects.get_or_create(user=request.user)
            
            user_role = profile.get_role()
            
            if user_role not in allowed_roles:
                messages.error(request, f'Access denied. This page is only for {", ".join(allowed_roles)}.')
                # Redirect to appropriate dashboard
                if profile.is_instructor:
                    return redirect('manager_dashboard')
                elif profile.is_trainer:
                    return redirect('trainer_dashboard')
                else:
                    return redirect('student_dashboard')
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def manager_required(view_func):
    """Decorator to restrict access to Managers only"""
    return role_required('Manager')(view_func)


def trainer_required(view_func):
    """Decorator to restrict access to Trainers only"""
    return role_required('Trainer')(view_func)


def student_required(view_func):
    """Decorator to restrict access to Students only"""
    return role_required('Student')(view_func)

