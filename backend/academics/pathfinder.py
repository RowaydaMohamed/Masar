"""
Pure-Python Graduation Path Engine (Contract-compatible baseline for Track 3 integration).
Zero Django ORM imports. Will be replaced/extended by full Slack-Aware CPM engine in Track 2.
"""
from collections import defaultdict
from typing import Any


def _next_term(academic_year: int, term: str) -> tuple[int, str]:
    if term == "fall":
        return academic_year, "spring"
    # spring or summer -> next academic year's fall
    return academic_year + 1, "fall"


def _term_label(academic_year: int, term: str) -> str:
    return f"{academic_year}/{academic_year + 1} {term}"


def _prereqs_satisfied(prereq_groups: list[list[str]], completed: set[str]) -> bool:
    if not prereq_groups:
        return True
    return any(all(code in completed for code in group) for group in prereq_groups)


def _compute_level(earned_hours: int, level_thresholds: dict[str, int]) -> int:
    level = 1
    for lvl_str, min_hrs in sorted(level_thresholds.items(), key=lambda x: int(x[0])):
        if earned_hours >= int(min_hrs):
            level = int(lvl_str)
    return level


def _simulate_schedule(inputs: dict[str, Any], use_preferences: bool) -> dict[str, Any]:
    student_info = inputs.get("student", {})
    settings = inputs.get("settings", {})
    starting_term = inputs.get("starting_term", {})
    elective_remaining = dict(inputs.get("elective_hours_remaining", {"general": 0, "faculty": 0, "department": 0}))

    max_courses = int(settings.get("max_courses_per_semester", 6))
    credit_cap = int(settings.get("default_credit_cap", 18))
    benchmark_terms = int(settings.get("graduation_benchmark_terms", 8))
    level_thresholds = settings.get("level_thresholds", {"1": 0, "2": 36, "3": 72, "4": 108})

    has_department = bool(student_info.get("has_department", False))
    can_take_7th = bool(student_info.get("can_take_7th_course", False))

    passed = set(inputs.get("passed_course_codes", []))
    in_progress = set(inputs.get("in_progress_course_codes", []))
    failed = set(inputs.get("failed_course_codes", [])) - passed - in_progress

    prefs = inputs.get("preferences", {}) if use_preferences else {}
    want_set = set(prefs.get("want", []))
    avoid_set = set(prefs.get("avoid", []))

    all_courses = {}
    for c in inputs.get("courses", []):
        if not has_department and c.get("requirement_group") == "department":
            continue
        all_courses[c["code"]] = c

    # Earned hours so far (passed + in_progress assumed passing in active semester)
    earned_hours = sum(
        all_courses[code]["credits"]
        for code in (passed | in_progress)
        if code in all_courses
    )

    # Account for in_progress electives toward remaining elective caps
    for code in in_progress:
        c = all_courses.get(code)
        if c and c.get("requirement_type") == "elective":
            grp = c.get("requirement_group")
            if grp in elective_remaining:
                elective_remaining[grp] = max(0, elective_remaining[grp] - c["credits"])

    completed_for_sim = set(passed | in_progress)

    # Build downstream dependent counts for priority scoring
    dependents = defaultdict(set)
    for code, c in all_courses.items():
        for group in c.get("prerequisite_groups", []):
            for p in group:
                dependents[p].add(code)

    remaining_compulsory = {
        code for code, c in all_courses.items()
        if code not in completed_for_sim and c.get("requirement_type") == "compulsory"
    }
    remaining_electives = {
        code for code, c in all_courses.items()
        if code not in completed_for_sim and c.get("requirement_type") == "elective"
    }

    cur_year = int(starting_term.get("academic_year", 2026))
    cur_term = starting_term.get("term", "fall")
    completed_terms = int(starting_term.get("completed_terms_count", 0))
    # Active semester counts as 1 if in_progress courses exist
    term_index = completed_terms + (1 if in_progress else 0)

    semesters = []
    scheduled_electives = set()
    max_iterations = 20

    for _ in range(max_iterations):
        need_electives = any(v > 0 for v in elective_remaining.values())
        if not remaining_compulsory and not need_electives:
            break

        cur_year, cur_term = _next_term(cur_year, cur_term)
        term_index += 1
        sim_level = max(int(student_info.get("academic_level", 1)), _compute_level(earned_hours, level_thresholds))

        def is_eligible(code: str) -> bool:
            c = all_courses[code]
            if c.get("typical_term", "both") not in (cur_term, "both"):
                return False
            if sim_level < int(c.get("min_level", 1)):
                return False
            if earned_hours < int(c.get("min_earned_hours", 0)):
                return False
            return _prereqs_satisfied(c.get("prerequisite_groups", []), completed_for_sim)

        eligible_comp = [c for c in remaining_compulsory if is_eligible(c)]
        eligible_comp.sort(
            key=lambda code: (
                0 if code in failed else 1,
                -len(dependents.get(code, ())),
                code,
            )
        )

        eligible_elec = [
            c for c in remaining_electives
            if elective_remaining.get(all_courses[c]["requirement_group"], 0) > 0 and is_eligible(c)
        ]
        eligible_elec.sort(
            key=lambda code: (
                0 if code in want_set else (2 if code in avoid_set else 1),
                -len(dependents.get(code, ())),
                code,
            )
        )

        chosen = []
        used_credits = 0
        comp_credits = 0
        elec_credits = 0

        # Schedule compulsory bottlenecks first, leaving room for electives if available
        target_comp_cap = int(credit_cap * 0.7) if eligible_elec else credit_cap

        for code in eligible_comp:
            c = all_courses[code]
            if len(chosen) >= max_courses or used_credits + c["credits"] > credit_cap:
                continue
            is_urgent = (code in failed) or (len(dependents.get(code, ())) > 0)
            if not is_urgent and comp_credits + c["credits"] > target_comp_cap and eligible_elec:
                continue
            chosen.append((code, "Critical bottleneck / failed retake" if is_urgent else "Compulsory requirement"))
            used_credits += c["credits"]
            comp_credits += c["credits"]

        # Fill elective slots (Want first, Avoid last)
        for code in eligible_elec:
            c = all_courses[code]
            grp = c["requirement_group"]
            if elective_remaining.get(grp, 0) <= 0:
                continue
            if len(chosen) >= max_courses or used_credits + c["credits"] > credit_cap:
                continue
            reason = "Preferred elective (Want)" if code in want_set else "Elective requirement"
            chosen.append((code, reason))
            used_credits += c["credits"]
            elec_credits += c["credits"]
            elective_remaining[grp] = max(0, elective_remaining[grp] - c["credits"])

        # Top up with remaining deferred compulsory courses if credits remain
        chosen_codes = {code for code, _ in chosen}
        for code in eligible_comp:
            if code in chosen_codes:
                continue
            c = all_courses[code]
            if len(chosen) >= max_courses or used_credits + c["credits"] > credit_cap:
                continue
            chosen.append((code, "Compulsory requirement"))
            chosen_codes.add(code)
            used_credits += c["credits"]
            comp_credits += c["credits"]

        sem_courses = []
        for code, reason in chosen:
            c = all_courses[code]
            pref_val = "want" if code in want_set else ("avoid" if code in avoid_set else "none")
            sem_courses.append({
                "code": c["code"],
                "name": c["name"],
                "name_ar": c.get("name_ar", ""),
                "credits": c["credits"],
                "typical_term": c.get("typical_term", "both"),
                "category": c["requirement_type"],
                "requirement_group": c["requirement_group"],
                "preference": pref_val,
                "is_retake": code in failed,
                "slack": 0 if (code in failed or dependents.get(code)) else 1,
                "reason": reason,
            })
            completed_for_sim.add(code)
            earned_hours += c["credits"]
            remaining_compulsory.discard(code)
            if c["requirement_type"] == "elective":
                remaining_electives.discard(code)
                scheduled_electives.add(code)

        semesters.append({
            "term_index": term_index,
            "label": _term_label(cur_year, cur_term),
            "term_type": cur_term,
            "credit_cap": credit_cap,
            "total_credits": used_credits,
            "compulsory_credits": comp_credits,
            "elective_credits": elec_credits,
            "courses": sem_courses,
        })

    remaining_hours = sum(
        c["credits"] for sem in semesters for c in sem["courses"]
    )
    projected_term = semesters[-1]["label"] if semesters else _term_label(cur_year, cur_term)
    total_terms = (semesters[-1]["term_index"] if semesters else term_index)

    warnings = []
    if total_terms > benchmark_terms:
        warnings.append({
            "code": "exceeds_8_terms",
            "severity": "info",
            "message": f"Your path takes {total_terms} terms. Taking summer courses or a 7th course can help you graduate on time.",
            "message_ar": f"مسارك الحالي يستغرق {total_terms} فصول. التسجيل في الصيفي أو مادة سابعة يساعدك على التخرج في موعدك.",
            "suggestions": {
                "can_take_7th_course": can_take_7th,
                "summer_recommended": True,
            },
        })

    return {
        "remaining_hours": remaining_hours,
        "estimated_semesters": len(semesters),
        "projected_graduation_term": projected_term,
        "is_on_track_with_peers": total_terms <= benchmark_terms,
        "warnings": warnings,
        "semesters": semesters,
        "_scheduled_electives": scheduled_electives,
    }


