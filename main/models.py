from django.db import models
from django.utils.text import slugify
from django.contrib.auth.models import User


# -------------------------
# USER PROFILE (STUDENT / TRAINER / MANAGER)
# -------------------------
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    # ROLE MANAGEMENT
    is_instructor = models.BooleanField(default=False)   # Manager
    is_trainer = models.BooleanField(default=False)      # Trainer
    is_student = models.BooleanField(default=True)       # Default role

    # Location fields for registration
    country = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    district = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return self.user.username

    def get_role(self):
        """Returns the primary role of the user"""
        if self.is_instructor:
            return 'Manager'
        elif self.is_trainer:
            return 'Trainer'
        else:
            return 'Student'


# -------------------------
# LIBRARY MODEL
# -------------------------
class library(models.Model):
    title = models.CharField(max_length=100)
    description = models.CharField(max_length=255)
    image = models.ImageField(upload_to="library_images/", blank=True, null=True)

    def __str__(self):
        return self.title


# -------------------------
# COURSE MODEL
# -------------------------
class Course(models.Model):
    LEVEL_CHOICES = [
        ('Beginner', 'Beginner'),
        ('Intermediate', 'Intermediate'),
        ('Advanced', 'Advanced'),
    ]

    id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    description = models.TextField()

    thumbnail = models.ImageField(upload_to="thumbnails/", blank=True, null=True)
    featured_video = models.FileField(upload_to="videos/", blank=True, null=True)

    instructor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='courses', default=None)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    level = models.CharField(max_length=20, choices=LEVEL_CHOICES, default='Beginner')
    duration = models.CharField(max_length=20, default='0 Hours')
    category = models.CharField(max_length=255, default="uncategorized")

    price = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    discount = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)

    requirements = models.TextField(help_text='Enter the requirements separated by commas.', default='')
    content = models.TextField(help_text='Enter the course content separated by commas.', default='')

    lesson_title = models.CharField(max_length=255, default='Lesson')
    lesson_video = models.FileField(upload_to="lesson_videos/", blank=True, null=True)

    students = models.ManyToManyField(User, related_name='enrolled_courses', blank=True)

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def get_instructor_username(self):
        return self.instructor.username

    def get_requirements_list(self):
        return [i.strip() for i in self.requirements.split(',') if i.strip()]

    def get_content_list(self):
        return [i.strip() for i in self.content.split(',') if i.strip()]


# -------------------------
# ENROLLMENT MODEL
# -------------------------
class Enrollment(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='enrollments')
    enrolled_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.student.username} enrolled in {self.course.title}'


# -------------------------
# LOCATION MODELS (Country → State → District)
# -------------------------
class Country(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class State(models.Model):
    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name='states')
    name = models.CharField(max_length=100)

    class Meta:
        unique_together = ['country', 'name']

    def __str__(self):
        return f'{self.name}, {self.country.name}'


class District(models.Model):
    state = models.ForeignKey(State, on_delete=models.CASCADE, related_name='districts')
    name = models.CharField(max_length=100)

    class Meta:
        unique_together = ['state', 'name']

    def __str__(self):
        return f'{self.name}, {self.state.name}'


# -------------------------
# COURSE VIDEO MODEL (Multiple videos per course)
# -------------------------
class CourseVideo(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='videos')
    title = models.CharField(max_length=255)
    video = models.FileField(upload_to="course_videos/", blank=True, null=True)
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'created_at']

    def __str__(self):
        return f'{self.course.title} - {self.title}'


# -------------------------
# VIDEO PROGRESS TRACKING
# -------------------------
class VideoProgress(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='video_progress')
    video = models.ForeignKey(CourseVideo, on_delete=models.CASCADE, related_name='progress')
    completed = models.BooleanField(default=False)
    progress_percentage = models.IntegerField(default=0)  # 0-100
    time_spent_seconds = models.IntegerField(default=0, help_text='Total time spent watching this video in seconds')
    last_watched = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['student', 'video']

    def __str__(self):
        return f'{self.student.username} - {self.video.title} ({self.progress_percentage}%)'
    
    def get_time_spent_formatted(self):
        """Returns time spent in HH:MM:SS format"""
        hours = self.time_spent_seconds // 3600
        minutes = (self.time_spent_seconds % 3600) // 60
        seconds = self.time_spent_seconds % 60
        if hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"


# -------------------------
# RATING MODELS
# -------------------------
class TrainerRating(models.Model):
    RATING_CHOICES = [
        (1, '1 Star'),
        (2, '2 Stars'),
        (3, '3 Stars'),
        (4, '4 Stars'),
        (5, '5 Stars'),
    ]
    trainer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='trainer_ratings')
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='given_trainer_ratings')
    rating = models.IntegerField(choices=RATING_CHOICES)
    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['trainer', 'student']

    def __str__(self):
        return f'{self.student.username} rated {self.trainer.username} - {self.rating} stars'


class VideoRating(models.Model):
    RATING_CHOICES = [
        (1, '1 Star'),
        (2, '2 Stars'),
        (3, '3 Stars'),
        (4, '4 Stars'),
        (5, '5 Stars'),
    ]
    video = models.ForeignKey(CourseVideo, on_delete=models.CASCADE, related_name='ratings')
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='given_video_ratings')
    rating = models.IntegerField(choices=RATING_CHOICES)
    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['video', 'student']

    def __str__(self):
        return f'{self.student.username} rated {self.video.title} - {self.rating} stars'


# -------------------------
# TRAINER CONTACT INFO
# -------------------------
class TrainerContact(models.Model):
    trainer = models.OneToOneField(User, on_delete=models.CASCADE, related_name='contact_info')
    whatsapp = models.URLField(blank=True, null=True, help_text='WhatsApp contact link')
    microsoft_teams = models.URLField(blank=True, null=True, help_text='Microsoft Teams contact link')
    skype = models.URLField(blank=True, null=True, help_text='Skype contact link')
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return f'Contact info for {self.trainer.username}'


# -------------------------
# STUDENT FEEDBACK
# -------------------------
class Feedback(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='feedbacks')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='feedbacks')
    rating = models.IntegerField(choices=TrainerRating.RATING_CHOICES)
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Feedback from {self.student.username} for {self.course.title}'


# -------------------------
# TRAINER-COURSE ASSIGNMENT (Manager assigns trainers to courses)
# -------------------------
class TrainerCourseAssignment(models.Model):
    trainer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='assigned_courses')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='assigned_trainers')
    assigned_at = models.DateTimeField(auto_now_add=True)
    assigned_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='assignments_made')

    class Meta:
        unique_together = ['trainer', 'course']

    def __str__(self):
        return f'{self.trainer.username} assigned to {self.course.title}'


# -------------------------
# PAYMENT MODEL (Track student payments)
# -------------------------
class Payment(models.Model):
    PAYMENT_STATUS_CHOICES = [
        ('requested', 'Payment Requested'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    PAYMENT_METHOD_CHOICES = [
        ('card', 'Credit/Debit Card'),
        ('upi', 'UPI'),
        ('netbanking', 'Net Banking'),
        ('wallet', 'Wallet'),
        ('cash', 'Cash'),
        ('other', 'Other'),
    ]
    
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='card')
    transaction_id = models.CharField(max_length=255, blank=True, null=True, help_text='Transaction ID (if available)')
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='requested')
    payment_date = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_payments')
    approved_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, null=True, help_text='Manager notes about this payment')
    
    class Meta:
        ordering = ['-payment_date']
    
    def __str__(self):
        return f'{self.student.username} - {self.course.title} - ${self.amount} ({self.get_status_display()})'
