from django.contrib import admin
from .models import (
    Department,
    Course,
    CoursePrerequisite,
    GradeScale,
    Student,
    StudentCourseHistory,
    ScheduleSlot,
    Notification,
    SummerRequest,
    SeventhCourseRequest,
    SpecializationRecommendation,
)

admin.site.register(Department)
admin.site.register(Course)
admin.site.register(CoursePrerequisite)
admin.site.register(GradeScale)
admin.site.register(Student)
admin.site.register(StudentCourseHistory)
admin.site.register(ScheduleSlot)
admin.site.register(Notification)
admin.site.register(SummerRequest)
admin.site.register(SeventhCourseRequest)
admin.site.register(SpecializationRecommendation)