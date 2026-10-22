from django.core.management import call_command
from django.test import TestCase

from academics import bylaw_data, services
from academics.models import (Course, CourseOffering, Enrollment, SeventhCourseRequest, Student,
                              StudentSemesterRecord)
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase

from academics import bylaw_data, services
from academics.models import (
    Course,
    CourseOffering,
    Enrollment,
    Notification,
    SeventhCourseRequest,
    Student,
    StudentSemesterRecord,
)

User = get_user_model()

class BylawDataTests(TestCase):
    def test_bylaw_data_is_consistent(self):
        bylaw_data.validate()


class SeedTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_data", verbosity=0)

    @staticmethod
    def student(uid):
        return Student.objects.get(university_id=uid)

    @staticmethod
    def offering(code):
        return CourseOffering.objects.get(course__code=code, semester=services.current_semester())

    def test_check_seed_passes(self):
        call_command("check_seed", verbosity=0)

    def test_seed_is_idempotent(self):
        before = (Course.objects.count(), Enrollment.objects.count(), StudentSemesterRecord.objects.count())
        call_command("seed_data", verbosity=0)
        self.assertEqual(before, (Course.objects.count(), Enrollment.objects.count(),
                                  StudentSemesterRecord.objects.count()))

    def test_retake_counts_only_latest_attempt(self):
        s = self.student("20230005")                    # failed IT111, passed the retake
        it111 = Course.objects.get(code="IT111")
        self.assertEqual(services.counted_attempts(s)[it111.id].status, "completed")
        self.assertEqual(Enrollment.objects.filter(student=s, offering__course=it111).count(), 2)

    def test_failed_prerequisite_blocks_registration(self):
        s = self.student("20230004")                    # failed CS214, never retook it
        self.assertEqual(services.counted_attempts(s)[Course.objects.get(code="CS214").id].status, "failed")
        self.assertIn("prerequisites_not_met", services.can_register(s, self.offering("CS316")))

    def test_passed_course_cannot_be_retaken(self):
        s = self.student("20230003")
        self.assertIn("already_passed", services.can_register(s, self.offering("CS214")))

    def test_levels_and_snapshots(self):
        self.assertEqual(self.student("20230006").academic_level, 4)
        self.assertEqual(self.student("20250002").academic_level, 1)
        self.assertEqual(StudentSemesterRecord.objects.filter(student__university_id="20230003").count(), 5)

    def test_seventh_course_eligibility(self):
        sem = services.current_semester()
        ok, reasons = services.seventh_course_eligibility(self.student("20240008"), sem)
        self.assertFalse(ok)
        self.assertIn("cgpa_below_minimum", reasons)
        ok, reasons = services.seventh_course_eligibility(self.student("20240007"), sem)
        self.assertEqual(reasons, ["pending_request_exists"])   # CGPA qualifies; request already pending

    def test_approve_seventh_request_creates_enrollment(self):
        # Use a seeded student whose level is suitable for HU323.
        student = self.student("20230006")
        offering = self.offering("HU323")

        # Remove only this offering's time slots in the isolated test DB
        # so unrelated schedule conflicts do not affect this service test.
        offering.time_slots.all().delete()

        # Create a request for this student in the test database.
        request, _ = SeventhCourseRequest.objects.get_or_create(
            student=student,
            offering=offering,
            defaults={
                "reason": "Testing seventh-course approval."
            },
        )

        # Ensure the request is pending for this test.
        request.status = SeventhCourseRequest._meta.get_field(
            "status"
        ).default
        request.decided_by = None
        request.decided_at = None
        request.decision_reason = ""
        request.save()

        admin = User.objects.get(username="demo_admin")

        services.approve_seventh_request(request, admin)

        self.assertTrue(
            Enrollment.objects.filter(
                student=student,
                offering=offering,
                status=Enrollment.Status.REGISTERED,
            ).exists()
        )

        self.assertTrue(
            Notification.objects.filter(
                student=student,
                type=Notification.Type.SEVENTH_APPROVED,
            ).exists()
        )

        request.refresh_from_db()
        self.assertEqual(request.status, "approved")
        self.assertEqual(request.decided_by, admin)
        self.assertIsNotNone(request.decided_at)


    def test_open_summer_offering_links_requests(self):
        from academics.models import Semester, SummerRequest
        summer = Semester.objects.get(term="summer")
        admin = Student.objects.first().user.__class__.objects.get(username="demo_admin")
        _, n = services.open_summer_offering(Course.objects.get(code="IS321"), summer, admin)
        self.assertEqual(n, 2)
        self.assertEqual(SummerRequest.objects.filter(status="approved", fulfilled_by_offering__isnull=False).count(), 2)



    def test_debug_seventh_course_candidates(self):
        student = self.student("20240007")
        sem = services.current_semester()

        print("\n--- SEVENTH COURSE CANDIDATES ---")
        print("Student level:", student.academic_level)

        offerings = (
            CourseOffering.objects.filter(
                semester=sem,
                status=CourseOffering.Status.OPEN,
                course__min_level__lte=student.academic_level,
            )
            .select_related("course", "semester")
            .order_by("course__code")
        )

        for offering in offerings:
            reasons = services.can_register(
                student,
                offering,
                admin_override=True,
            )

            print(
                offering.course.code,
                "| min_level:", offering.course.min_level,
                "| reasons:", reasons,
            )

            target = CourseOffering.objects.get(
            semester=sem,
            course__code="HU323",
        )

        print("\n--- HU323 FULL CHECK ---")
        print("Student level:", student.academic_level)
        print("Course min_level:", target.course.min_level)
        print(
            "Registration reasons:",
            services.can_register(
                student,
                target,
                admin_override=True,
            ),
        )
        print("--- END HU323 FULL CHECK ---\n")

        print("--- END CANDIDATES ---\n")