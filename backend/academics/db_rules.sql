
-- ===================================================================================
-- Masar db_rules.sql (PostgreSQL 14+)
-- Triggers, constraints, functions and reporting views.
-- Installed by migrations/0002_db_rules.py
-- ===================================================================================


-- 1. EXCLUDE: CGPA bands of credit_limit_rule must not overlap
-- -------------------------------------------------------------------------------
ALTER TABLE credit_limit_rule
    DROP CONSTRAINT IF EXISTS ex_creditlimit_no_overlap;

ALTER TABLE credit_limit_rule
    ADD CONSTRAINT ex_creditlimit_no_overlap
    EXCLUDE USING gist (
        numrange(min_cgpa, max_cgpa, '[)') WITH &&
    );


-- 2. enrollment: prevent retaking passed courses and duplicate registrations
-- -------------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_enrollment_rules()
RETURNS trigger AS $$
DECLARE
    v_course bigint;
BEGIN
    SELECT course_id
    INTO v_course
    FROM course_offering
    WHERE id = NEW.offering_id;

    IF NEW.status IN ('registered', 'completed')
       AND EXISTS (
            SELECT 1
            FROM enrollment e
            JOIN course_offering o ON o.id = e.offering_id
            WHERE e.student_id = NEW.student_id
              AND o.course_id = v_course
              AND e.status = 'completed'
              AND e.id IS DISTINCT FROM NEW.id
       )
    THEN
        RAISE EXCEPTION
            'student % already passed course % (no grade-improvement retakes)',
            NEW.student_id, v_course
            USING ERRCODE = 'check_violation';
    END IF;

    IF NEW.status = 'registered'
       AND EXISTS (
            SELECT 1
            FROM enrollment e
            JOIN course_offering o ON o.id = e.offering_id
            WHERE e.student_id = NEW.student_id
              AND o.course_id = v_course
              AND e.status = 'registered'
              AND e.id IS DISTINCT FROM NEW.id
       )
    THEN
        RAISE EXCEPTION
            'student % is already registered in course %',
            NEW.student_id, v_course
            USING ERRCODE = 'check_violation';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_enrollment_rules ON enrollment;

CREATE TRIGGER trg_enrollment_rules
BEFORE INSERT OR UPDATE OF status, offering_id, student_id
ON enrollment
FOR EACH ROW
EXECUTE FUNCTION fn_enrollment_rules();


-- 3. course_prerequisite: prevent prerequisite cycles
-- -------------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_prereq_no_cycle()
RETURNS trigger AS $$
BEGIN
    IF EXISTS (
        WITH RECURSIVE reach(course_id) AS (
            SELECT NEW.prerequisite_id

            UNION

            SELECT cp.prerequisite_id
            FROM course_prerequisite AS cp
            JOIN reach AS r
                ON cp.course_id = r.course_id
        )
        SELECT 1
        FROM reach
        WHERE course_id = NEW.course_id
    )
    THEN
        RAISE EXCEPTION
            'prerequisite cycle: course % <-> %',
            NEW.course_id, NEW.prerequisite_id
            USING ERRCODE = 'check_violation';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_prereq_no_cycle ON course_prerequisite;

CREATE TRIGGER trg_prereq_no_cycle
BEFORE INSERT OR UPDATE OF course_id, prerequisite_id
ON course_prerequisite
FOR EACH ROW
EXECUTE FUNCTION fn_prereq_no_cycle();


-- 4. department_course: only department-group courses
-- -------------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_deptcourse_group()
RETURNS trigger AS $$
BEGIN
    IF (
        SELECT requirement_group
        FROM course
        WHERE id = NEW.course_id
    ) <> 'department'
    THEN
        RAISE EXCEPTION
            'course % is not a department-group course',
            NEW.course_id
            USING ERRCODE = 'check_violation';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_deptcourse_group ON department_course;

CREATE TRIGGER trg_deptcourse_group
BEFORE INSERT OR UPDATE OF course_id
ON department_course
FOR EACH ROW
EXECUTE FUNCTION fn_deptcourse_group();


-- 5. summer_request: summer semester and matching fulfilling offering
-- -------------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_summer_request_rules()
RETURNS trigger AS $$
BEGIN
    IF (
        SELECT term
        FROM semester
        WHERE id = NEW.semester_id
    ) <> 'summer'
    THEN
        RAISE EXCEPTION
            'summer requests need a summer semester'
            USING ERRCODE = 'check_violation';
    END IF;

    IF NEW.fulfilled_by_offering_id IS NOT NULL
       AND NOT EXISTS (
            SELECT 1
            FROM course_offering AS o
            WHERE o.id = NEW.fulfilled_by_offering_id
              AND o.course_id = NEW.course_id
              AND o.semester_id = NEW.semester_id
       )
    THEN
        RAISE EXCEPTION
            'fulfilling offering must be the same course and semester'
            USING ERRCODE = 'check_violation';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_summer_request_rules ON summer_request;

CREATE TRIGGER trg_summer_request_rules
BEFORE INSERT OR UPDATE OF semester_id, course_id, fulfilled_by_offering_id
ON summer_request
FOR EACH ROW
EXECUTE FUNCTION fn_summer_request_rules();


-- 6. seventh_course_request: one pending request per student per semester
-- -------------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_seventh_one_pending()
RETURNS trigger AS $$
DECLARE
    v_sem bigint;
