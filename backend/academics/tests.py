from datetime import datetime
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APITestCase

from academics import bylaw_data, services
from academics.models import (
    Course,
    CourseOffering,
    Department,
    Enrollment,
    Notification,
    SavedGraduationPlan,
    Semester,
    SeventhCourseRequest,
    Student,
    StudentCoursePreference,
    StudentSemesterRecord,
)
from academics.pathfinder_adapter import (
    build_pathfinder_inputs,
    is_course_compulsory_for_student,
    recalculate_student_plan,
)

User = get_user_model()


class BylawDataTests(TestCase):
    def test_bylaw_data_is_consistent(self):
        bylaw_data.validate()


class SeedTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        with patch.dict("os.environ", {"MASAR_DEMO_PASSWORD": "TestOnly-Password-123!"}):
            call_command("seed_data", verbosity=0)

    @staticmethod
    def student(uid):
        return Student.objects.get(university_id=uid)

    @staticmethod
    def offering(code):
        return CourseOffering.objects.get(
            course__code=code,
            semester=services.current_semester(),
        )

    def test_check_seed_passes(self):
        call_command("check_seed", verbosity=0)

    def test_seed_is_idempotent(self):
        before = (
            Course.objects.count(),
            Enrollment.objects.count(),
            StudentSemesterRecord.objects.count(),
        )
        call_command("seed_data", verbosity=0)
        self.assertEqual(
            before,
            (
                Course.objects.count(),
                Enrollment.objects.count(),
                StudentSemesterRecord.objects.count(),
            ),
        )

    def test_retake_counts_only_latest_attempt(self):
        s = self.student("20230005")
        it111 = Course.objects.get(code="IT111")
        self.assertEqual(
            services.counted_attempts(s)[it111.id].status,
            "completed",
        )
        self.assertEqual(
            Enrollment.objects.filter(
                student=s,
                offering__course=it111,
            ).count(),
            2,
        )

    def test_failed_prerequisite_blocks_registration(self):
        s = self.student("20230004")
        self.assertEqual(
            services.counted_attempts(s)[
                Course.objects.get(code="CS214").id
            ].status,
            "failed",
        )
        self.assertIn(
            "prerequisites_not_met",
            services.can_register(s, self.offering("CS316")),
        )

    def test_passed_course_cannot_be_retaken(self):
        s = self.student("20230003")
        self.assertIn(
            "already_passed",
            services.can_register(s, self.offering("CS214")),
        )

    def test_levels_and_snapshots(self):
        self.assertEqual(self.student("20230006").academic_level, 4)
        self.assertEqual(self.student("20250002").academic_level, 1)
        self.assertEqual(
            StudentSemesterRecord.objects.filter(
                student__university_id="20230003"
            ).count(),
            5,
        )

    def test_seventh_course_eligibility(self):
        sem = services.current_semester()

        ok, reasons = services.seventh_course_eligibility(
            self.student("20240008"),
            sem,
        )
        self.assertFalse(ok)
        self.assertIn("cgpa_below_minimum", reasons)

        ok, reasons = services.seventh_course_eligibility(
            self.student("20240007"),
            sem,
        )
        self.assertEqual(reasons, ["pending_request_exists"])

    def test_approve_seventh_request_creates_enrollment(self):
        student = self.student("20230006")
        offering = self.offering("HU323")

        offering.time_slots.all().delete()

        request, _ = SeventhCourseRequest.objects.get_or_create(
            student=student,
            offering=offering,
            defaults={
                "reason": "Testing seventh-course approval."
            },
        )

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
        from academics.models import SummerRequest

        summer = Semester.objects.get(term="summer")
        admin = Student.objects.first().user.__class__.objects.get(
            username="demo_admin"
        )

        _, n = services.open_summer_offering(
            Course.objects.get(code="IS321"),
            summer,
            admin,
        )

        self.assertEqual(n, 2)
        self.assertEqual(
            SummerRequest.objects.filter(
                status="approved",
                fulfilled_by_offering__isnull=False,
            ).count(),
            2,
        )

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

    def test_saved_graduation_plan_defaults(self):
        student = self.student("20230006")
        SavedGraduationPlan.objects.filter(student=student).delete()
        plan = SavedGraduationPlan.objects.create(student=student)

        self.assertEqual(plan.plan_data, {})
        self.assertEqual(plan.projected_graduation_term, "")
        self.assertTrue(plan.is_stale)
        self.assertIsNotNone(plan.updated_at)

    def test_mark_plan_stale(self):
        student = self.student("20230006")
        plan, _ = SavedGraduationPlan.objects.update_or_create(
            student=student,
            defaults={
                "plan_data": {"courses": ["CS111"]},
                "is_stale": False,
            },
        )

        services.mark_plan_stale(student)

        plan.refresh_from_db()
        self.assertTrue(plan.is_stale)
        self.assertIsNotNone(plan.updated_at)

    def test_pathfinder_adapter_dual_run_and_stability_gate(self):
        student = self.student("20240007")
        inputs = build_pathfinder_inputs(student)

        self.assertIn("student", inputs)
        self.assertIn("settings", inputs)
        self.assertIn("starting_term", inputs)
        self.assertIn("elective_hours_remaining", inputs)
        self.assertIn("courses", inputs)

        plan = recalculate_student_plan(student)
        self.assertFalse(plan.is_stale)
        self.assertIn("semesters", plan.plan_data)
        self.assertIn("baseline_semesters", plan.plan_data)
        self.assertIn("estimated_semesters", plan.plan_data)
        self.assertTrue(plan.projected_graduation_term)

        # Re-running with identical valid state preserves semester layout via Stability Gate
        original_semesters = plan.plan_data["semesters"]
        plan_rerun = recalculate_student_plan(student)
        self.assertEqual(plan_rerun.plan_data["semesters"], original_semesters)

        # Avoiding a scheduled elective invalidates the Stability Gate and replans without it
        scheduled_elective_code = next(
            (
                c["code"]
                for sem in original_semesters
                for c in sem["courses"]
                if c["category"] == "elective"
            ),
            None,
        )
        if scheduled_elective_code:
            elective_course = Course.objects.get(code=scheduled_elective_code)
            StudentCoursePreference.objects.update_or_create(
                student=student,
                course=elective_course,
                defaults={"kind": StudentCoursePreference.Kind.AVOID},
            )
            plan_after_avoid = recalculate_student_plan(student)
            new_codes = {
                c["code"]
                for sem in plan_after_avoid.plan_data["semesters"]
                for c in sem["courses"]
            }
            self.assertNotIn(scheduled_elective_code, new_codes)


