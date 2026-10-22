"""
python manage.py seed_data            # safe to re-run (update_or_create / get_or_create)
python manage.py seed_data --reset    # wipe seeded tables + demo users, then seed again
python manage.py seed_data --no-demo  # catalog + semesters + instructors + offerings only

Order: catalog -> semesters/instructors/current offerings -> demo students -> close past semesters.
Demo history is written DIRECTLY (it does not go through can_register); then
services.close_semester builds the StudentSemesterRecord rows and the levels.
"""
from datetime import date, datetime, time, timedelta
import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.utils import timezone
from academics import bylaw_data as data
from academics import services
from academics.models import (
    Course, CourseOffering, CoursePrerequisite, CreditLimitRule, DegreeRequirement, Department,
    DepartmentCourse, Enrollment, GradeScale, Instructor, LevelThreshold, Notification,
    OfferingTimeSlot, Semester, SeventhCourseRequest, SpecializationRecommendation, Student,
    StudentCoursePreference, StudentDepartmentChange, StudentSemesterRecord, SummerRequest,
    SystemSetting,
)
User = get_user_model()
PASSWORD = os.environ.get("MASAR_DEMO_PASSWORD")
ADMIN_USERNAME = "demo_admin"

# (start year of the academic year, term). 0-5 past, 6 current, 7 = summer to open.
SEMS = [(2023, "fall"), (2023, "spring"), (2024, "fall"), (2024, "spring"),
        (2025, "fall"), (2025, "spring"), (2026, "fall"), (2026, "summer")]
CURRENT_IDX, SUMMER_IDX = 6, 7

# PLACEHOLDER scale (common Egyptian 4.0 scale) - replace with the faculty's official table.
# (letter, quality_points, min_score, max_score, is_passing)
GRADE_SCALE = [("A+", "4.00", "97.00", "100.00", True), ("A", "4.00", "93.00", "96.99", True),
               ("A-", "3.70", "89.00", "92.99", True), ("B+", "3.30", "84.00", "88.99", True),
               ("B", "3.00", "80.00", "83.99", True), ("B-", "2.70", "76.00", "79.99", True),
               ("C+", "2.30", "73.00", "75.99", True), ("C", "2.00", "70.00", "72.99", True),
               ("C-", "1.70", "67.00", "69.99", True), ("D+", "1.30", "64.00", "66.99", True),
               ("D", "1.00", "60.00", "63.99", True), ("F", "0.00", "0.00", "59.99", False)]

SETTINGS = {  # key: (value, description)   - PLACEHOLDER values need the faculty's answer
    "TOTAL_GRADUATION_HOURS": ("144", "Credit hours required to graduate"),
    "PROBATION_CGPA": ("2.0", "Below this CGPA the student is on probation"),
    "GRADUATION_MIN_CGPA": ("2.0", "Minimum CGPA to graduate"),
    "MAX_COURSES_PER_SEMESTER": ("6", "Normal course limit per semester"),
    "SEVENTH_COURSE_MIN_CGPA": ("3.00", "PLACEHOLDER: minimum CGPA to request a 7th course"),
    "SUMMER_MAX_CREDITS": ("9", "PLACEHOLDER: credit cap in the summer semester"),
    "NEW_STUDENT_MAX_CREDITS": ("18", "PLACEHOLDER: credit cap when the student has no CGPA yet"),
}
CREDIT_LIMITS = [(None, "2.00", 12), ("2.00", "3.00", 18), ("3.00", None, 21)]   # PLACEHOLDER bands
LEVELS = [(1, 0, "سنة أولى"), (2, 36, "سنة ثانية"), (3, 72, "سنة ثالثة"), (4, 108, "سنة رابعة")]

INSTRUCTORS = [("Dr. Ahmed Hassan", "د. أحمد حسن"), ("Dr. Mona Fathy", "د. منى فتحي"),
               ("Dr. Khaled Samir", "د. خالد سمير"), ("Dr. Heba Mostafa", "د. هبة مصطفى"),
               ("Dr. Tarek Nabil", "د. طارق نبيل"), ("Dr. Sara Adel", "د. سارة عادل"),
               ("Dr. Omar Farouk", "د. عمر فاروق"), ("Dr. Dina Ibrahim", "د. دينا إبراهيم")]

PERIODS = [(time(8, 30), time(10, 0)), (time(10, 15), time(11, 45)),
           (time(12, 0), time(13, 30)), (time(13, 45), time(15, 15))]

