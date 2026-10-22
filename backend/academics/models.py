"""
Masar - academics/models.py  (ERD v3, 23 tables incl. Django's auth_user)

Requires Django >= 5.1 (CheckConstraint(condition=...)). On older Django replace
`condition=` with `check=`.  Recommended settings:
    DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
    AUTH_USER_MODEL    = "auth.User"   # default; Student is the profile

Rules the database cannot express as plain constraints (cycles, "passed course cannot be
retaken", summer-only semester, ...) live in db_rules.sql (installed with RunSQL) AND are
checked in services.py.
"""
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q

User = settings.AUTH_USER_MODEL


def enum_check(tag, field, choices):
    """DB-level CHECK that a text column only holds values of a TextChoices class."""
    return models.CheckConstraint(
        condition=Q(**{f"{field}__in": list(choices.values)}),
        name=f"ck_{tag}_{field}_valid",
    )


# ======================================================================================
# A. CATALOG  (bylaw; changes rarely)
# ======================================================================================
class DegreeScope(models.TextChoices):
    GENERAL = "general", "General (Art. 19)"
    FACULTY = "faculty", "Faculty (Art. 20)"
    DEPARTMENT = "department", "Department (Art. 21)"


class RequirementType(models.TextChoices):
    COMPULSORY = "compulsory", "Compulsory"
    ELECTIVE = "elective", "Elective"


class CourseGroup(models.TextChoices):
    GENERAL = "general", "General"
    FACULTY = "faculty", "Faculty"
    DEPARTMENT = "department", "Department"


class CourseTerm(models.TextChoices):
    FALL = "fall", "Fall"
    SPRING = "spring", "Spring"
    BOTH = "both", "Both"


class SemesterTerm(models.TextChoices):
    FALL = "fall", "Fall"
    SPRING = "spring", "Spring"
    SUMMER = "summer", "Summer"


class OfferingStatus(models.TextChoices):
    PROPOSED = "proposed", "Proposed"
    OPEN = "open", "Open"
    CLOSED = "closed", "Closed"


class WeekDay(models.TextChoices):
    SAT = "sat", "Saturday"
    SUN = "sun", "Sunday"
    MON = "mon", "Monday"
    TUE = "tue", "Tuesday"
    WED = "wed", "Wednesday"
    THU = "thu", "Thursday"


class StudentStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    GRADUATED = "graduated", "Graduated"
    SUSPENDED = "suspended", "Suspended"


class EnrollmentStatus(models.TextChoices):
    REGISTERED = "registered", "Registered"
    COMPLETED = "completed", "Completed (passed)"
    FAILED = "failed", "Failed"
    WITHDRAWN = "withdrawn", "Withdrawn"


class PreferenceKind(models.TextChoices):
    WANT = "want", "Want"
    AVOID = "avoid", "Avoid"


class DecisionStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"


class NotificationType(models.TextChoices):
    SEVENTH_APPROVED = "seventh_approved", "7th course approved"
    SEVENTH_REJECTED = "seventh_rejected", "7th course rejected"
    SUMMER_OPENED = "summer_opened", "Summer course opened"
    SUMMER_REJECTED = "summer_rejected", "Summer request rejected"
    DEPARTMENT_CHANGED = "department_changed", "Department changed"
    SYSTEM = "system", "System"

class Department(models.Model):
    code = models.CharField(max_length=10, unique=True)            # CS / IT / IS / AI
    name = models.CharField(max_length=120)
    name_ar = models.CharField(max_length=120, blank=True, default="")
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "department"
        ordering = ["code"]

    def __str__(self):
        return self.code


