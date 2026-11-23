"""
academics/pathfinder_adapter.py

Imperative Django adapter connecting the database to the pure-Python pathfinder engine,
enforcing Dual-Run evaluation and the Stability Gate on SavedGraduationPlan.
"""
from django.db import transaction

from academics.engine import cgpa as compute_cgpa, counted_attempts, student_plan
from academics.models import (
    Course,
    CreditLimitRule,
    DegreeRequirement,
    DepartmentCourse,
    Enrollment,
    LevelThreshold,
    SavedGraduationPlan,
    Semester,
    StudentCoursePreference,
    StudentSemesterRecord,
)
from academics.pathfinder import calculate_slack_cpm_path

E = Enrollment.Status


def _regular_credit_cap(student, student_cgpa) -> int:
    from academics.services import get_setting

    if student_cgpa is None:
        return int(get_setting("new_student_max_credits"))
    for rule in CreditLimitRule.objects.all():
        min_ok = rule.min_cgpa is None or student_cgpa >= rule.min_cgpa
        max_ok = rule.max_cgpa is None or student_cgpa < rule.max_cgpa
        if min_ok and max_ok:
            return int(rule.max_credits)
    return int(get_setting("new_student_max_credits"))


def is_course_compulsory_for_student(student, course: Course) -> bool:
    """Returns True if `course` is compulsory in the student's general/faculty/department plan."""
    if course.requirement_group in (Course.Group.GENERAL, Course.Group.FACULTY):
        return course.requirement_type == Course.Type.COMPULSORY
    if course.requirement_group == Course.Group.DEPARTMENT and student.department_id:
        return DepartmentCourse.objects.filter(
            department_id=student.department_id,
            course=course,
            type=Course.Type.COMPULSORY,
        ).exists()
    return False


def build_pathfinder_inputs(student) -> dict:
    """Builds the plain-dictionary input schema required by calculate_slack_cpm_path."""
    from academics.services import get_setting

    current_sem = Semester.objects.filter(is_current=True).first()
    plan = student_plan(student)
    attempts = counted_attempts(student)
    student_cgpa = compute_cgpa(student)

    # Course IDs & codes by status
    passed_cids = {cid for cid, e in attempts.items() if e.status == E.COMPLETED}
    passed_codes = sorted(
        e.offering.course.code for e in attempts.values() if e.status == E.COMPLETED
    )

    in_progress_qs = Enrollment.objects.none()
    if current_sem:
        in_progress_qs = Enrollment.objects.filter(
            student=student,
            status=E.REGISTERED,
            offering__semester=current_sem,
        ).select_related("offering__course")

    in_progress_cids = {e.offering.course_id for e in in_progress_qs}
    in_progress_codes = sorted(e.offering.course.code for e in in_progress_qs)

    # Failed courses that have not been passed or currently registered for retake
    failed_codes = sorted(
        e.offering.course.code
        for cid, e in attempts.items()
        if e.status == E.FAILED and cid not in passed_cids and cid not in in_progress_cids
    )

    # Level thresholds mapping {"1": 0, "2": 36, ...}
    thresholds = {
        str(lt.level): lt.min_earned_hours
        for lt in LevelThreshold.objects.all()
    }
    if not thresholds:
        thresholds = {"1": 0, "2": 36, "3": 72, "4": 108}

    # Seventh-course eligibility based on CGPA setting
    seventh_min = get_setting("seventh_course_min_cgpa")
    can_take_7th = bool(student_cgpa is not None and student_cgpa >= seventh_min)

    # Starting term metadata
    if current_sem:
        start_year = current_sem.academic_year
        start_term = current_sem.term
    else:
        start_year = student.admission_semester.academic_year
        start_term = student.admission_semester.term

    completed_terms_count = (
        StudentSemesterRecord.objects.filter(student=student)
        .exclude(semester__term=Semester.Term.SUMMER)
        .count()
    )

    # Elective credit-hour requirements & remaining hours
    elective_required = {"general": 6, "faculty": 9, "department": 21}
    for req in DegreeRequirement.objects.filter(type=DegreeRequirement.Type.ELECTIVE):
        if req.scope in ("general", "faculty") and req.department_id is None:
            elective_required[req.scope] = req.required_hours
        elif req.scope == "department" and student.department_id and req.department_id == student.department_id:
            elective_required["department"] = req.required_hours

    elective_earned = {"general": 0, "faculty": 0, "department": 0}
    for cid in passed_cids:
        info = plan.get(cid)
        if info and info["type"] == "elective":
            grp = info["group"]
            if grp in elective_earned:
                elective_earned[grp] += info["course"].credit_hours

    elective_hours_remaining = {
        grp: max(0, elective_required[grp] - elective_earned[grp])
        for grp in ("general", "faculty", "department")
    }

    # Student preferences (Want / Avoid; guard against Avoid on compulsory courses)
    want_codes = []
    avoid_codes = []
    prefs_qs = StudentCoursePreference.objects.filter(student=student).select_related("course")
    for pref in prefs_qs:
        if pref.kind == StudentCoursePreference.Kind.WANT:
            want_codes.append(pref.course.code)
        elif pref.kind == StudentCoursePreference.Kind.AVOID:
            if not is_course_compulsory_for_student(student, pref.course):
                avoid_codes.append(pref.course.code)

    # Prefetch prerequisite links for all courses in the student's plan
    course_ids = list(plan.keys())
    courses_qs = (
        Course.objects.filter(id__in=course_ids)
        .prefetch_related("prerequisite_links__prerequisite")
        .order_by("code")
    )

    courses_payload = []
    for course in courses_qs:
        info = plan[course.id]
        groups_map: dict[int, list[str]] = {}
        for link in course.prerequisite_links.all():
            groups_map.setdefault(link.group, []).append(link.prerequisite.code)
        prereq_groups = [sorted(codes) for _, codes in sorted(groups_map.items())]

        courses_payload.append({
            "code": course.code,
            "name": course.name,
            "name_ar": course.name_ar,
            "credits": course.credit_hours,
            "min_level": course.min_level,
            "min_earned_hours": course.min_earned_hours,
            "typical_term": course.typical_term,
            "requirement_group": info["group"],
            "requirement_type": info["type"],
            "prerequisite_groups": prereq_groups,
        })

    return {
        "student": {
            "academic_level": student.academic_level,
            "cgpa": float(student_cgpa) if student_cgpa is not None else None,
            "has_department": bool(student.department_id),
            "can_take_7th_course": can_take_7th,
        },
        "settings": {
            "max_courses_per_semester": int(get_setting("max_courses_per_semester")),
            "default_credit_cap": _regular_credit_cap(student, student_cgpa),
            "summer_max_credits": int(get_setting("summer_max_credits")),
            "graduation_benchmark_terms": 8,
            "level_thresholds": thresholds,
        },
        "starting_term": {
            "academic_year": start_year,
            "term": start_term,
            "completed_terms_count": completed_terms_count,
        },
        "elective_hours_remaining": elective_hours_remaining,
        "passed_course_codes": passed_codes,
        "in_progress_course_codes": in_progress_codes,
        "failed_course_codes": failed_codes,
        "preferences": {
            "want": sorted(want_codes),
            "avoid": sorted(avoid_codes),
        },
        "courses": courses_payload,
    }


