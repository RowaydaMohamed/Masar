from django.db import models
from django.contrib.auth.models import User


class Department(models.Model):
    code = models.CharField(max_length=10, unique=True)          # "AI", "CS", "IT", "IS"
    name_en = models.CharField(max_length=100)
    name_ar = models.CharField(max_length=100)
    compulsory_hours = models.IntegerField(default=39)
    elective_hours = models.IntegerField(default=21)

    def __str__(self):
        return self.code


class Course(models.Model):
    # Team decision: category alone identifies general vs. department, since some
    # courses (e.g. AI310) are compulsory in one department's list and elective in
    # another's — a single department FK couldn't represent that anyway.
    CATEGORY_CHOICES = [
        ("general", "General"),
        ("cs", "Computer Science"),
        ("it", "Information Technology"),
        ("is", "Information Systems"),
        ("ai", "Artificial Intelligence"),
    ]
    REQUIREMENT_CHOICES = [
        ("compulsory", "Compulsory"),
        ("elective", "Elective"),
    ]

    code = models.CharField(max_length=20, unique=True)           # e.g. "CS316"
    name_en = models.CharField(max_length=200)
    name_ar = models.CharField(max_length=200)
    credit_hours = models.IntegerField()
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    requirement_type = models.CharField(max_length=20, choices=REQUIREMENT_CHOICES)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.code


class CoursePrerequisite(models.Model):
    course = models.ForeignKey(
        Course, on_delete=models.CASCADE, related_name="prerequisites"
    )
    prerequisite_course = models.ForeignKey(
        Course, on_delete=models.CASCADE, related_name="unlocks"
    )

    class Meta:
        unique_together = ("course", "prerequisite_course")

    def __str__(self):
        return f"{self.course.code} needs {self.prerequisite_course.code}"


class GradeScale(models.Model):
    min_score = models.IntegerField()
    max_score = models.IntegerField()
    letter = models.CharField(max_length=5)          # "A+", "A", "B+", ...
    gpa_points = models.DecimalField(max_digits=3, decimal_places=2)

    def __str__(self):
        return f"{self.min_score}-{self.max_score} -> {self.letter}"


class Student(models.Model):
    STATUS_CHOICES = [
        ("enrolled", "Enrolled"),
        ("graduated", "Graduated"),
        ("probation", "Probation"),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    university_email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=150)
    entry_year = models.IntegerField()
    academic_level = models.IntegerField()
    department = models.ForeignKey(
        Department, on_delete=models.SET_NULL, null=True, blank=True
    )
    cgpa = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    total_hours_completed = models.IntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="enrolled")

    def __str__(self):
        return self.full_name


class StudentCourseHistory(models.Model):
    STATUS_CHOICES = [
        ("completed", "Completed"),
        ("failed", "Failed"),
        ("registered", "Registered"),
        ("withdrawn", "Withdrawn"),
    ]

    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    academic_year = models.CharField(max_length=20, null=True, blank=True)
    semester = models.CharField(max_length=20, null=True, blank=True)
    numeric_score = models.IntegerField(null=True, blank=True)
    letter_grade = models.CharField(max_length=5, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    attempt_number = models.IntegerField(default=1)

    def __str__(self):
        return f"{self.student.full_name} - {self.course.code} ({self.status})"


class ScheduleSlot(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    day = models.CharField(max_length=20)
    start_time = models.TimeField()
    end_time = models.TimeField()


class Notification(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    text = models.CharField(max_length=300)
    icon = models.CharField(max_length=10, default="📢")
    created_at = models.DateTimeField(auto_now_add=True)


class SummerRequest(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("review", "Review"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")


class SeventhCourseRequest(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    requested_at = models.DateTimeField(auto_now_add=True)


class SpecializationRecommendation(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    recommended_department = models.ForeignKey(
        Department, on_delete=models.SET_NULL, null=True
    )
    confidence = models.DecimalField(max_digits=4, decimal_places=3)
    reason = models.TextField()
    generated_at = models.DateTimeField(auto_now_add=True)