class DegreeRequirement(models.Model):
    """144 = 12 general + 72 faculty + 60 department. The total is a SUM of these rows."""

    class Scope(models.TextChoices):
        GENERAL = "general", "General (Art. 19)"
        FACULTY = "faculty", "Faculty (Art. 20)"
        DEPARTMENT = "department", "Department (Art. 21)"

    class Type(models.TextChoices):
        COMPULSORY = "compulsory", "Compulsory"
        ELECTIVE = "elective", "Elective"

    scope = models.CharField(max_length=12, choices=Scope.choices)
    department = models.ForeignKey(
        Department, null=True, blank=True, on_delete=models.PROTECT,
        related_name="degree_requirements",
    )
    type = models.CharField(max_length=12, choices=Type.choices)
    required_hours = models.PositiveSmallIntegerField()

    class Meta:
        db_table = "degree_requirement"
        constraints = [
            models.CheckConstraint(
                condition=Q(required_hours__gt=0), name="ck_degreq_hours_positive"),
            models.CheckConstraint(
                condition=(Q(scope="department", department__isnull=False)
                           | (~Q(scope="department") & Q(department__isnull=True))),
                name="ck_degreq_dept_iff_dept_scope"),
            # NULLs are distinct in a plain UNIQUE, so use two partial uniques.
            models.UniqueConstraint(
                fields=["scope", "department", "type"],
                condition=Q(department__isnull=False), name="uq_degreq_dept"),
            models.UniqueConstraint(
                fields=["scope", "type"],
                condition=Q(department__isnull=True), name="uq_degreq_global"),
            enum_check("degreq", "scope", DegreeScope),
enum_check("degreq", "type", RequirementType),
        ]

    def __str__(self):
        return f"{self.scope}/{self.department_id or '-'}/{self.type}: {self.required_hours}h"


class Course(models.Model):
    class Group(models.TextChoices):
        GENERAL = "general", "General"
        FACULTY = "faculty", "Faculty"
        DEPARTMENT = "department", "Department"

    class Type(models.TextChoices):
        COMPULSORY = "compulsory", "Compulsory"
        ELECTIVE = "elective", "Elective"

    class Term(models.TextChoices):
        FALL = "fall", "Fall"
        SPRING = "spring", "Spring"
        BOTH = "both", "Both"

    code = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=200)
    name_ar = models.CharField(max_length=200, blank=True, default="")
    description = models.TextField(blank=True, default="")
    description_ar = models.TextField(blank=True, default="")
    credit_hours = models.PositiveSmallIntegerField(default=3)
    lecture_hours = models.PositiveSmallIntegerField(default=2)
    lab_hours = models.PositiveSmallIntegerField(default=0)       # lab / tutorial
    requirement_group = models.CharField(max_length=12, choices=Group.choices)
    # compulsory/elective for general+faculty courses; NULL for department courses
    # (their role lives on DepartmentCourse, per department).
    requirement_type = models.CharField(max_length=12, choices=Type.choices, null=True, blank=True)
    min_level = models.PositiveSmallIntegerField(default=1)       # first digit of the code
    typical_term = models.CharField(max_length=6, choices=Term.choices, default=Term.BOTH)
    is_active = models.BooleanField(default=True)                  # retire, never delete

    class Meta:
        db_table = "course"
        ordering = ["code"]
        constraints = [
            models.CheckConstraint(condition=Q(credit_hours__gt=0), name="ck_course_credits_positive"),
            models.CheckConstraint(
                condition=Q(min_level__gte=1, min_level__lte=4), name="ck_course_min_level_range"),
            models.CheckConstraint(
                condition=(Q(requirement_group="department", requirement_type__isnull=True)
                           | (~Q(requirement_group="department") & Q(requirement_type__isnull=False))),
                name="ck_course_type_iff_not_dept"),
            enum_check("course", "requirement_group", CourseGroup),
            enum_check("course", "typical_term", CourseTerm),
        ]

    def __str__(self):
        return f"{self.code} {self.name}"


class DepartmentCourse(models.Model):
    """Role of a course INSIDE one department (AI310: compulsory in CS/IT/AI, elective in IS)."""
    department = models.ForeignKey(Department, on_delete=models.PROTECT, related_name="pool")
    course = models.ForeignKey(Course, on_delete=models.PROTECT, related_name="department_roles")
    type = models.CharField(max_length=12, choices=Course.Type.choices)

    class Meta:
        db_table = "department_course"
        constraints = [
            models.UniqueConstraint(fields=["department", "course"], name="uq_deptcourse_dept_course"),
            enum_check("deptcourse", "type", Course.Type),
        ]

    def clean(self):
        if self.course_id and self.course.requirement_group != Course.Group.DEPARTMENT:
            raise ValidationError("Only courses in the 'department' group belong to a department pool.")

    def __str__(self):
        return f"{self.department_id}:{self.course_id}:{self.type}"


