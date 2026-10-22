
"""Verify that the seeded catalog satisfies the bylaw rules."""

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Sum

from academics import bylaw_data as data
from academics.models import (
    Course,
    CoursePrerequisite,
    DegreeRequirement,
    Department,
    DepartmentCourse,
)


class Command(BaseCommand):
    help = "Verify the seeded catalog against the bylaw."

    def handle(self, *args, **opts):
        errors = []

        def check(ok, message):
            self.stdout.write(("  OK   " if ok else "  FAIL ") + message)
            if not ok:
                errors.append(message)

        def hours(**filters):
            return (
                Course.objects.filter(**filters).aggregate(
                    total=Sum("credit_hours")
                )["total"]
                or 0
            )

        check(
            hours(
                requirement_group="general",
                requirement_type="compulsory",
            ) == 6,
            "general compulsory = 6 h",
        )

        check(
            hours(
                requirement_group="faculty",
                requirement_type="compulsory",
            ) == 63,
            "faculty compulsory = 63 h",
        )

        for department in Department.objects.all():
            courses = DepartmentCourse.objects.filter(
                department=department
            )

            compulsory = (
                courses.filter(type="compulsory").aggregate(
                    total=Sum("course__credit_hours")
                )["total"]
                or 0
            )

            elective_pool = (
                courses.filter(type="elective").aggregate(
                    total=Sum("course__credit_hours")
                )["total"]
                or 0
            )

            check(
                compulsory == 39,
                f"{department.code} compulsory = {compulsory} h "
                "(expected 39)",
            )

            check(
                elective_pool >= 21,
                f"{department.code} elective pool = {elective_pool} h "
                "(expected at least 21)",
            )

            shared_hours = (
                DegreeRequirement.objects.filter(
                    department__isnull=True
                ).aggregate(total=Sum("required_hours"))["total"]
                or 0
            )

            department_hours = (
                DegreeRequirement.objects.filter(
                    department=department
                ).aggregate(total=Sum("required_hours"))["total"]
                or 0
            )

            degree_total = shared_hours + department_hours

            check(
                degree_total == 144,
                f"{department.code} degree total = {degree_total} h "
                "(expected 144)",
            )

        check(
            not Course.objects.filter(credit_hours__lte=0).exists(),
            "every course has positive credit hours",
        )

        check(
            not Course.objects.exclude(
                requirement_group="department"
            ).filter(requirement_type__isnull=True).exists(),
            "general/faculty courses have a requirement type",
        )

        check(
            not Course.objects.filter(
                requirement_group="department"
            ).exclude(requirement_type__isnull=True).exists(),
            "department courses have NULL requirement type",
        )

        bad_levels = [
            course.code
            for course in Course.objects.all()
            if len(course.code) < 3
            or not course.code[2].isdigit()
            or course.min_level != int(course.code[2])
        ]

        check(
            not bad_levels,
            f"min_level matches the level digit in course codes: {bad_levels}",
        )

        check(
            not DepartmentCourse.objects.exclude(
                course__requirement_group="department"
            ).exists(),
            "DepartmentCourse only contains department-group courses",
        )

        graph = {}
        for course_id, prerequisite_id in (
            CoursePrerequisite.objects.values_list(
                "course_id", "prerequisite_id"
            )
        ):
            graph.setdefault(course_id, []).append(prerequisite_id)

        state = {}

        def has_cycle(course_id):
            state[course_id] = 1

            for prerequisite_id in graph.get(course_id, []):
                if state.get(prerequisite_id) == 1:
                    return True

                if (
                    state.get(prerequisite_id) is None
                    and has_cycle(prerequisite_id)
                ):
                    return True

            state[course_id] = 2
            return False

        has_prerequisite_cycle = any(
            state.get(course_id) is None and has_cycle(course_id)
            for course_id in list(graph)
        )

        check(
            not has_prerequisite_cycle,
            "no prerequisite cycles",
        )

        missing_features = [
            code
            for code in data.AI_FEATURE_COURSES
            if not Course.objects.filter(code=code).exists()
        ]

        check(
            not missing_features,
            f"all AI feature courses exist: {missing_features}",
        )

        if errors:
            raise CommandError(f"{len(errors)} check(s) failed")

        self.stdout.write(
            self.style.SUCCESS("All seed checks passed.")
        )