PROFILE_SCORES = {"high": [96, 92, 94, 90, 95, 93], "mid": [84, 78, 88, 75, 81, 72],
                  "low": [71, 70, 72, 73, 70, 71]}

# Current-semester offerings. Order matters: one student's courses sit within 12 consecutive
# positions, so the slot grid below never makes two of his courses overlap.
CURRENT_OFFERINGS = (
    "CS316 IS351 HU213 IT241 CS313 HU331  MA111 CS111 PH111 HU111 HU112  "
    "AI460 AI498 AI457 IT443 CS416  MA113 ST122 HU122  "
    "HU313 CS342 IT342 IT444 HU323 CS214 IS321").split()

H1 = "HU111 HU112 MA111 CS111 PH111 IT111 ST121"
H2 = "MA112 MA113 CS112 HU121 HU122 ST122"
H3 = "CS213 CS214 CS221 IS231 IT221 IS240"
H4 = "CS241 CS251 IS211 IT222 IT223 IT211"

DEMO = [
    dict(username="demo_new", uid="20260001", first="Student One", last="(New L1)", name_ar="طالب جديد",
         admitted=6, dept=None, profile="mid", history={},
         current="MA111 CS111 PH111 HU111 HU112", summer="MA112", prefs=[], notes=[]),
    dict(username="demo_l1_continuing", uid="20250002", first="Student Two", last="(L1 Continuing)",
         name_ar="طالب سنة أولى مستمر", admitted=4, dept=None, profile="mid",
         history={4: "HU111 HU112 MA111 CS111 PH111 IT111", 5: "MA112 MA113 CS112 ST121 HU121"},
         overrides={(5, "MA113"): 45}, current="MA113 ST122 HU122", summer="CS213", prefs=[], notes=[]),
    dict(username="demo_ai_features", uid="20230003", first="Student Three", last="(AI features)",
         name_ar="طالب للذكاء الاصطناعي", admitted=0, dept=None, profile="high",
         history={0: H1, 1: H2, 2: H3, 3: H4, 4: "CS316 IS351"},
         current="HU313 HU331", summer="CS313",
         prefs=[("AI330", "want"), ("CS405", "avoid")], notes=[], reco=True),
    dict(username="demo_failed_prereq", uid="20230004", first="Student Four", last="(Failed CS214)",
         name_ar="طالب راسب في هياكل البيانات", admitted=0, dept="CS", change_at=4, profile="mid",
         history={0: H1, 1: "MA112 MA113 CS112 HU121 ST122 HU122",
                  2: "CS213 CS214 CS221 IS231 IT221 HU213",
                  3: "CS241 CS251 IS211 IT222 IT223 IT241",
                  4: "IS351 HU313 CS322 IS240", 5: "CS352 AI330 IT331"},
         overrides={(2, "CS214"): 40}, current="CS342", summer="CS313",
         prefs=[("CS460", "avoid")], notes=[]),
    dict(username="demo_retake_passed", uid="20230005", first="Student Five", last="(Retake passed)",
         name_ar="طالب أعاد مادة ونجح", admitted=0, dept="IT", change_at=4, profile="mid",
         history={0: H1, 1: "MA112 MA113 CS112 IT111 ST122 HU121", 2: H3,
                  3: "CS241 CS251 IS211 IT222 IT223 HU122",
                  4: "CS316 IS351 IT311 IT321 IT322 HU313", 5: "IT331 IT341 IT433 IT312"},
         overrides={(0, "IT111"): 38}, current="IT342 IT444", summer="IT411", prefs=[], notes=[]),
    dict(username="demo_near_graduation", uid="20230006", first="Student Six", last="(Level 4)",
         name_ar="طالب سنة رابعة", admitted=0, dept="AI", change_at=2, profile="high",
         history={0: H1, 1: H2, 2: H3 + " HU213", 3: "CS241 CS251 IS211 IT222 IT223 IT241 CS316",
                  4: "IS351 AI310 AI320 AI330 IT441 IS365 HU313",
                  5: "AI335 AI360 AI370 AI420 AI430 AI350 AI380"},
         current="AI460 AI498 AI457 IT443 CS416", summer="AI490", prefs=[("IT312", "want")], notes=[]),
    dict(username="demo_seventh_eligible", uid="20240007", first="Student Seven", last="(7th eligible)",
         name_ar="طالب مؤهل للمادة السابعة", admitted=2, dept=None, profile="high",
         history={2: "HU111 HU112 MA111 CS111 PH111 ST121", 3: "MA112 MA113 CS112 HU121 IT111 ST122",
                  4: H3, 5: "CS241 CS251 IS211 IT222 IT223 HU122"},
         current="CS316 IS351 HU213 IT241 CS313 HU331", summer="IS321", prefs=[],
         seventh="HU323",
         notes=[("system", "7th course request received", "تم استلام طلب المادة السابعة",
                 "Your request is waiting for the admin.", "طلبك في انتظار الإدارة.", "/seventh-request")]),
    dict(username="demo_seventh_ineligible", uid="20240008", first="Student Eight", last="(7th not eligible)",
         name_ar="طالب غير مؤهل للمادة السابعة", admitted=2, dept=None, profile="low",
         history={2: "HU111 HU112 MA111 CS111 PH111 ST121", 3: "MA112 MA113 CS112 HU121 IT111 ST122",
                  4: H3, 5: "CS241 CS251 IS211 IT222 IT223 HU122"},
         current="CS316 IS351 HU213 IT241 CS313 HU331", summer="IS321", prefs=[], notes=[]),
]