class CoursePrerequisite(models.Model):
    """Rows with the same group are ALL required (AND); different groups are
    alternatives (OR). Level standing is Course.min_level, not a row here."""
    course = models.ForeignKey(Course, on_delete=models.PROTECT, related_name="prerequisite_links")
    prerequisite = models.ForeignKey(Course, on_delete=models.PROTECT, related_name="unlocks_links")
    group = models.PositiveSmallIntegerField(default=1, db_column="group_number")

    class Meta:
        db_table = "course_prerequisite"
        constraints = [
            models.UniqueConstraint(fields=["course", "prerequisite", "group"],
                                    name="uq_prereq_course_prereq_group"),
            models.CheckConstraint(condition=~Q(course=models.F("prerequisite")),
                                   name="ck_prereq_not_self"),
            models.CheckConstraint(condition=Q(group__gte=1), name="ck_prereq_group_positive"),
        ]
        indexes = [models.Index(fields=["prerequisite"], name="ix_prereq_prerequisite")]


class GradeScale(models.Model):
    letter = models.CharField(max_length=3, unique=True)
    points = models.DecimalField(max_digits=3, decimal_places=2)
    min_score = models.DecimalField(max_digits=5, decimal_places=2)   # lowest score for this letter
    is_passing = models.BooleanField()

    class Meta:
        db_table = "grade_scale"
        ordering = ["-min_score"]
        constraints = [
            models.CheckConstraint(condition=Q(points__gte=0, points__lte=4), name="ck_grade_points_range"),
            models.CheckConstraint(condition=Q(min_score__gte=0, min_score__lte=100),
                                   name="ck_grade_min_score_range"),
        ]


class LevelThreshold(models.Model):
    level = models.PositiveSmallIntegerField(unique=True)             # 1..4
    min_earned_hours = models.PositiveSmallIntegerField()             # 0, 36, 72, 108

    class Meta:
        db_table = "level_threshold"
        ordering = ["level"]
        constraints = [
            models.CheckConstraint(condition=Q(level__gte=1, level__lte=4), name="ck_level_range"),
            models.UniqueConstraint(fields=["min_earned_hours"], name="uq_level_min_hours"),
        ]


class CreditLimitRule(models.Model):
    """Max credits per semester for a CGPA band [min_cgpa, max_cgpa). NULL = unbounded.
    Non-overlap is enforced by an EXCLUDE constraint in db_rules.sql."""
    min_cgpa = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)
    max_cgpa = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)
    max_credits = models.PositiveSmallIntegerField()

    class Meta:
        db_table = "credit_limit_rule"
        constraints = [
            models.CheckConstraint(
                condition=(Q(min_cgpa__isnull=True) | Q(max_cgpa__isnull=True)
                           | Q(max_cgpa__gt=models.F("min_cgpa"))),
                name="ck_creditlimit_band_valid"),
            models.CheckConstraint(condition=Q(max_credits__gt=0), name="ck_creditlimit_positive"),
        ]


class SystemSetting(models.Model):
    """seventh_course_min_cgpa, max_courses_per_semester, summer_max_credits,
    graduation_min_cgpa, probation_cgpa, new_student_max_credits."""
    key = models.CharField(max_length=80, unique=True)
    value = models.CharField(max_length=255)
    description = models.CharField(max_length=255, blank=True, default="")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "system_setting"


# ======================================================================================
# B. TIME & OFFERINGS
# ======================================================================================
class Semester(models.Model):
    class Term(models.TextChoices):
        FALL = "fall", "Fall"
        SPRING = "spring", "Spring"
        SUMMER = "summer", "Summer"

    academic_year = models.PositiveSmallIntegerField()   # start year: 2026 means 2026/2027
    term = models.CharField(max_length=6, choices=Term.choices)
    start_date = models.DateField()
    end_date = models.DateField()
    registration_deadline = models.DateTimeField()
    is_current = models.BooleanField(default=False)
    is_closed = models.BooleanField(default=False)       # set by close_semester()

    class Meta:
        db_table = "semester"
        ordering = ["start_date"]
        constraints = [
            models.UniqueConstraint(fields=["academic_year", "term"], name="uq_semester_year_term"),
            models.CheckConstraint(condition=Q(end_date__gt=models.F("start_date")),
                                   name="ck_semester_dates"),
            models.UniqueConstraint(fields=["is_current"], condition=Q(is_current=True),
                                    name="uq_semester_single_current"),
            models.CheckConstraint(condition=Q(is_current=False) | Q(is_closed=False),
                                   name="ck_semester_current_not_closed"),
            enum_check("semester", "term", SemesterTerm),
        ]

    @property
    def label(self):
        return f"{self.academic_year}/{self.academic_year + 1} {self.term}"

    def __str__(self):
        return self.label


