from django.contrib import admin, messages

from . import services
from .models import (Course, CourseOffering, CoursePrerequisite, CreditLimitRule, DegreeRequirement,
                     Department, DepartmentCourse, Enrollment, GradeScale, Instructor, LevelThreshold,
                     Notification, OfferingTimeSlot, Semester, SeventhCourseRequest,
                     SpecializationRecommendation, Student, StudentCoursePreference,
                     StudentDepartmentChange, StudentSemesterRecord, SummerRequest, SystemSetting)


class TimeSlotInline(admin.TabularInline):
    model = OfferingTimeSlot
    extra = 1


class PrereqInline(admin.TabularInline):
    model = CoursePrerequisite
    fk_name = "course"
    extra = 0


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "name_ar", "is_active")


@admin.register(DegreeRequirement)
class DegreeRequirementAdmin(admin.ModelAdmin):
    list_display = ("scope", "department", "type", "required_hours")
    list_filter = ("scope", "department", "type")


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "credit_hours", "requirement_group", "requirement_type", "min_level", "is_active")
    list_filter = ("requirement_group", "requirement_type", "min_level", "typical_term", "is_active")
    search_fields = ("code", "name", "name_ar")
    inlines = [PrereqInline]


@admin.register(DepartmentCourse)
class DepartmentCourseAdmin(admin.ModelAdmin):
    list_display = ("department", "course", "type")
    list_filter = ("department", "type")
    search_fields = ("course__code", "course__name")


@admin.register(CoursePrerequisite)
class CoursePrerequisiteAdmin(admin.ModelAdmin):
    list_display = ("course", "prerequisite", "group")
    search_fields = ("course__code", "prerequisite__code")


@admin.register(Semester)
class SemesterAdmin(admin.ModelAdmin):
    list_display = ("label", "start_date", "end_date", "registration_deadline", "is_current", "is_closed")
    list_filter = ("term", "is_current", "is_closed")


@admin.register(CourseOffering)
class CourseOfferingAdmin(admin.ModelAdmin):
    list_display = ("course", "semester", "instructor", "status", "capacity")
    list_filter = ("semester", "status")
    search_fields = ("course__code", "course__name")
    inlines = [TimeSlotInline]


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ("university_id", "full_name", "department", "academic_level", "status")
    list_filter = ("department", "academic_level", "status")
    search_fields = ("university_id", "full_name", "full_name_ar", "user__username")


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ("student", "offering", "status", "score", "grade_letter")
    list_filter = ("status", "offering__semester")
    search_fields = ("student__university_id", "offering__course__code")
    raw_id_fields = ("student", "offering")


@admin.register(SummerRequest)
class SummerRequestAdmin(admin.ModelAdmin):
    list_display = ("student", "course", "semester", "status", "fulfilled_by_offering")
    list_filter = ("status", "semester", "course")
    actions = ["open_summer_courses", "reject_summer_courses"]

    @admin.action(description="Open the selected courses for summer (links requests + notifies)")
    def open_summer_courses(self, request, queryset):
        pairs = {(r.course, r.semester) for r in queryset.select_related("course", "semester")}
        for course, semester in pairs:
            try:
                _, n = services.open_summer_offering(course, semester, request.user)
                self.message_user(request, f"{course.code}: opened, {n} request(s) fulfilled.")
            except services.DomainError as exc:
                self.message_user(request, f"{course.code}: {exc}", messages.ERROR)

    @admin.action(description="Reject the demand for the selected courses")
    def reject_summer_courses(self, request, queryset):
        for course, semester in {(r.course, r.semester) for r in queryset.select_related("course", "semester")}:
            n = services.reject_summer_demand(course, semester, request.user)
            self.message_user(request, f"{course.code}: {n} request(s) rejected.")


@admin.register(SeventhCourseRequest)
class SeventhCourseRequestAdmin(admin.ModelAdmin):
    list_display = ("student", "offering", "status", "decided_by", "decided_at")
    list_filter = ("status",)
    actions = ["approve", "reject"]

    @admin.action(description="Approve selected requests")
    def approve(self, request, queryset):
        for r in queryset:
            try:
                services.approve_seventh_request(r, request.user)
            except services.DomainError as exc:
                self.message_user(request, f"{r}: {exc}", messages.ERROR)

    @admin.action(description="Reject selected requests")
    def reject(self, request, queryset):
        for r in queryset:
            try:
                services.reject_seventh_request(r, request.user)
            except services.DomainError as exc:
                self.message_user(request, f"{r}: {exc}", messages.ERROR)


@admin.register(StudentSemesterRecord)
class StudentSemesterRecordAdmin(admin.ModelAdmin):
    list_display = ("student", "semester", "level_at_time", "credits_earned", "semester_gpa", "cumulative_gpa")
    list_filter = ("semester",)

    def has_change_permission(self, request, obj=None):    # frozen snapshot
        return False


for _m in (GradeScale, LevelThreshold, CreditLimitRule, SystemSetting, Instructor, StudentDepartmentChange,
           StudentCoursePreference, SpecializationRecommendation, Notification, OfferingTimeSlot):
    admin.site.register(_m)