BEGIN
    IF NEW.status = 'pending' THEN
        SELECT semester_id
        INTO v_sem
        FROM course_offering
        WHERE id = NEW.offering_id;

        IF EXISTS (
            SELECT 1
            FROM seventh_course_request AS r
            JOIN course_offering AS o
                ON o.id = r.offering_id
            WHERE r.student_id = NEW.student_id
              AND r.status = 'pending'
              AND o.semester_id = v_sem
              AND r.id IS DISTINCT FROM NEW.id
        )
        THEN
            RAISE EXCEPTION
                'student % already has a pending 7th-course request this semester',
                NEW.student_id
                USING ERRCODE = 'check_violation';
        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_seventh_one_pending
ON seventh_course_request;

CREATE TRIGGER trg_seventh_one_pending
BEFORE INSERT OR UPDATE OF status, offering_id, student_id
ON seventh_course_request
FOR EACH ROW
EXECUTE FUNCTION fn_seventh_one_pending();


-- 7. student_semester_record: frozen snapshot
-- To allow corrections in a transaction:
-- SET LOCAL masar.allow_snapshot_edit = 'on';
-- -------------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_semrecord_frozen()
RETURNS trigger AS $$
BEGIN
    IF COALESCE(
        current_setting('masar.allow_snapshot_edit', true),
        'off'
    ) <> 'on'
    THEN
        RAISE EXCEPTION
            'student_semester_record rows are frozen'
            USING ERRCODE = 'check_violation';
    END IF;

    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_semrecord_frozen
ON student_semester_record;

CREATE TRIGGER trg_semrecord_frozen
BEFORE UPDATE OR DELETE
ON student_semester_record
FOR EACH ROW
EXECUTE FUNCTION fn_semrecord_frozen();


-- 8. Determine academic level from earned credit hours
-- -------------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_level_for_hours(h int)
RETURNS int AS $$
    SELECT COALESCE(MAX(level), 1)
    FROM level_threshold
    WHERE min_earned_hours <= h;
$$ LANGUAGE sql STABLE;


-- 9. Read-only reporting views
-- -------------------------------------------------------------------------------

-- Latest graded attempt per student and course.
-- Withdrawn and registered enrollments are excluded.
CREATE OR REPLACE VIEW v_counted_attempt AS
SELECT DISTINCT ON (e.student_id, o.course_id)
       e.student_id,
       o.course_id,
       e.id AS enrollment_id,
       o.semester_id,
       e.status,
       e.score,
       e.grade_letter,
       e.grade_points,
       c.credit_hours
FROM enrollment AS e
JOIN course_offering AS o
    ON o.id = e.offering_id
JOIN semester AS s
    ON s.id = o.semester_id
JOIN course AS c
    ON c.id = o.course_id
WHERE e.status IN ('completed', 'failed')
ORDER BY
    e.student_id,
    o.course_id,
    s.start_date DESC,
    e.id DESC;


-- Student progress and CGPA
CREATE OR REPLACE VIEW v_student_progress AS
SELECT
    st.id AS student_id,
    st.university_id,
    st.department_id,
    st.academic_level,

    COALESCE(
        SUM(ca.credit_hours)
            FILTER (
                WHERE ca.status = 'completed'
                  AND x.in_plan
            ),
        0
    )::int AS earned_hours_in_plan,

    COALESCE(
        SUM(ca.credit_hours)
            FILTER (WHERE ca.status = 'completed'),
        0
    )::int AS earned_hours_all,

    ROUND(
        SUM(ca.grade_points * ca.credit_hours)
            / NULLIF(SUM(ca.credit_hours), 0),
        2
    ) AS cgpa

FROM student AS st

LEFT JOIN v_counted_attempt AS ca
    ON ca.student_id = st.id

LEFT JOIN LATERAL (
    SELECT (
        c.requirement_group IN ('general', 'faculty')
        OR EXISTS (
            SELECT 1
            FROM department_course AS dc
            WHERE dc.department_id = st.department_id
              AND dc.course_id = c.id
        )
    ) AS in_plan
    FROM course AS c
    WHERE c.id = ca.course_id
) AS x ON TRUE

GROUP BY
    st.id,
    st.university_id,
    st.department_id,
    st.academic_level;


-- Course statistics: all graded attempts, including previous failures
CREATE OR REPLACE VIEW v_course_stats AS
SELECT
    o.course_id,
    c.code,
    o.semester_id,
    s.academic_year,
    s.term,

    COUNT(*) AS graded_attempts,

    COUNT(*) FILTER (
        WHERE e.status = 'completed'
    ) AS passed,

    COUNT(*) FILTER (
        WHERE e.status = 'failed'
    ) AS failed,

    ROUND(
        100.0 * COUNT(*) FILTER (
            WHERE e.status = 'completed'
        ) / COUNT(*),
        1
    ) AS pass_rate_pct

FROM enrollment AS e
JOIN course_offering AS o
    ON o.id = e.offering_id
JOIN course AS c
    ON c.id = o.course_id
JOIN semester AS s
    ON s.id = o.semester_id

WHERE e.status IN ('completed', 'failed')

GROUP BY
    o.course_id,
    c.code,
    o.semester_id,
    s.academic_year,
    s.term;


-- Pending summer requests by semester and course
CREATE OR REPLACE VIEW v_summer_demand AS
SELECT
    r.semester_id,
    r.course_id,
    c.code,
    COUNT(*) AS pending_requests
FROM summer_request AS r
JOIN course AS c
    ON c.id = r.course_id
WHERE r.status = 'pending'
GROUP BY
    r.semester_id,
    r.course_id,
    c.code;