def _is_saved_plan_valid(saved_plan: SavedGraduationPlan, inputs: dict, preferred_result: dict) -> bool:
    """
    Stability Gate check:
    Returns True iff the saved semester layout is still valid (no broken prerequisites,
    no newly failed/dropped/registered courses, no violated Avoid preferences) AND
    finishes in the exact same projected_graduation_term.
    """
    old_data = saved_plan.plan_data or {}
    old_semesters = old_data.get("semesters")
    new_semesters = preferred_result.get("semesters")

    if not old_semesters or not new_semesters:
        return False

    new_grad_term = preferred_result.get("projected_graduation_term", "")
    if not saved_plan.projected_graduation_term or saved_plan.projected_graduation_term != new_grad_term:
        return False

    catalog = {c["code"]: c for c in inputs.get("courses", [])}
    passed = set(inputs.get("passed_course_codes", []))
    in_progress = set(inputs.get("in_progress_course_codes", []))
    failed = set(inputs.get("failed_course_codes", []))
    avoid = set(inputs.get("preferences", {}).get("avoid", []))

    old_codes = []
    for sem in old_semesters:
        for item in sem.get("courses", []):
            code = item.get("code")
            if not code or code not in catalog:
                return False
            if code in passed or code in in_progress or code in avoid:
                return False
            old_codes.append(code)

    new_codes = [
        item["code"]
        for sem in new_semesters
        for item in sem.get("courses", [])
    ]

    # Exact same set of planned courses (catches drops, registrations, department changes, new wants)
    if set(old_codes) != set(new_codes) or len(old_codes) != len(new_codes):
        return False

    # Every failed course requiring retake must be included
    if not failed.issubset(set(old_codes)):
        return False

    # Verify prerequisite ordering and typical_term validity across saved semesters
    completed_so_far = set(passed | in_progress)
    for sem in old_semesters:
        term_type = sem.get("term_type")
        sem_codes = [item["code"] for item in sem.get("courses", [])]
        for code in sem_codes:
            course_meta = catalog[code]
            typical = course_meta.get("typical_term", "both")
            if term_type in ("fall", "spring") and typical not in (term_type, "both"):
                return False
            groups = course_meta.get("prerequisite_groups", [])
            if groups and not any(all(p in completed_so_far for p in grp) for grp in groups):
                return False
        completed_so_far.update(sem_codes)

    return True


@transaction.atomic
def recalculate_student_plan(student) -> SavedGraduationPlan:
    """
    Runs Dual-Run evaluation (Baseline vs Preferred), applies the Stability Gate,
    and persists the updated plan in SavedGraduationPlan with is_stale=False.
    """
    inputs_preferred = build_pathfinder_inputs(student)
    inputs_baseline = {
        **inputs_preferred,
        "preferences": {"want": [], "avoid": []},
    }

    baseline_result = calculate_slack_cpm_path(inputs_baseline)
    preferred_result = calculate_slack_cpm_path(inputs_preferred)

    # Ensure baseline_semesters reflects the baseline run
    preferred_result["baseline_semesters"] = baseline_result.get(
        "baseline_semesters", baseline_result.get("estimated_semesters", 0)
    )

    saved_plan, _ = SavedGraduationPlan.objects.select_for_update().get_or_create(
        student=student,
        defaults={"is_stale": True},
    )

    if _is_saved_plan_valid(saved_plan, inputs_preferred, preferred_result):
        # Preserve existing semester layout to prevent unnecessary shuffling
        preferred_result["semesters"] = saved_plan.plan_data["semesters"]

    saved_plan.plan_data = preferred_result
    saved_plan.projected_graduation_term = preferred_result.get("projected_graduation_term", "")
    saved_plan.is_stale = False
    saved_plan.save(update_fields=["plan_data", "projected_graduation_term", "is_stale", "updated_at"])
    return saved_plan