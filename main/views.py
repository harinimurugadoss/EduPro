import json
import time
from django.utils import timezone

from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from django.utils.text import slugify
from .models import (
    Course, Enrollment, Profile, Country, State, District,
    CourseVideo, VideoProgress, TrainerRating, VideoRating,
    TrainerContact, Feedback, TrainerCourseAssignment, Payment
)
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count, Q
from django.views.decorators.http import require_http_methods
from .forms import CourseEditForm
from .decorators import manager_required, trainer_required, student_required, role_required
from django.contrib import messages
import pytz

# Create your views here.


def index(request):
    courses = Course.objects.all()[:6]
    return render(request, 'index.html', {'courses': courses})


def about(request):
    return render(request, 'about.html')


def contact(request):
    return render(request, 'contact.html')


def courses(request):
    courses = Course.objects.all()
    return render(request, 'courses.html', {'courses': courses})

# def profile(request):
#     user = request.user
#     if user.is_authenticated:
#         # get first and last name
#         first_name = user.first_name
#         last_name = user.last_name

#         # get username and email
#         username = user.username
#         email = user.email

#         # get profile picture
#         profile_picture = None
#         if hasattr(user, 'profile'):
#             profile_picture = user.profile.picture

#         return render(request, 'account/dashboard/profile.html', {'first_name': first_name, 'last_name': last_name, 'username': username, 'email': email, 'profile_picture': profile_picture})
#     else:
#         return redirect('account_login')

def dashboard_home(request):
    """Legacy dashboard - redirects to role-specific dashboards"""
    user = request.user
    if not user.is_authenticated:
        return redirect('account_login')
    
    profile, created = Profile.objects.get_or_create(user=user)
    role = profile.get_role()
    
    if role == 'Manager':
        return redirect('manager_dashboard')
    elif role == 'Trainer':
        return redirect('trainer_dashboard')
    else:
        return redirect('student_dashboard')


# ==================== STUDENT DASHBOARD & VIEWS ====================

@login_required
@student_required
def student_dashboard(request):
    """Student Dashboard"""
    user = request.user
    enrolled_courses = Enrollment.objects.filter(student=user)
    
    # Calculate progress for each course
    course_progress = []
    for enrollment in enrolled_courses:
        course = enrollment.course
        videos = CourseVideo.objects.filter(course=course)
        total_videos = videos.count()
        if total_videos > 0:
            completed_videos = VideoProgress.objects.filter(
                student=user, video__course=course, completed=True
            ).count()
            progress_percentage = (completed_videos / total_videos) * 100
        else:
            progress_percentage = 0
        
        course_progress.append({
            'course': course,
            'enrollment': enrollment,
            'progress': progress_percentage,
            'total_videos': total_videos,
            'completed_videos': completed_videos if total_videos > 0 else 0
        })
    
    context = {
        "user": user,
        "course_progress": course_progress,
    }
    return render(request, "dashboard/student_dashboard.html", context)


@login_required
@student_required
def student_course_detail(request, course_id):
    """Student view of course with videos and progress"""
    user = request.user
    course = get_object_or_404(Course, id=course_id)
    
    # Check if student is enrolled
    if not course.students.filter(id=user.id).exists():
        messages.error(request, 'You are not enrolled in this course.')
        return redirect('student_dashboard')
    
    videos = CourseVideo.objects.filter(course=course).order_by('order', 'created_at')
    
    # Get progress for each video
    video_progress_list = []
    for video in videos:
        progress, created = VideoProgress.objects.get_or_create(
            student=user, video=video
        )
        video_progress_list.append({
            'video': video,
            'progress': progress
        })
    
    # Calculate overall course progress
    total_videos = videos.count()
    if total_videos > 0:
        completed = VideoProgress.objects.filter(
            student=user, video__course=course, completed=True
        ).count()
        overall_progress = (completed / total_videos) * 100
    else:
        overall_progress = 0
    
    context = {
        'course': course,
        'video_progress_list': video_progress_list,
        'overall_progress': overall_progress,
    }
    return render(request, 'dashboard/student_course_detail.html', context)


@login_required
@student_required
@require_http_methods(["POST"])
def update_video_progress(request, video_id):
    """Update video progress (AJAX)"""
    user = request.user
    video = get_object_or_404(CourseVideo, id=video_id)
    
    # Check if student is enrolled in the course
    if not video.course.students.filter(id=user.id).exists():
        return JsonResponse({'error': 'Not enrolled'}, status=403)
    
    progress_percentage = int(request.POST.get('progress', 0))
    completed = request.POST.get('completed', 'false') == 'true'
    time_spent = int(request.POST.get('time_spent', 0))  # Time in seconds
    
    progress, created = VideoProgress.objects.get_or_create(
        student=user, video=video
    )
    progress.progress_percentage = min(100, max(0, progress_percentage))
    progress.completed = completed
    progress.time_spent_seconds = max(progress.time_spent_seconds, time_spent)  # Update if new time is greater
    progress.save()
    
    return JsonResponse({
        'success': True,
        'progress': progress.progress_percentage,
        'completed': progress.completed,
        'time_spent': progress.time_spent_seconds
    })