class Instructor(models.Model):
    name = models.CharField(max_length=150)
    name_ar = models.CharField(max_length=150, blank=True, default="")
    email = models.EmailField(null=True, blank=True, unique=True)

    class Meta:
        db_table = "instructor"

    def __str__(self):
        return self.name


class CourseOffering(models.Model):
    """Course X running in semester Y (no sections: one offering per course per semester)."""
    class Status(models.TextChoices):
        PROPOSED = "proposed", "Proposed"
        OPEN = "open", "Open"
        CLOSED = "closed", "Closed"

    course = models.ForeignKey(Course, on_delete=models.PROTECT, related_name="offerings")
    semester = models.ForeignKey(Semester, on_delete=models.PROTECT, related_name="offerings")
    instructor = models.ForeignKey(Instructor, null=True, blank=True, on_delete=models.SET_NULL,
                                   related_name="offerings")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PROPOSED)
    capacity = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        db_table = "course_offering"
        constraints = [
            models.UniqueConstraint(fields=["course", "semester"], name="uq_offering_course_semester"),
           enum_check("offering", "status", OfferingStatus),
        ]
        indexes = [models.Index(fields=["semester", "status"], name="ix_offering_sem_status")]

    def __str__(self):
        return f"{self.course_id}@{self.semester_id}"


class OfferingTimeSlot(models.Model):
    class Day(models.TextChoices):
        SAT = "sat", "Saturday"
        SUN = "sun", "Sunday"
        MON = "mon", "Monday"
        TUE = "tue", "Tuesday"
        WED = "wed", "Wednesday"
        THU = "thu", "Thursday"

    offering = models.ForeignKey(CourseOffering, on_delete=models.CASCADE, related_name="time_slots")
    day = models.CharField(max_length=3, choices=Day.choices)
    start_time = models.TimeField()
    end_time = models.TimeField()

    class Meta:
        db_table = "offering_time_slot"
        constraints = [
            models.UniqueConstraint(fields=["offering", "day", "start_time"], name="uq_slot_offering_day_start"),
            models.CheckConstraint(condition=Q(end_time__gt=models.F("start_time")), name="ck_slot_times"),
           enum_check("slot", "day", WeekDay),
        ]


# ======================================================================================
# C. IDENTITY + STUDENT HISTORY
# ======================================================================================
class Student(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        GRADUATED = "graduated", "Graduated"
        SUSPENDED = "suspended", "Suspended"

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="student")
    university_id = models.CharField(max_length=20, unique=True)
    full_name = models.CharField(max_length=150)
    full_name_ar = models.CharField(max_length=150, blank=True, default="")
    # Written ONLY by services.close_semester (derived from earned hours).
    academic_level = models.PositiveSmallIntegerField(default=1)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)
    department = models.ForeignKey(Department, null=True, blank=True, on_delete=models.SET_NULL,
                                   related_name="students")
    admission_semester = models.ForeignKey(Semester, on_delete=models.PROTECT,
                                           related_name="admitted_students")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "student"
        constraints = [
            models.CheckConstraint(condition=Q(academic_level__gte=1, academic_level__lte=4),
                                   name="ck_student_level_range"),
           enum_check("student", "status", StudentStatus),
        ]
        indexes = [models.Index(fields=["department"], name="ix_student_department")]

    def __str__(self):
        return f"{self.university_id} {self.full_name}"


