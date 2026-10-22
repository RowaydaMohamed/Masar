"""Installs triggers, the EXCLUDE constraint and views from academics/db_rules.sql."""

from pathlib import Path

from django.db import migrations  # type: ignore[reportMissingModuleSource]


SQL = (
    Path(__file__).resolve().parent.parent / "db_rules.sql"
).read_text(encoding="utf-8")


REVERSE = """
DROP VIEW IF EXISTS
    v_summer_demand,
    v_course_stats,
    v_student_progress,
    v_counted_attempt;

DROP TRIGGER IF EXISTS trg_semrecord_frozen ON student_semester_record;
DROP TRIGGER IF EXISTS trg_seventh_one_pending ON seventh_course_request;
DROP TRIGGER IF EXISTS trg_summer_request_rules ON summer_request;
DROP TRIGGER IF EXISTS trg_deptcourse_group ON department_course;
DROP TRIGGER IF EXISTS trg_prereq_no_cycle ON course_prerequisite;
DROP TRIGGER IF EXISTS trg_enrollment_rules ON enrollment;

DROP FUNCTION IF EXISTS fn_level_for_hours(int);
DROP FUNCTION IF EXISTS fn_semrecord_frozen();
DROP FUNCTION IF EXISTS fn_seventh_one_pending();
DROP FUNCTION IF EXISTS fn_summer_request_rules();
DROP FUNCTION IF EXISTS fn_deptcourse_group();
DROP FUNCTION IF EXISTS fn_prereq_no_cycle();
DROP FUNCTION IF EXISTS fn_enrollment_rules();

ALTER TABLE credit_limit_rule
    DROP CONSTRAINT IF EXISTS ex_creditlimit_no_overlap;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("academics", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(
            sql=[SQL],
            reverse_sql=[REVERSE],
        ),
    ]
