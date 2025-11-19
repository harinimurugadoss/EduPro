from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User

# Register your models here.

from .models import (
    library, Course, Enrollment, Profile, Country, State, District,
    CourseVideo, VideoProgress, TrainerRating, VideoRating,
    TrainerContact, Feedback, TrainerCourseAssignment, Payment
)


# ==================== PROFILE INLINE (Shows Profile in User Admin) ====================
class ProfileInline(admin.StackedInline):
    """Inline admin for Profile - shows in User admin page"""
    model = Profile
    can_delete = False
    verbose_name = 'User Role & Profile'
    verbose_name_plural = 'User Role & Profile'
    fieldsets = (
        ('Role Management', {
            'fields': ('is_instructor', 'is_trainer', 'is_student'),
            'description': '⚠️ IMPORTANT: Only check ONE role at a time!<br>'
                          '• Manager = is_instructor ✅<br>'
                          '• Trainer = is_trainer ✅<br>'
                          '• Student = is_student ✅ (default)'
        }),
        ('Location Information', {
            'fields': ('country', 'state', 'district'),
            'classes': ('collapse',)
        }),
    )


# ==================== CUSTOM USER ADMIN ====================
class UserAdmin(BaseUserAdmin):
    """Custom User Admin with Profile inline"""
    inlines = (ProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'get_user_role', 'is_staff', 'is_active')
    list_filter = ('is_staff', 'is_active', 'is_superuser')
    
    def get_user_role(self, obj):
        """Display user role in list view"""
        try:
            profile = obj.profile
            return profile.get_role()
        except Profile.DoesNotExist:
            return 'No Profile'
    get_user_role.short_description = 'Role'


# ==================== PROFILE ADMIN ====================
@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    """Custom Profile Admin with better interface"""
    list_display = ('user', 'get_role', 'is_instructor', 'is_trainer', 'is_student', 'country', 'state')
    list_filter = ('is_instructor', 'is_trainer', 'is_student', 'country')
    search_fields = ('user__username', 'user__email', 'user__first_name', 'user__last_name')
    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Role Management', {
            'fields': ('is_instructor', 'is_trainer', 'is_student'),
            'description': '⚠️ IMPORTANT: Only check ONE role at a time!<br>'
                          '<strong>Manager:</strong> Check is_instructor ✅, uncheck others<br>'
                          '<strong>Trainer:</strong> Check is_trainer ✅, uncheck others<br>'
                          '<strong>Student:</strong> Check is_student ✅, uncheck others'
        }),
        ('Location Information', {
            'fields': ('country', 'state', 'district'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ('user',)
    
    def get_role(self, obj):
        """Display role in list view"""
        return obj.get_role()
    get_role.short_description = 'Current Role'


# ==================== REGISTER MODELS ====================
# Unregister default User admin and register custom one
admin.site.unregister(User)
admin.site.register(User, UserAdmin)

# Register other models
admin.site.register(library)
admin.site.register(Course)
admin.site.register(Enrollment)
admin.site.register(Country)
admin.site.register(State)
admin.site.register(District)
admin.site.register(CourseVideo)
admin.site.register(VideoProgress)
admin.site.register(TrainerRating)
admin.site.register(VideoRating)
admin.site.register(TrainerContact)
admin.site.register(Feedback)
admin.site.register(TrainerCourseAssignment)
admin.site.register(Payment)