class Command(BaseCommand):

    help = "Seed the Masar catalog, semesters, offerings and demo students."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="wipe seeded data first")
        parser.add_argument("--no-demo", action="store_true", help="skip demo students")

    @transaction.atomic
    def handle(self, *args, **opts):
        if not PASSWORD:
            raise CommandError(
                "Set MASAR_DEMO_PASSWORD before running seed_data."
            )

        info = data.validate()

        if opts["reset"]:
            self.reset()

        self.seed_catalog()
        self.seed_time()

        if not opts["no_demo"]:
            self.seed_demo()

        self.stdout.write(
            self.style.SUCCESS(
                f"Seed done. courses={Course.objects.count()} "
                f"prerequisites={CoursePrerequisite.objects.count()} "
                f"(expected {info['courses']}/{info['prerequisite_rows']}) "
                f"students={Student.objects.count()} "
                f"offerings={CourseOffering.objects.count()}"
            )
        )
    # ------------------------------------------------------------------ reset ---------
    def reset(self):
        with connection.cursor() as cur:   # allow deleting frozen snapshots (see db_rules.sql)
            cur.execute("SET LOCAL masar.allow_snapshot_edit = 'on'")
        user_ids = list(Student.objects.values_list("user_id", flat=True))
        user_ids += list(User.objects.filter(username=ADMIN_USERNAME).values_list("id", flat=True))
        for model in [Notification, SpecializationRecommendation, SeventhCourseRequest, SummerRequest,
                      StudentCoursePreference, StudentDepartmentChange, StudentSemesterRecord,
                      Enrollment, OfferingTimeSlot, CourseOffering, Student, CoursePrerequisite,
                      DepartmentCourse, DegreeRequirement, Course, Department, Semester,
                      Instructor, GradeScale, LevelThreshold, CreditLimitRule, SystemSetting]:
            model.objects.all().delete()
        User.objects.filter(id__in=user_ids).delete()
        self.stdout.write("Reset done.")

    # ------------------------------------------------------------------ catalog -------

    def seed_catalog(self):
        depts = {}
        for code, (name_en, name_ar) in data.DEPARTMENTS.items():
            depts[code], _ = Department.objects.update_or_create(
                code=code,
                defaults={"name": name_en, "name_ar": name_ar},
            )

        def req(scope, dept, type_, hours):
            DegreeRequirement.objects.update_or_create(
                scope=scope,
                department=dept,
                type=type_,
                defaults={"required_hours": hours},
            )

        req("general", None, "compulsory", 6)
        req("general", None, "elective", 6)
        req("faculty", None, "compulsory", 63)
        req("faculty", None, "elective", 9)

        for dept in depts.values():
            req("department", dept, "compulsory", 39)
            req("department", dept, "elective", 21)

        for level, hours, _label in LEVELS:
            LevelThreshold.objects.update_or_create(
                level=level,
                defaults={"min_earned_hours": hours},
            )

        for key, (value, desc) in SETTINGS.items():
            SystemSetting.objects.get_or_create(
                key=key,
                defaults={"value": value, "description": desc},
            )

        for letter, pts, lo, _hi, passing in GRADE_SCALE:
            GradeScale.objects.update_or_create(
                letter=letter,
                defaults={
                    "points": pts,
                    "min_score": lo,
                    "is_passing": passing,
                },
            )

        if not CreditLimitRule.objects.exists():
            for lo, hi, mx in CREDIT_LIMITS:
                CreditLimitRule.objects.create(
                    min_cgpa=lo,
                    max_cgpa=hi,
                    max_credits=mx,
                )

        courses = {}
        for code, d in data.all_courses().items():
            courses[code], _ = Course.objects.update_or_create(
                code=code,
                defaults={
                    "name": d["name"],
                    "credit_hours": d["credits"],
                    "requirement_group": d["group"],
                    "requirement_type": d["type"],
                    "min_level": d["min_level"],
                    "typical_term": Course.Term.BOTH,
                    "is_active": True,
                },
            )

        for dept_code, dept in depts.items():
            for type_, codes in (
                ("compulsory", data.DEPT_COMPULSORY[dept_code]),
                ("elective", data.DEPT_ELECTIVE[dept_code]),
            ):
                for code in codes:
                    DepartmentCourse.objects.update_or_create(
                        department=dept,
                        course=courses[code],
                        defaults={"type": type_},
                    )

        for course_code, groups in data.parse_prereqs().items():
            for n, group in enumerate(groups, start=1):
                for pre in group:
                    CoursePrerequisite.objects.update_or_create(
                        course=courses[course_code],
                        prerequisite=courses[pre],
                        group=n,
                    )

    # ------------------------------------------------------------------ time ----------
    @staticmethod
    def _aware(d, t=time(23, 59)):
        return timezone.make_aware(datetime.combine(d, t))

    def seed_time(self):
        now = timezone.now()
        for i, (year, term) in enumerate(SEMS):
            if term == "fall":
                start, end = date(year, 9, 20), date(year + 1, 1, 14)
            elif term == "spring":
                start, end = date(year + 1, 2, 14), date(year + 1, 6, 15)
            else:
                start, end = date(year + 1, 7, 1), date(year + 1, 8, 15)
            deadline = (now + timedelta(days=14) if i == CURRENT_IDX
                        else self._aware(start - timedelta(days=7)) if i == SUMMER_IDX
                        else self._aware(start + timedelta(days=14)))
            Semester.objects.update_or_create(
                academic_year=year, term=term, defaults=dict(
                    start_date=start, end_date=end, registration_deadline=deadline,
                    is_current=(i == CURRENT_IDX)))
        for name_en, name_ar in INSTRUCTORS:
            email = name_en.lower().replace("dr. ", "").replace(" ", ".") + "@faculty.example.edu"
            Instructor.objects.update_or_create(email=email, defaults=dict(name=name_en, name_ar=name_ar))
        self.seed_current_offerings()

    def sem(self, idx):
        year, term = SEMS[idx]
        return Semester.objects.get(academic_year=year, term=term)

    def seed_current_offerings(self):
        sem, instructors = self.sem(CURRENT_IDX), list(Instructor.objects.order_by("id"))
        first_days = ["sat", "sun", "mon"]
        second_days = ["tue", "wed", "thu"]
        for i, code in enumerate(CURRENT_OFFERINGS):
            off, _ = CourseOffering.objects.update_or_create(
                course=Course.objects.get(code=code), semester=sem,
                defaults=dict(status="open", instructor=instructors[i % len(instructors)]))
            for day, period in ((first_days[i % 3], (i // 3) % 4), (second_days[i % 3], (i // 3 + 2) % 4)):
                start, end = PERIODS[period]
                OfferingTimeSlot.objects.update_or_create(
                    offering=off, day=day, start_time=start, defaults=dict(end_time=end))

    # ------------------------------------------------------------------ demo ----------
    def grade_for(self, score):
        return GradeScale.objects.filter(min_score__lte=score).order_by("-min_score").first()

    def past_offering(self, code, sem_idx):
        instructors = list(Instructor.objects.order_by("id"))
        off, _ = CourseOffering.objects.get_or_create(
            course=Course.objects.get(code=code), semester=self.sem(sem_idx),
            defaults=dict(status="closed", instructor=instructors[(len(code) + sem_idx) % len(instructors)]))
        return off

    def seed_demo(self):
        admin, _ = User.objects.get_or_create(username=ADMIN_USERNAME, defaults=dict(
            is_staff=True, is_superuser=True, email="admin@masar.example.edu"))
        admin.set_password(PASSWORD)
        admin.save()
        summer = self.sem(SUMMER_IDX)
        for spec in DEMO:
            user, _ = User.objects.get_or_create(
                username=spec["username"],
                defaults={
                    "email": f"{spec['username']}@masar.example.edu",
                },
            )
            user.set_password(PASSWORD)
            user.save()

            department = (
                Department.objects.get(code=spec["dept"])
                if spec["dept"]
                else None
            )

            student, _ = Student.objects.update_or_create(
                university_id=spec["uid"],
                defaults={
                    "user": user,
                    "full_name": f"{spec['first']} {spec['last']}",
                    "full_name_ar": spec["name_ar"],
                    "department": department,
                    "admission_semester": self.sem(spec["admitted"]),
                    "status": "active",
                },
            )
            user.set_password(PASSWORD)
            user.save()
            department = Department.objects.get(code=spec["dept"]) if spec["dept"] else None
            student, _ = Student.objects.update_or_create(university_id=spec["uid"], defaults=dict(
                user=user, full_name_ar=spec["name_ar"], department=department,
                admission_semester=self.sem(spec["admitted"]), status="active"))
            if department is not None:
                StudentDepartmentChange.objects.get_or_create(
                    student=student, from_department=None, to_department=department,
                    semester=self.sem(spec["change_at"]))
            scores = PROFILE_SCORES[spec["profile"]]
            for sem_idx, codes in spec["history"].items():
                sem = self.sem(sem_idx)
                for n, code in enumerate(codes.split()):
                    score = spec.get("overrides", {}).get((sem_idx, code), scores[n % len(scores)])
                    gs = self.grade_for(score)
                    Enrollment.objects.get_or_create(
                        student=student, offering=self.past_offering(code, sem_idx), defaults=dict(
                            status="completed" if gs.is_passing else "failed", score=score,
                            grade_letter=gs.letter,grade_points=gs.points,graded_by=admin, graded_at=self._aware(sem.end_date + timedelta(days=5))))
            cur = self.sem(CURRENT_IDX)
            for code in spec["current"].split():
                Enrollment.objects.get_or_create(
                    student=student, offering=CourseOffering.objects.get(course__code=code, semester=cur),
                    defaults=dict(status="registered"))
            SummerRequest.objects.get_or_create(
                student=student, course=Course.objects.get(code=spec["summer"]), semester=summer)
            for code, kind in spec["prefs"]:
                StudentCoursePreference.objects.get_or_create(
                    student=student, course=Course.objects.get(code=code), defaults=dict(kind=kind))
            if spec.get("seventh"):
                SeventhCourseRequest.objects.get_or_create(
                    student=student,
                    offering=CourseOffering.objects.get(course__code=spec["seventh"], semester=cur),
                    defaults=dict(reason="I need this course to graduate on time."))
            if not student.notifications.exists():
                Notification.objects.create(
                                student=student,
                                type="system",
                                text="Welcome to Masar. Explore your curriculum tree and plan your path.",
                                text_ar="مرحبًا بك في مسار. استكشف شجرة المقررات وخطط لمسارك.",
                                link="/dashboard",
                                is_read=True,
                            )
                for type_, t_en, t_ar, m_en, m_ar, link in spec["notes"]:
                    Notification.objects.create(
                                student=student,
                                type=type_,
                                text=f"{t_en}: {m_en}",
                                text_ar=f"{t_ar}: {m_ar}",
                                link=link,
                            )
                if department is not None:
                    Notification.objects.create(
    student=student,
    type="system",
    text=f"Department selected: {department.code}.",
    text_ar=f"تم اختيار القسم: {department.code}.",
    link="/graduation-path",
)
                if not spec["notes"] and department is None:
                    Notification.objects.create(
                        student=student, type="system", text="Registration closes soon.",
                        text_ar="التسجيل سيغلق قريبًا", link="/curriculum")
            if spec.get("reco") and not student.recommendations.exists():
                snap, counted = {}, services.counted_attempts(student)
                for code in data.AI_FEATURE_COURSES:
                    e = counted.get(Course.objects.get(code=code).id)
                    snap[code] = float(e.score) if e and e.score is not None else None
                SpecializationRecommendation.objects.create(
    student=student,
    recommended_department=Department.objects.get(code="AI"),
    confidence="0.820",
    model_version="seed-demo-0",
    input_snapshot=snap,
    top3=[
        {"code": "AI", "p": 0.82},
        {"code": "CS", "p": 0.11},
        {"code": "IS", "p": 0.05},
    ],
)

            # Freeze the six past semesters (also writes Student.academic_level).
        # Freeze the six past semesters (also writes Student.academic_level).
        for idx in range(CURRENT_IDX):
            sem = self.sem(idx)
            if not sem.is_closed:
                services.close_semester(sem)
