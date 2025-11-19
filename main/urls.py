from django.urls import path
from django.shortcuts import redirect
from main import views

urlpatterns = [
    # Public pages
    path('', views.index, name='home'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    path('courses/', views.courses, name='courses'),
    path('courses/<str:category>/', views.category, name='category'),
    
    # Legacy dashboard (redirects to role-specific)
    path('dashboard/home/', views.dashboard_home, name='dashboard-home'),
    path('dashboard/profile/', views.profile, name='profile'),
    path('dashboard/courses-enrolled/', views.courses_enrolled, name='courses-enrolled'),
    path('dashboard/courses-uploaded/', views.courses_uploaded, name='courses-uploaded'),
    path('dashboard/upload/', views.upload, name='uploade'),
    path('dashboard/<slug:slug>/course-edit/', views.course_edit, name='course-edit'),
    path('dashboard/<slug:slug>/delete/', views.delete_course, name='delete-course'),
    
    # Student Dashboard & Views (MUST come before generic course_details pattern)
    path('student/dashboard/', views.student_dashboard, name='student_dashboard'),
    path('student/course/<int:course_id>/', views.student_course_detail, name='student_course_detail'),
    path('student/video/<int:video_id>/progress/', views.update_video_progress, name='update_video_progress'),
    path('student/course/<int:course_id>/payment/', views.payment_page, name='payment_page'),
    path('student/trainer/<int:trainer_id>/rate/', views.rate_trainer, name='rate_trainer'),
    path('student/video/<int:video_id>/rate/', views.rate_video, name='rate_video'),
    path('student/trainer/<int:trainer_id>/contact/', views.trainer_contact, name='trainer_contact'),
    path('student/course/<int:course_id>/feedback/', views.submit_feedback, name='submit_feedback'),
    
    # Trainer Dashboard & Views (MUST come before generic course_details pattern)
    path('trainer/dashboard/', views.trainer_dashboard, name='trainer_dashboard'),
    path('trainer/course/<int:course_id>/students/', views.trainer_course_students, name='trainer_course_students'),
    path('trainer/course/<int:course_id>/upload-video/', views.trainer_upload_video, name='trainer_upload_video'),
    path('trainer/contact/edit/', views.trainer_edit_contact, name='trainer_edit_contact'),
    path('trainer/contact/delete/', views.trainer_delete_contact, name='trainer_delete_contact'),
    
    # Manager Dashboard & Views (MUST come before generic course_details pattern)
    path('manager/dashboard/', views.manager_dashboard, name='manager_dashboard'),
    path('manager/add-course/', views.manager_add_course, name='manager_add_course'),
    path('manager/course/<int:course_id>/edit/', views.manager_edit_course, name='manager_edit_course'),
    path('manager/course/<int:course_id>/delete/', views.manager_delete_course, name='manager_delete_course'),
    path('manager/course/<int:course_id>/videos/', views.manager_manage_course_videos, name='manager_manage_course_videos'),
    path('manager/course/<int:course_id>/add-video/', views.manager_add_video_to_course, name='manager_add_video_to_course'),
    path('manager/video/<int:video_id>/edit/', views.manager_edit_video, name='manager_edit_video'),
    path('manager/video/<int:video_id>/delete/', views.manager_delete_video, name='manager_delete_video'),
    path('manager/add-trainer/', views.manager_add_trainer, name='manager_add_trainer'),
    path('manager/trainer/<int:trainer_id>/edit/', views.manager_edit_trainer, name='manager_edit_trainer'),
    path('manager/trainer/<int:trainer_id>/delete/', views.manager_delete_trainer, name='manager_delete_trainer'),
    path('manager/trainer/<int:trainer_id>/contact/edit/', views.manager_edit_trainer_contact, name='manager_edit_trainer_contact'),
    path('manager/trainer/<int:trainer_id>/contact/delete/', views.manager_delete_trainer_contact, name='manager_delete_trainer_contact'),
    path('manager/trainer/<int:trainer_id>/assignments/', views.manager_manage_trainer_assignments, name='manager_manage_trainer_assignments'),
    path('manager/assign-trainer/', views.manager_assign_trainer, name='manager_assign_trainer'),
    path('manager/assignment/<int:assignment_id>/unassign/', views.manager_unassign_trainer, name='manager_unassign_trainer'),
    path('manager/view-feedback/', views.manager_view_feedback, name='manager_view_feedback'),
    path('manager/analyze-progress/', views.manager_analyze_progress, name='manager_analyze_progress'),
    path('manager/view-payments/', views.manager_view_payments, name='manager_view_payments'),
    path('manager/payment/<int:payment_id>/update/', views.manager_update_payment, name='manager_update_payment'),
    
    # AJAX endpoints for dependent dropdowns
    path('ajax/states/<int:country_id>/', views.get_states, name='get_states'),
    path('ajax/districts/<int:state_id>/', views.get_districts, name='get_districts'),
    
    # Profile completion
    path('complete-profile/', views.complete_profile, name='complete_profile'),
    
    # Generic course details (MUST come last to avoid conflicts)
    path('<str:instructor>/course/<slug:slug>/', views.course_details, name='course_details'),
    
    # Redirects
    path('signup/', lambda request: redirect('/accounts/signup/'), name='signup'),
]