@login_required
@student_required
def payment_page(request, course_id):
    """Payment request page - student requests to purchase course"""
    course = get_object_or_404(Course, id=course_id)
    user = request.user
    
    # Check if already enrolled
    if course.students.filter(id=user.id).exists():
        messages.info(request, 'You are already enrolled in this course.')
        return redirect('student_course_detail', course_id=course.id)
    
    # Check if payment request already exists
    existing_payment = Payment.objects.filter(student=user, course=course, status='requested').first()
    if existing_payment:
        messages.info(request, 'You have already requested to purchase this course. Please wait for manager approval.')
        return redirect('student_dashboard')
    
    if request.method == 'POST':
        # Create payment request (not approved yet)
        payment_method = request.POST.get('payment_method', 'card')
        transaction_id = request.POST.get('transaction_id', '')
        notes = request.POST.get('notes', '')
        
        payment = Payment.objects.create(
            student=user,
            course=course,
            amount=course.price,
            payment_method=payment_method,
            transaction_id=transaction_id if transaction_id else None,
            status='requested',  # Request pending manager approval
            notes=notes
        )
        
        messages.success(request, 'Payment request submitted! The manager will review and approve your request. You will be notified once approved.')
        return redirect('student_dashboard')
    
    context = {'course': course}
    return render(request, 'dashboard/payment.html', context)


@login_required
@student_required
def rate_trainer(request, trainer_id):
    """Rate a trainer"""
    trainer = get_object_or_404(User, id=trainer_id)
    profile = get_object_or_404(Profile, user=trainer)
    student = request.user
    
    # Check if user is a trainer OR is a course instructor for a course the student is enrolled in
    is_trainer = profile.is_trainer
    is_course_instructor = Course.objects.filter(
        instructor=trainer,
        students=student
    ).exists()
    
    if not is_trainer and not is_course_instructor:
        messages.error(request, 'You can only rate trainers or course instructors.')
        return redirect('student_dashboard')
    
    if request.method == 'POST':
        rating = int(request.POST.get('rating'))
        comment = request.POST.get('comment', '')
        
        TrainerRating.objects.update_or_create(
            trainer=trainer,
            student=request.user,
            defaults={'rating': rating, 'comment': comment}
        )
        messages.success(request, 'Thank you for your rating!')
        return redirect('trainer_contact', trainer_id=trainer_id)
    
    existing_rating = TrainerRating.objects.filter(
        trainer=trainer, student=request.user
    ).first()
    
    context = {'trainer': trainer, 'existing_rating': existing_rating}
    return render(request, 'dashboard/rate_trainer.html', context)


@login_required
@student_required
def rate_video(request, video_id):
    """Rate a video"""
    video = get_object_or_404(CourseVideo, id=video_id)
    
    if request.method == 'POST':
        rating = int(request.POST.get('rating'))
        comment = request.POST.get('comment', '')
        
        VideoRating.objects.update_or_create(
            video=video,
            student=request.user,
            defaults={'rating': rating, 'comment': comment}
        )
        messages.success(request, 'Thank you for your rating!')
        return redirect('student_course_detail', course_id=video.course.id)
    
    existing_rating = VideoRating.objects.filter(
        video=video, student=request.user
    ).first()
    
    context = {'video': video, 'existing_rating': existing_rating}
    return render(request, 'dashboard/rate_video.html', context)


@login_required
@student_required
def trainer_contact(request, trainer_id):
    """View trainer contact information"""
    trainer = get_object_or_404(User, id=trainer_id)
    profile = get_object_or_404(Profile, user=trainer)
    student = request.user
    
    # Check if user is a trainer OR is a course instructor for a course the student is enrolled in
    is_trainer = profile.is_trainer
    is_course_instructor = Course.objects.filter(
        instructor=trainer,
        students=student
    ).exists()
    
    if not is_trainer and not is_course_instructor:
        messages.error(request, 'You can only contact trainers or course instructors.')
        return redirect('student_dashboard')
    
    contact_info, created = TrainerContact.objects.get_or_create(trainer=trainer)
    
    # Get average rating
    avg_rating = TrainerRating.objects.filter(trainer=trainer).aggregate(
        Avg('rating')
    )['rating__avg'] or 0
    
    context = {
        'trainer': trainer,
        'contact_info': contact_info,
        'avg_rating': round(avg_rating, 1),
    }
    return render(request, 'dashboard/trainer_contact.html', context)


@login_required
@student_required
def submit_feedback(request, course_id):
    """Submit feedback for a course"""
    course = get_object_or_404(Course, id=course_id)
    user = request.user
    
    # Check if student is enrolled
    if not course.students.filter(id=user.id).exists():
        messages.error(request, 'You must be enrolled in this course to submit feedback.')
        return redirect('student_dashboard')
    
    if request.method == 'POST':
        rating = int(request.POST.get('rating'))
        comment = request.POST.get('comment', '')
        
        Feedback.objects.update_or_create(
            student=user,
            course=course,
            defaults={'rating': rating, 'comment': comment}
        )
        messages.success(request, 'Thank you for your feedback!')
        return redirect('student_course_detail', course_id=course.id)
    
    existing_feedback = Feedback.objects.filter(student=user, course=course).first()
    context = {'course': course, 'existing_feedback': existing_feedback}
    return render(request, 'dashboard/submit_feedback.html', context)