def calculate_slack_cpm_path(inputs: dict[str, Any]) -> dict[str, Any]:
    """Pure-Python entry point matching Sprint 3 Black-Box Engine Contract."""
    baseline = _simulate_schedule(inputs, use_preferences=False)
    preferred = _simulate_schedule(inputs, use_preferences=True)

    baseline_sems = baseline["estimated_semesters"]
    preferred_sems = preferred["estimated_semesters"]
    warnings = list(preferred["warnings"])

    if preferred_sems > baseline_sems:
        prefs = inputs.get("preferences", {})
        want_list = prefs.get("want", [])
        avoid_list = prefs.get("avoid", [])
        caused_by = list(dict.fromkeys(avoid_list + want_list))
        diff = preferred_sems - baseline_sems
        if caused_by:
            warnings.insert(0, {
                "code": "preference_delay",
                "severity": "warning",
                "message": f"Your course preferences ({', '.join(caused_by)}) push your graduation back by {diff} semester(s).",
                "message_ar": f"تفضيلاتك للمواد ({'، '.join(caused_by)}) تؤخر تخرجك بمقدار {diff} فصل دراسي.",
                "caused_by": caused_by,
            })

    return {
        "remaining_hours": preferred["remaining_hours"],
        "baseline_semesters": baseline_sems,
        "estimated_semesters": preferred_sems,
        "projected_graduation_term": preferred["projected_graduation_term"],
        "is_on_track_with_peers": preferred["is_on_track_with_peers"],
        "warnings": warnings,
        "semesters": preferred["semesters"],
    }