class StudentViewTests(APITestCase):
    def setUp(self):
        self.semester = Semester.objects.create(
            academic_year=2026,
            term="fall",
            start_date="2026-09-01",
            end_date="2027-01-15",
            registration_deadline=timezone.make_aware(datetime(2026, 9, 15, 0, 0)),
            is_current=True,
        )

        self.user = User.objects.create_user(
            username="2024123456",
            password="testpassword",
        )

        self.student = Student.objects.create(
            user=self.user,
            university_id="2024123456",
            admission_semester=self.semester,
        )

        self.dept = Department.objects.create(
            code="CS",
            name="Computer Science",
            is_active=True,
        )

        self.course = Course.objects.create(
            code="CS112",
            name="Programming 1",
            credit_hours=3,
            requirement_group="faculty",
            requirement_type="compulsory",
            min_level=1,
            is_active=True,
        )

        self.elective_course = Course.objects.create(
            code="HU399",
            name="Selected Topics in Humanities",
            credit_hours=3,
            requirement_group="general",
            requirement_type="elective",
            min_level=1,
            is_active=True,
        )

        self.client.force_authenticate(user=self.user)

    def test_get_specialization_tree_success(self):
        response = self.client.get("/api/specializations/CS/tree/")
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.data, list)

    def test_get_course_details_success(self):
        response = self.client.get("/api/courses/CS112/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["code"], "CS112")

    def test_update_specialization_success(self):
        response = self.client.put(
            "/api/me/specialization/",
            {"department_code": "CS"},
        )
        self.assertEqual(response.status_code, 200)

        self.student.refresh_from_db()
        self.assertEqual(self.student.department, self.dept)
        self.assertTrue(
            SavedGraduationPlan.objects.filter(
                student=self.student,
                is_stale=False,
            ).exists()
        )

    def test_preferences_compulsory_avoid_guardrail_and_recalculation(self):
        self.assertTrue(is_course_compulsory_for_student(self.student, self.course))
        self.assertFalse(is_course_compulsory_for_student(self.student, self.elective_course))

        # Compulsory course in avoid list must be rejected with 400
        bad_resp = self.client.put(
            "/api/me/preferences/",
            [{"course_code": "CS112", "kind": "avoid"}],
            format="json",
        )
        self.assertEqual(bad_resp.status_code, 400)

        # Valid elective preference succeeds and updates SavedGraduationPlan
        ok_resp = self.client.put(
            "/api/me/preferences/",
            [{"course_code": "HU399", "kind": "want"}],
            format="json",
        )
        self.assertEqual(ok_resp.status_code, 200)
        self.assertTrue(
            StudentCoursePreference.objects.filter(
                student=self.student,
                course=self.elective_course,
                kind=StudentCoursePreference.Kind.WANT,
            ).exists()
        )
        self.assertTrue(
            SavedGraduationPlan.objects.filter(
                student=self.student,
                is_stale=False,
            ).exists()
        )

        # GET returns saved preferences
        get_resp = self.client.get("/api/me/preferences/")
        self.assertEqual(get_resp.status_code, 200)
        self.assertEqual(len(get_resp.data), 1)
        self.assertEqual(get_resp.data[0]["course_code"], "HU399")

    def test_unauthenticated_access_is_blocked(self):
        self.client.force_authenticate(user=None)

        response = self.client.get("/api/specializations/CS/tree/")
        self.assertEqual(response.status_code, 401)