# ==================== TRAINER DASHBOARD & VIEWS ====================

@login_required
@trainer_required
def trainer_dashboard(request):
    """Trainer Dashboard"""
    user = request.user
    
    # Get assigned courses
    assigned_courses = TrainerCourseAssignment.objects.filter(trainer=user)
    course_ids = [ac.course.id for ac in assigned_courses]
    courses = Course.objects.filter(id__in=course_ids)
    
    # Get total students across all assigned courses
    total_students = Enrollment.objects.filter(
        course__in=courses
    ).values('student').distinct().count()
    
    context = {
        'user': user,
        'courses': courses,
        'total_students': total_students,
        'num_courses': courses.count(),
    }
    return render(request, 'dashboard/trainer_dashboard.html', context)


@login_required
@trainer_required
def trainer_course_students(request, course_id):
    """View student progress for a specific course with average time per video"""
    user = request.user
    course = get_object_or_404(Course, id=course_id)
    
    # Check if trainer is assigned to this course
    if not TrainerCourseAssignment.objects.filter(trainer=user, course=course).exists():
        messages.error(request, 'You are not assigned to this course.')
        return redirect('trainer_dashboard')
    
    enrollments = Enrollment.objects.filter(course=course)
    videos = CourseVideo.objects.filter(course=course)
    total_videos = videos.count()
    
    student_progress = []
    for enrollment in enrollments:
        student = enrollment.student
        
        if total_videos > 0:
            completed = VideoProgress.objects.filter(
                student=student, video__course=course, completed=True
            ).count()
            progress_percentage = (completed / total_videos) * 100
            
            # Calculate average time per video
            video_progresses = VideoProgress.objects.filter(
                student=student, video__course=course
            )
            total_time = sum(vp.time_spent_seconds for vp in video_progresses)
            avg_time_per_video = total_time / total_videos if total_videos > 0 else 0
            
            # Format average time
            hours = int(avg_time_per_video // 3600)
            minutes = int((avg_time_per_video % 3600) // 60)
            seconds = int(avg_time_per_video % 60)
            if hours > 0:
                avg_time_formatted = f"{hours}h {minutes}m {seconds}s"
            elif minutes > 0:
                avg_time_formatted = f"{minutes}m {seconds}s"
            else:
                avg_time_formatted = f"{seconds}s"
        else:
            progress_percentage = 0
            completed = 0
            avg_time_formatted = "0s"
        
        student_progress.append({
            'student': student,
            'enrollment': enrollment,
            'progress': progress_percentage,
            'completed_videos': completed if total_videos > 0 else 0,
            'total_videos': total_videos,
            'avg_time_per_video': avg_time_formatted,
            'avg_time_seconds': avg_time_per_video if total_videos > 0 else 0,
        })
    
    context = {
        'course': course,
        'student_progress': student_progress,
    }
    return render(request, 'dashboard/trainer_course_students.html', context)


@login_required
@trainer_required
def trainer_upload_video(request, course_id):
    """Trainer uploads video to assigned course"""
    user = request.user
    course = get_object_or_404(Course, id=course_id)
    
    # Check if trainer is assigned to this course
    if not TrainerCourseAssignment.objects.filter(trainer=user, course=course).exists():
        messages.error(request, 'You are not assigned to this course.')
        return redirect('trainer_dashboard')
    
    if request.method == 'POST':
        title = request.POST.get('title')
        video_file = request.FILES.get('video')
        order = int(request.POST.get('order', 0))
        
        if title and video_file:
            CourseVideo.objects.create(
                course=course,
                title=title,
                video=video_file,
                order=order
            )
            messages.success(request, 'Video uploaded successfully!')
            return redirect('trainer_course_students', course_id=course.id)
        else:
            messages.error(request, 'Please fill all required fields.')
    
    context = {'course': course}
    return render(request, 'dashboard/trainer_upload_video.html', context)


@login_required
@trainer_required
def trainer_edit_contact(request):
    """Trainer edits their own contact information"""
    user = request.user
    contact_info, created = TrainerContact.objects.get_or_create(trainer=user)
    
    if request.method == 'POST':
        contact_info.whatsapp = request.POST.get('whatsapp', '').strip() or None
        contact_info.microsoft_teams = request.POST.get('microsoft_teams', '').strip() or None
        contact_info.skype = request.POST.get('skype', '').strip() or None
        contact_info.email = request.POST.get('email', '').strip() or None
        contact_info.phone = request.POST.get('phone', '').strip() or None
        contact_info.save()
        
        messages.success(request, 'Contact information updated successfully!')
        return redirect('trainer_dashboard')
    
    context = {'contact_info': contact_info}
    return render(request, 'dashboard/trainer_edit_contact.html', context)


@login_required
@trainer_required
def trainer_delete_contact(request):
    """Trainer deletes their contact information"""
    user = request.user
    
    try:
        contact_info = TrainerContact.objects.get(trainer=user)
        if request.method == 'POST':
            contact_info.delete()
            messages.success(request, 'Contact information deleted successfully!')
            return redirect('trainer_dashboard')
        
        context = {'contact_info': contact_info}
        return render(request, 'dashboard/trainer_delete_contact.html', context)
    except TrainerContact.DoesNotExist:
        messages.info(request, 'No contact information to delete.')
        return redirect('trainer_dashboard')


# ==================== MANAGER DASHBOARD & VIEWS ====================

@login_required
@manager_required
def manager_dashboard(request):
    """Manager Dashboard"""
    user = request.user
    
    # Statistics
    total_courses = Course.objects.count()
    total_students = User.objects.filter(profile__is_student=True).count()
    total_trainers = User.objects.filter(profile__is_trainer=True).count()
    total_enrollments = Enrollment.objects.count()
    
    # All courses with details
    all_courses = Course.objects.select_related('instructor').annotate(
        num_students=Count('students'),
        num_videos=Count('videos'),
        avg_rating=Avg('feedbacks__rating')
    ).order_by('-created_at')
    
    # All trainers with ratings
    all_trainers = User.objects.filter(profile__is_trainer=True).annotate(
        num_courses=Count('assigned_courses'),
        avg_rating=Avg('trainer_ratings__rating'),
        num_ratings=Count('trainer_ratings')
    ).order_by('-date_joined')
    
    # All ratings
    trainer_ratings = TrainerRating.objects.select_related('trainer', 'student').order_by('-created_at')[:20]
    video_ratings = VideoRating.objects.select_related('video', 'student').order_by('-created_at')[:20]
    
    # All feedback
    all_feedback = Feedback.objects.select_related('student', 'course').order_by('-created_at')
    
    # Recent enrollments
    recent_enrollments = Enrollment.objects.select_related('student', 'course').order_by('-enrolled_at')[:10]
    
    # Recent feedback (for dashboard widget)
    recent_feedback = Feedback.objects.select_related('student', 'course').order_by('-created_at')[:5]
    
    context = {
        'user': user,
        'total_courses': total_courses,
        'total_students': total_students,
        'total_trainers': total_trainers,
        'total_enrollments': total_enrollments,
        'all_courses': all_courses,
        'all_trainers': all_trainers,
        'trainer_ratings': trainer_ratings,
        'video_ratings': video_ratings,
        'all_feedback': all_feedback,
        'recent_enrollments': recent_enrollments,
        'recent_feedback': recent_feedback,
    }
    return render(request, 'dashboard/manager_dashboard.html', context)


@login_required
@manager_required
def manager_add_course(request):
    """Manager adds a new course"""
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        instructor_id = request.POST.get('instructor')
        duration = request.POST.get('duration', '0 Hours')
        level = request.POST.get('level', 'Beginner')
        category = request.POST.get('category', 'uncategorized')
        price = float(request.POST.get('price', 0))
        discount = float(request.POST.get('discount', 0))
        requirements = request.POST.get('requirements', '')
        content = request.POST.get('content', '')
        thumbnail = request.FILES.get('thumbnail')
        featured_video = request.FILES.get('featured_video')
        
        if instructor_id:
            instructor = get_object_or_404(User, id=instructor_id)
        else:
            instructor = request.user  # Default to manager
        
        discounted_price = (discount / 100) * price
        final_price = price - discounted_price
        
        course = Course.objects.create(
            title=title,
            description=description,
            instructor=instructor,
            duration=duration,
            level=level,
            category=category,
            price=final_price,
            discount=discount,
            requirements=requirements,
            content=content,
        )
        
        if thumbnail:
            course.thumbnail = thumbnail
        if featured_video:
            course.featured_video = featured_video
        course.save()
        
        messages.success(request, f'Course "{title}" created successfully!')
        return redirect('manager_dashboard')
    
    # Get all instructors (managers and trainers)
    instructors = User.objects.filter(
        Q(profile__is_instructor=True) | Q(profile__is_trainer=True)
    )
    
    context = {'instructors': instructors}
    return render(request, 'dashboard/manager_add_course.html', context)


@login_required
@manager_required
def manager_add_trainer(request):
    """Manager adds a new trainer"""
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')
        
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists.')
        elif User.objects.filter(email=email).exists():
            messages.error(request, 'Email already exists.')
        else:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name
            )
            profile, created = Profile.objects.get_or_create(user=user)
            profile.is_trainer = True
            profile.is_student = False
            profile.is_instructor = False
            profile.save()
            
            messages.success(request, f'Trainer "{username}" added successfully!')
            return redirect('manager_dashboard')
    
    return render(request, 'dashboard/manager_add_trainer.html')


@login_required
@manager_required
def manager_edit_trainer(request, trainer_id):
    """Manager edits a trainer"""
    trainer = get_object_or_404(User, id=trainer_id)
    profile = get_object_or_404(Profile, user=trainer)
    
    if not profile.is_trainer:
        messages.error(request, 'This user is not a trainer.')
        return redirect('manager_dashboard')
    
    if request.method == 'POST':
        trainer.first_name = request.POST.get('first_name', trainer.first_name)
        trainer.last_name = request.POST.get('last_name', trainer.last_name)
        trainer.email = request.POST.get('email', trainer.email)
        
        # Update password if provided
        new_password = request.POST.get('password')
        if new_password:
            trainer.set_password(new_password)
        
        trainer.save()
        
        # Update location if provided
        profile.country = request.POST.get('country', profile.country)
        profile.state = request.POST.get('state', profile.state)
        profile.district = request.POST.get('district', profile.district)
        profile.save()
        
        messages.success(request, f'Trainer "{trainer.username}" updated successfully!')
        return redirect('manager_dashboard')
    
    context = {'trainer': trainer, 'profile': profile}
    return render(request, 'dashboard/manager_edit_trainer.html', context)


@login_required
@manager_required
def manager_delete_trainer(request, trainer_id):
    """Manager deletes a trainer"""
    trainer = get_object_or_404(User, id=trainer_id)
    profile = get_object_or_404(Profile, user=trainer)
    
    if not profile.is_trainer:
        messages.error(request, 'This user is not a trainer.')
        return redirect('manager_dashboard')
    
    if request.method == 'POST':
        trainer_username = trainer.username
        
        # Delete all assignments
        TrainerCourseAssignment.objects.filter(trainer=trainer).delete()
        
        # Delete trainer contact info if exists
        try:
            trainer.contact_info.delete()
        except TrainerContact.DoesNotExist:
            pass
        
        # Delete trainer ratings
        TrainerRating.objects.filter(trainer=trainer).delete()
        
        # Delete the user (this will cascade delete profile)
        trainer.delete()
        
        messages.success(request, f'Trainer "{trainer_username}" deleted successfully!')
        return redirect('manager_dashboard')
    
    # Get trainer's assigned courses
    assigned_courses = TrainerCourseAssignment.objects.filter(trainer=trainer)
    
    context = {
        'trainer': trainer,
        'assigned_courses': assigned_courses,
    }
    return render(request, 'dashboard/manager_delete_trainer.html', context)


@login_required
@manager_required
def manager_edit_trainer_contact(request, trainer_id):
    """Manager edits trainer contact information"""
    trainer = get_object_or_404(User, id=trainer_id)
    profile = get_object_or_404(Profile, user=trainer)
    
    if not profile.is_trainer:
        messages.error(request, 'This user is not a trainer.')
        return redirect('manager_dashboard')
    
    contact_info, created = TrainerContact.objects.get_or_create(trainer=trainer)
    
    if request.method == 'POST':
        contact_info.whatsapp = request.POST.get('whatsapp', '').strip() or None
        contact_info.microsoft_teams = request.POST.get('microsoft_teams', '').strip() or None
        contact_info.skype = request.POST.get('skype', '').strip() or None
        contact_info.email = request.POST.get('email', '').strip() or None
        contact_info.phone = request.POST.get('phone', '').strip() or None
        contact_info.save()
        
        messages.success(request, f'Contact information for "{trainer.username}" updated successfully!')
        return redirect('manager_dashboard')
    
    context = {'trainer': trainer, 'contact_info': contact_info}
    return render(request, 'dashboard/manager_edit_trainer_contact.html', context)


@login_required
@manager_required
def manager_delete_trainer_contact(request, trainer_id):
    """Manager deletes trainer contact information"""
    trainer = get_object_or_404(User, id=trainer_id)
    profile = get_object_or_404(Profile, user=trainer)
    
    if not profile.is_trainer:
        messages.error(request, 'This user is not a trainer.')
        return redirect('manager_dashboard')
    
    try:
        contact_info = TrainerContact.objects.get(trainer=trainer)
        if request.method == 'POST':
            contact_info.delete()
            messages.success(request, f'Contact information for "{trainer.username}" deleted successfully!')
            return redirect('manager_dashboard')
        
        context = {'trainer': trainer, 'contact_info': contact_info}
        return render(request, 'dashboard/manager_delete_trainer_contact.html', context)
    except TrainerContact.DoesNotExist:
        messages.info(request, f'No contact information found for "{trainer.username}".')
        return redirect('manager_dashboard')


@login_required
@manager_required
def manager_assign_trainer(request):
    """Manager assigns trainer to course"""
    if request.method == 'POST':
        trainer_id = request.POST.get('trainer')
        course_id = request.POST.get('course')
        
        trainer = get_object_or_404(User, id=trainer_id)
        course = get_object_or_404(Course, id=course_id)
        
        assignment, created = TrainerCourseAssignment.objects.get_or_create(
            trainer=trainer,
            course=course,
            assigned_by=request.user
        )
        
        if created:
            messages.success(request, f'Trainer "{trainer.username}" assigned to "{course.title}" successfully!')
        else:
            messages.info(request, f'Trainer "{trainer.username}" is already assigned to "{course.title}".')
        
        return redirect('manager_assign_trainer')
    
    trainers = User.objects.filter(profile__is_trainer=True)
    courses = Course.objects.all()
    
    # Get all existing assignments
    assignments = TrainerCourseAssignment.objects.select_related('trainer', 'course', 'assigned_by').order_by('-assigned_at')
    
    context = {
        'trainers': trainers,
        'courses': courses,
        'assignments': assignments,
    }
    return render(request, 'dashboard/manager_assign_trainer.html', context)


@login_required
@manager_required
def manager_unassign_trainer(request, assignment_id):
    """Manager unassigns trainer from course"""
    assignment = get_object_or_404(TrainerCourseAssignment, id=assignment_id)
    
    if request.method == 'POST':
        trainer_name = assignment.trainer.username
        course_name = assignment.course.title
        assignment.delete()
        messages.success(request, f'Trainer "{trainer_name}" unassigned from "{course_name}" successfully!')
        return redirect('manager_assign_trainer')
    
    context = {'assignment': assignment}
    return render(request, 'dashboard/manager_unassign_trainer.html', context)


@login_required
@manager_required
def manager_manage_trainer_assignments(request, trainer_id):
    """Manager views and manages all assignments for a specific trainer"""
    trainer = get_object_or_404(User, id=trainer_id)
    profile = get_object_or_404(Profile, user=trainer)
    
    if not profile.is_trainer:
        messages.error(request, 'This user is not a trainer.')
        return redirect('manager_dashboard')
    
    assignments = TrainerCourseAssignment.objects.filter(trainer=trainer).select_related('course', 'assigned_by').order_by('-assigned_at')
    all_courses = Course.objects.all()
    
    if request.method == 'POST':
        course_id = request.POST.get('course')
        if course_id:
            course = get_object_or_404(Course, id=course_id)
            TrainerCourseAssignment.objects.get_or_create(
                trainer=trainer,
                course=course,
                assigned_by=request.user
            )
            messages.success(request, f'Trainer assigned to "{course.title}" successfully!')
            return redirect('manager_manage_trainer_assignments', trainer_id=trainer.id)
    
    context = {
        'trainer': trainer,
        'assignments': assignments,
        'all_courses': all_courses,
    }
    return render(request, 'dashboard/manager_manage_trainer_assignments.html', context)


@login_required
@manager_required
def manager_view_feedback(request):
    """Manager views all student feedback"""
    feedbacks = Feedback.objects.select_related('student', 'course').order_by('-created_at')
    
    # Calculate average rating
    avg_rating = Feedback.objects.aggregate(Avg('rating'))['rating__avg'] or 0
    
    context = {
        'feedbacks': feedbacks,
        'avg_rating': round(avg_rating, 1),
    }
    return render(request, 'dashboard/manager_view_feedback.html', context)


@login_required
@manager_required
def manager_analyze_progress(request):
    """Manager analyzes student progress"""
    courses = Course.objects.all()
    
    course_analytics = []
    for course in courses:
        enrollments = Enrollment.objects.filter(course=course)
        total_students = enrollments.count()
        
        videos = CourseVideo.objects.filter(course=course)
        total_videos = videos.count()
        
        if total_students > 0 and total_videos > 0:
            # Calculate average progress
            total_progress = 0
            for enrollment in enrollments:
                student = enrollment.student
                completed = VideoProgress.objects.filter(
                    student=student, video__course=course, completed=True
                ).count()
                progress = (completed / total_videos) * 100
                total_progress += progress
            
            avg_progress = total_progress / total_students
        else:
            avg_progress = 0
        
        course_analytics.append({
            'course': course,
            'total_students': total_students,
            'total_videos': total_videos,
            'avg_progress': round(avg_progress, 1),
        })
    
    context = {'course_analytics': course_analytics}
    return render(request, 'dashboard/manager_analyze_progress.html', context)


@login_required
@manager_required
def manager_edit_course(request, course_id):
    """Manager edits an existing course"""
    course = get_object_or_404(Course, id=course_id)
    
    if request.method == 'POST':
        course.title = request.POST.get('title', course.title)
        course.description = request.POST.get('description', course.description)
        course.duration = request.POST.get('duration', course.duration)
        course.level = request.POST.get('level', course.level)
        course.category = request.POST.get('category', course.category)
        course.price = float(request.POST.get('price', course.price))
        course.discount = float(request.POST.get('discount', course.discount))
        course.requirements = request.POST.get('requirements', course.requirements)
        course.content = request.POST.get('content', course.content)
        
        instructor_id = request.POST.get('instructor')
        if instructor_id:
            course.instructor = get_object_or_404(User, id=instructor_id)
        
        if 'thumbnail' in request.FILES:
            course.thumbnail = request.FILES['thumbnail']
        if 'featured_video' in request.FILES:
            course.featured_video = request.FILES['featured_video']
        
        course.save()
        messages.success(request, f'Course "{course.title}" updated successfully!')
        return redirect('manager_dashboard')
    
    instructors = User.objects.filter(
        Q(profile__is_instructor=True) | Q(profile__is_trainer=True)
    )
    
    context = {
        'course': course,
        'instructors': instructors,
    }
    return render(request, 'dashboard/manager_edit_course.html', context)


@login_required
@manager_required
def manager_manage_course_videos(request, course_id):
    """Manager views and manages all videos for a course"""
    course = get_object_or_404(Course, id=course_id)
    videos = CourseVideo.objects.filter(course=course).order_by('order', 'created_at')
    
    context = {
        'course': course,
        'videos': videos,
    }
    return render(request, 'dashboard/manager_manage_course_videos.html', context)


@login_required
@manager_required
def manager_add_video_to_course(request, course_id):
    """Manager adds a video to an existing course"""
    course = get_object_or_404(Course, id=course_id)
    
    if request.method == 'POST':
        title = request.POST.get('title')
        video_file = request.FILES.get('video')
        order = int(request.POST.get('order', 0))
        
        if title and video_file:
            CourseVideo.objects.create(
                course=course,
                title=title,
                video=video_file,
                order=order
            )
            messages.success(request, 'Video added successfully!')
            return redirect('manager_manage_course_videos', course_id=course.id)
        else:
            messages.error(request, 'Please fill all required fields.')
    
    context = {'course': course}
    return render(request, 'dashboard/manager_add_video_to_course.html', context)


@login_required
@manager_required
def manager_edit_video(request, video_id):
    """Manager edits a video"""
    video = get_object_or_404(CourseVideo, id=video_id)
    
    if request.method == 'POST':
        video.title = request.POST.get('title', video.title)
        video.order = int(request.POST.get('order', video.order))
        
        if 'video' in request.FILES:
            video.video = request.FILES['video']
        
        video.save()
        messages.success(request, 'Video updated successfully!')
        return redirect('manager_manage_course_videos', course_id=video.course.id)
    
    context = {'video': video}
    return render(request, 'dashboard/manager_edit_video.html', context)


@login_required
@manager_required
def manager_delete_video(request, video_id):
    """Manager deletes a video"""
    video = get_object_or_404(CourseVideo, id=video_id)
    course_id = video.course.id
    
    if request.method == 'POST':
        video_title = video.title
        video.delete()
        messages.success(request, f'Video "{video_title}" deleted successfully!')
        return redirect('manager_manage_course_videos', course_id=course_id)
    
    context = {'video': video}
    return render(request, 'dashboard/manager_delete_video.html', context)


@login_required
@manager_required
def manager_delete_course(request, course_id):
    """Manager deletes a course"""
    course = get_object_or_404(Course, id=course_id)
    
    if request.method == 'POST':
        course_title = course.title
        course.delete()
        messages.success(request, f'Course "{course_title}" deleted successfully!')
        return redirect('manager_dashboard')
    
    context = {'course': course}
    return render(request, 'dashboard/manager_delete_course.html', context)


@login_required
@manager_required
def manager_view_payments(request):
    """Manager views all payment requests"""
    payments = Payment.objects.select_related('student', 'course', 'approved_by').order_by('-payment_date')
    
    # Statistics
    total_payments = payments.count()
    total_amount = sum(p.amount for p in payments if p.status == 'approved')
    requested_payments = payments.filter(status='requested').count()
    approved_payments = payments.filter(status='approved').count()
    rejected_payments = payments.filter(status='rejected').count()
    
    context = {
        'payments': payments,
        'total_payments': total_payments,
        'total_amount': total_amount,
        'requested_payments': requested_payments,
        'approved_payments': approved_payments,
        'rejected_payments': rejected_payments,
    }
    return render(request, 'dashboard/manager_view_payments.html', context)


@login_required
@manager_required
def manager_update_payment(request, payment_id):
    """Manager approves or rejects payment requests"""
    payment = get_object_or_404(Payment, id=payment_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')  # 'approve' or 'reject'
        notes = request.POST.get('notes', '')
        
        if action == 'approve':
            payment.status = 'approved'
            payment.approved_by = request.user
            payment.approved_at = timezone.now()
            
            # Enroll student in course
            if not payment.course.students.filter(id=payment.student.id).exists():
                payment.course.students.add(payment.student)
                Enrollment.objects.get_or_create(student=payment.student, course=payment.course)
            
            if notes:
                payment.notes = notes
            payment.save()
            
            messages.success(request, f'Payment request approved! Student "{payment.student.username}" has been enrolled in "{payment.course.title}".')
            
        elif action == 'reject':
            payment.status = 'rejected'
            payment.approved_by = request.user
            payment.approved_at = timezone.now()
            
            if notes:
                payment.notes = notes
            payment.save()
            
            messages.success(request, f'Payment request rejected.')
        
        return redirect('manager_view_payments')
    
    context = {'payment': payment}
    return render(request, 'dashboard/manager_update_payment.html', context)


# ==================== AJAX VIEWS FOR DEPENDENT DROPDOWNS ====================

@require_http_methods(["GET"])
def get_states(request, country_id):
    """AJAX endpoint to get states for a country"""
    states = State.objects.filter(country_id=country_id).values('id', 'name')
    return JsonResponse(list(states), safe=False)


@require_http_methods(["GET"])
def get_districts(request, state_id):
    """AJAX endpoint to get districts for a state"""
    districts = District.objects.filter(state_id=state_id).values('id', 'name')
    return JsonResponse(list(districts), safe=False)


@login_required
def complete_profile(request):
    """Complete profile with location information after signup"""
    user = request.user
    profile, created = Profile.objects.get_or_create(user=user)
    
    if request.method == 'POST':
        country_id = request.POST.get('country')
        state_id = request.POST.get('state')
        district_id = request.POST.get('district')
        
        if country_id:
            country = get_object_or_404(Country, id=country_id)
            profile.country = country.name
        
        if state_id:
            state = get_object_or_404(State, id=state_id)
            profile.state = state.name
        
        if district_id:
            district = get_object_or_404(District, id=district_id)
            profile.district = district.name
        
        profile.save()
        messages.success(request, 'Profile updated successfully!')
        return redirect('student_dashboard')
    
    countries = Country.objects.all()
    context = {
        'countries': countries,
        'profile': profile,
    }
    return render(request, 'dashboard/complete_profile.html', context)


def profile(request):
    user = request.user
    email = user.email
    full_name = f"{user.first_name} {user.last_name}"
    username = user.username
    return render(request, 'dashboard/profile.html', {'email': email, 'full_name': full_name, 'username': username})


def courses_enrolled(request):
    user = request.user
    courses = Course.objects.filter(students=user)
    context = {
        'courses': courses
    }
    return render(request, 'dashboard/courses-enrolled.html', context)


def courses_uploaded(request):
    courses = Course.objects.filter(instructor=request.user)
    return render(request, 'dashboard/courses-uploaded.html', {'courses': courses})

@login_required
def upload(request):
    if request.method == 'POST':
        # Get course details from the form
        title = request.POST['title']
        description = request.POST['description']
        thumbnail = request.FILES['thumbnail']
        featured_video = request.FILES['featured_video']
        instructor = request.user
        duration = request.POST['duration']
        level = request.POST['level']
        requirements = request.POST['requirements']
        content = request.POST['content']
        category = request.POST['category']
        price = int(request.POST['price'])
        discount = int(request.POST['discount'])

        lesson_title = request.POST['lesson_title']
        lesson_video = request.FILES['lesson_video']

        discounted_price = (discount/100)*price
        price = price-discounted_price

        # Create a new Course object with the given details
        # Django's FileField/ImageField will handle file storage automatically
        course = Course(
            title=title,
            description=description,
            thumbnail=thumbnail,
            featured_video=featured_video,
            instructor=instructor,
            duration=duration,
            level=level,
            requirements=requirements,  # Store as string (comma-separated)
            content=content,  # Store as string (comma-separated)
            category=category,
            price=price,
            discount=discount,
            lesson_title=lesson_title,
            lesson_video=lesson_video,
            )
        course.save()

    return render(request, 'dashboard/upload.html')


# def course_details(request, instructor, slug):
#     instructor_obj = get_object_or_404(User, username=instructor)
#     course = get_object_or_404(Course, slug=slug, instructor=instructor_obj)
#     context = {
#         'course': course
#     }
#     return render(request, 'course.html', context)

def course_details(request, instructor, slug):
    instructor_obj = get_object_or_404(User, username=instructor)
    course = get_object_or_404(Course, slug=slug, instructor=instructor_obj)
    category_courses = Course.objects.filter(category__iexact=course.category).exclude(id=course.id)[:3]

    enrolled = False
    
    if request.user.is_authenticated:
        enrolled = course.students.filter(id=request.user.id).exists()

    if request.method == 'POST' and not enrolled:
        user = request.user
        course.students.add(user)
        enrollment = Enrollment(student=user, course=course)
        enrollment.save()
        messages.success(request, 'You have enrolled in this course!')
        return redirect('course_details', instructor=instructor, slug=slug)

    context = {
        'course': course,
        'enrolled': enrolled,
        'category_courses': category_courses
    }
    return render(request, 'course.html', context)

@login_required
def course_edit(request, slug):
    course = get_object_or_404(Course, slug=slug, instructor=request.user)
    if request.method == 'POST':
        form = CourseEditForm(request.POST, request.FILES, instance=course)
        if form.is_valid():
            form.save()
    else:
        form = CourseEditForm(instance=course)
    return render(request, 'dashboard/course-edit.html', {'form': form, 'course': course})

@login_required
def delete_course(request, slug):
    course = get_object_or_404(Course, slug=slug, instructor=request.user)
    if request.method == 'POST':
        course.delete()
        return redirect('/dashboard/courses-uploaded')
    context = {
        'course': course,
    }
    return render(request, 'dashboard/course-edit.html', context)

def category(request, category):
    courses = Course.objects.filter(category__iexact=category)
    context = {
        'category': category,
        'courses': courses
    }
    return render(request, 'category.html', context)