class Enrollment(models.Model):
    """One row per ATTEMPT. Never deleted; a withdrawal sets status='withdrawn'.
    'completed' = passed, 'failed' = failed. Grade letter/points are snapshots."""
    class Status(models.TextChoices):
        REGISTERED = "registered", "Registered"
        COMPLETED = "completed", "Completed (passed)"
        FAILED = "failed", "Failed"
        WITHDRAWN = "withdrawn", "Withdrawn"

    student = models.ForeignKey(Student, on_delete=models.PROTECT, related_name="enrollments")
    offering = models.ForeignKey(CourseOffering, on_delete=models.PROTECT, related_name="enrollments")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.REGISTERED)
    score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True,
                                validators=[MinValueValidator(0), MaxValueValidator(100)])
    grade_letter = models.CharField(max_length=3, null=True, blank=True)   # NULL needed by CHECK below
    grade_points = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)
    graded_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL,
                                  related_name="graded_enrollments")
    graded_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "enrollment"
        constraints = [
            models.UniqueConstraint(fields=["student", "offering"], name="uq_enrollment_student_offering"),
            models.CheckConstraint(condition=Q(score__isnull=True) | Q(score__gte=0, score__lte=100),
                                   name="ck_enrollment_score_range"),
            models.CheckConstraint(condition=Q(grade_points__isnull=True) | Q(grade_points__gte=0, grade_points__lte=4),
                                   name="ck_enrollment_points_range"),
            models.CheckConstraint(
                condition=(
                    (Q(status__in=["registered", "withdrawn"])
                     & Q(score__isnull=True, grade_letter__isnull=True, grade_points__isnull=True))
                    | (Q(status__in=["completed", "failed"])
                       & Q(grade_letter__isnull=False, grade_points__isnull=False))),
                name="ck_enrollment_grade_fields"),
            enum_check("enrollment", "status", EnrollmentStatus),
        ]
        indexes = [
            models.Index(fields=["student", "status"], name="ix_enroll_student_status"),
            models.Index(fields=["offering"], name="ix_enroll_offering"),
        ]


class StudentSemesterRecord(models.Model):
    """Frozen snapshot of a closed semester (written once by close_semester; immutable trigger)."""
    student = models.ForeignKey(Student, on_delete=models.PROTECT, related_name="semester_records")
    semester = models.ForeignKey(Semester, on_delete=models.PROTECT, related_name="student_records")
    level_at_time = models.PositiveSmallIntegerField()
    department_at_time = models.ForeignKey(Department, null=True, blank=True, on_delete=models.SET_NULL,
                                           related_name="semester_records")
    credits_attempted = models.PositiveSmallIntegerField()
    credits_earned = models.PositiveSmallIntegerField()
    cumulative_earned_hours = models.PositiveSmallIntegerField(default=0)
    semester_gpa = models.DecimalField(max_digits=3, decimal_places=2)
    cumulative_gpa = models.DecimalField(max_digits=3, decimal_places=2)
    closed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "student_semester_record"
        constraints = [
            models.UniqueConstraint(fields=["student", "semester"], name="uq_semrecord_student_semester"),
            models.CheckConstraint(condition=Q(credits_earned__lte=models.F("credits_attempted")),
                                   name="ck_semrecord_earned_le_attempted"),
            models.CheckConstraint(condition=Q(semester_gpa__gte=0, semester_gpa__lte=4, cumulative_gpa__gte=0, cumulative_gpa__lte=4),
                                   name="ck_semrecord_gpa_range"),
            models.CheckConstraint(condition=Q(level_at_time__gte=1, level_at_time__lte=4),
                                   name="ck_semrecord_level_range"),
        ]


class StudentDepartmentChange(models.Model):
    student = models.ForeignKey(Student, on_delete=models.PROTECT, related_name="department_changes")
    from_department = models.ForeignKey(Department, null=True, blank=True, on_delete=models.PROTECT,
                                        related_name="changes_out")
    to_department = models.ForeignKey(Department, on_delete=models.PROTECT, related_name="changes_in")
    semester = models.ForeignKey(Semester, on_delete=models.PROTECT, related_name="department_changes")
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "student_department_change"
        constraints = [
            models.CheckConstraint(
                condition=Q(from_department__isnull=True) | ~Q(from_department=models.F("to_department")),
                name="ck_deptchange_differs"),
        ]


class StudentCoursePreference(models.Model):
    class Kind(models.TextChoices):
        WANT = "want", "Want"
        AVOID = "avoid", "Avoid"

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="course_preferences")
    course = models.ForeignKey(Course, on_delete=models.PROTECT, related_name="preferences")
    kind = models.CharField(max_length=5, choices=Kind.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "student_course_preference"
        constraints = [
            models.UniqueConstraint(fields=["student", "course"], name="uq_pref_student_course"),
            enum_check("pref", "kind", PreferenceKind),
        ]


# ======================================================================================
# D. REQUESTS, AI, NOTIFICATIONS
# ======================================================================================
class DecisionStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"


class _DecidedRequest(models.Model):
    status = models.CharField(max_length=10, choices=DecisionStatus.choices, default=DecisionStatus.PENDING)
    decided_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL,
                                   related_name="decided_%(class)s_set")
    decided_at = models.DateTimeField(null=True, blank=True)
    decision_reason = models.CharField(max_length=500, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


def _decision_checks(tag):
    # decided_by is NOT in the rule: it is SET_NULL if the staff user is deleted.
    return [
        models.CheckConstraint(
            condition=(Q(status="pending", decided_at__isnull=True)
                       | (~Q(status="pending") & Q(decided_at__isnull=False))),
            name=f"ck_{tag}_decided_at_iff_decided"),
        enum_check(tag, "status", DecisionStatus),
    ]


class SummerRequest(_DecidedRequest):
    """Student DEMAND for a course in a summer semester (not an enrollment)."""
    student = models.ForeignKey(Student, on_delete=models.PROTECT, related_name="summer_requests")
    course = models.ForeignKey(Course, on_delete=models.PROTECT, related_name="summer_requests")
    semester = models.ForeignKey(Semester, on_delete=models.PROTECT, related_name="summer_requests")
    fulfilled_by_offering = models.ForeignKey(CourseOffering, null=True, blank=True,
                                              on_delete=models.SET_NULL, related_name="fulfilled_requests")

    class Meta:
        db_table = "summer_request"
        constraints = [
            models.UniqueConstraint(fields=["student", "course", "semester"], name="uq_summer_student_course_sem"),
            *_decision_checks("summer"),
        ]
        indexes = [models.Index(fields=["semester", "course", "status"], name="ix_summer_demand")]


class SeventhCourseRequest(_DecidedRequest):
    student = models.ForeignKey(Student, on_delete=models.PROTECT, related_name="seventh_requests")
    offering = models.ForeignKey(CourseOffering, on_delete=models.PROTECT, related_name="seventh_requests")
    reason = models.CharField(max_length=500, blank=True, default="")

    class Meta:
        db_table = "seventh_course_request"
        constraints = [
            models.UniqueConstraint(fields=["student", "offering"], name="uq_seventh_student_offering"),
            *_decision_checks("seventh"),
        ]


class SpecializationRecommendation(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="recommendations")
    recommended_department = models.ForeignKey(Department, on_delete=models.PROTECT,
                                               related_name="recommendations")
    confidence = models.DecimalField(max_digits=4, decimal_places=3,
                                     validators=[MinValueValidator(0), MaxValueValidator(1)])
    top3 = models.JSONField(default=list)
    input_snapshot = models.JSONField(default=dict)
    model_version = models.CharField(max_length=60)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "specialization_recommendation"
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(condition=Q(confidence__gte=0, confidence__lte=1),
                                   name="ck_reco_confidence_range"),
            models.CheckConstraint(condition=~Q(model_version=""), name="ck_reco_model_version_set"),
        ]
        indexes = [models.Index(fields=["student", "-created_at"], name="ix_reco_student_recent")]


class Notification(models.Model):
    class Type(models.TextChoices):
        SEVENTH_APPROVED = "seventh_approved", "7th course approved"
        SEVENTH_REJECTED = "seventh_rejected", "7th course rejected"
        SUMMER_OPENED = "summer_opened", "Summer course opened"
        SUMMER_REJECTED = "summer_rejected", "Summer request rejected"
        DEPARTMENT_CHANGED = "department_changed", "Department changed"
        SYSTEM = "system", "System"

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="notifications")
    type = models.CharField(max_length=20, choices=Type.choices, default=Type.SYSTEM)
    text = models.CharField(max_length=500)
    text_ar = models.CharField(max_length=500, blank=True, default="")
    link = models.CharField(max_length=200, blank=True, default="")   # frontend route
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "notification"
        ordering = ["-created_at"]
        constraints = [enum_check("notification", "type", NotificationType)]
        indexes = [models.Index(fields=["student", "is_read", "-created_at"], name="ix_notif_student_unread")]
