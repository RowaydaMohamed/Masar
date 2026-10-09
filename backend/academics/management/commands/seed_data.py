from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from academics.models import (
    Department, Course, CoursePrerequisite, GradeScale,
    Student, StudentCourseHistory,
)


class Command(BaseCommand):
    help = "Seed departments, real bylaw courses, prerequisites, grade scale, and 3 test students"

    def handle(self, *args, **kwargs):
        # ---------- Departments ----------
        cs = Department.objects.create(code="CS", name_en="Computer Science", name_ar="علوم الحاسب")
        it = Department.objects.create(code="IT", name_en="Information Technology", name_ar="تكنولوجيا المعلومات")
        is_ = Department.objects.create(code="IS", name_en="Information Systems", name_ar="نظم المعلومات")
        ai = Department.objects.create(code="AI", name_en="Artificial Intelligence", name_ar="الذكاء الاصطناعي")

        # ---------- Grade scale (reverse-engineered from the real transcript) ----------
        bands = [
            (90, 100, "A+", 4.00), (85, 89, "A", 3.70), (80, 84, "B+", 3.30),
            (75, 79, "B", 3.00), (70, 74, "C+", 2.30), (65, 69, "C", 2.00),
            (60, 64, "D+", 1.30), (55, 59, "D", 1.00), (0, 54, "F", 0.00),
        ]
        for lo, hi, letter, points in bands:
            GradeScale.objects.create(min_score=lo, max_score=hi, letter=letter, gpa_points=points)

        # ---------- Courses (real codes/names/hours straight from the bylaw) ----------
        course_data = [
            # code, name_en, name_ar, credit_hours, category, requirement_type
            ("HU111", "English 1", "لغة إنجليزية 1", 2, "general", "compulsory"),
            ("MA111", "Mathematics 1", "رياضيات 1", 3, "general", "compulsory"),
            ("MA113", "Mathematics 2", "رياضيات 2", 3, "general", "compulsory"),
            ("ST121", "Probability and Statistics 1", "إحصاء واحتمالات 1", 3, "general", "compulsory"),
            ("ST122", "Probability and Statistics 2", "إحصاء واحتمالات 2", 3, "general", "elective"),
            ("CS111", "Introduction to Computers", "مقدمة في الحاسبات", 3, "general", "compulsory"),
            ("CS112", "Programming 1", "برمجة 1", 3, "general", "compulsory"),
            ("CS214", "Data Structures", "هياكل البيانات", 3, "general", "compulsory"),
            ("CS316", "Algorithms", "خوارزميات", 3, "general", "compulsory"),
            ("IT221", "Data Communication", "تراسل البيانات", 3, "general", "compulsory"),
            ("IT222", "Computer Networks 1", "شبكات الحاسبات 1", 3, "general", "compulsory"),
            ("IS231", "Fundamentals of Information Systems", "أساسيات نظم المعلومات", 3, "general", "compulsory"),
            ("IS211", "Database System 1", "نظم قواعد البيانات 1", 3, "general", "compulsory"),
            ("IS351", "System Analysis and Design 1", "تحليل وتصميم نظم 1", 3, "general", "compulsory"),
            ("IS312", "Database Systems 2", "نظم قواعد البيانات 2", 3, "is", "compulsory"),
            ("CS352", "Software Engineering 2", "هندسة برمجيات 2", 3, "cs", "compulsory"),
            ("IT322", "Computer Networks 2", "شبكات الحاسبات 2", 3, "it", "compulsory"),
            ("AI310", "Artificial Intelligence", "الذكاء الاصطناعي", 3, "ai", "compulsory"),
            ("AI330", "Machine Learning", "تعلم الآلة", 3, "ai", "compulsory"),
        ]
        courses = {}
        for code, name_en, name_ar, hours, category, req_type in course_data:
            courses[code] = Course.objects.create(
                code=code, name_en=name_en, name_ar=name_ar, credit_hours=hours,
                category=category, requirement_type=req_type,
            )

        # ---------- Prerequisites (straight from the bylaw's own "بلطتملا قباسلا" column) ----------
        prereq_pairs = [
            ("CS214", "CS112"),
            ("CS316", "CS214"),
            ("IT222", "IT221"),
            ("IS351", "IS231"),
            ("IS312", "IS211"),
            ("IT322", "IT222"),
            ("AI310", "CS316"),
            ("AI330", "ST122"),
            ("ST122", "ST121"),
        ]
        for course_code, prereq_code in prereq_pairs:
            CoursePrerequisite.objects.create(
                course=courses[course_code], prerequisite_course=courses[prereq_code]
            )

        # ============================================================
        # Student 1 — modeled on the REAL uploaded transcript
        # (محمود علاء الدين, Information Systems, real scores)
        # ============================================================
        u1 = User.objects.create_user("mahmoud_alaa", password="test1234")
        s1 = Student.objects.create(
            user=u1, university_email="mahmoud.alaa@student.masar.edu",
            full_name="محمود علاء الدين", entry_year=2022, academic_level=3,
            department=is_, cgpa=3.57, total_hours_completed=91, status="enrolled",
        )
        real_history = [
            ("HU111", 94, "A+"), ("MA111", 64, "D+"), ("MA113", 76, "B"),
            ("ST121", 81, "B+"), ("ST122", 95, "A+"), ("CS111", 80, "B+"),
            ("CS112", 85, "A"), ("CS214", 89, "A"), ("CS316", 90, "A+"),
            ("IT221", 78, "B"), ("IT222", 78, "B"), ("IS231", 67, "C"),
            ("IS211", 87, "A"), ("IS351", 78, "B"), ("IS312", 97, "A+"),
            ("AI310", 93, "A+"),
        ]
        for code, score, letter in real_history:
            StudentCourseHistory.objects.create(
                student=s1, course=courses[code], numeric_score=score,
                letter_grade=letter, status="completed", attempt_number=1,
                academic_year="2023/2024", semester="fall",
            )

        # ============================================================
        # Student 2 — synthetic, has a FAILED course (needed for testing 🔴 status)
        # ============================================================
        u2 = User.objects.create_user("ahmed_samir", password="test1234")
        s2 = Student.objects.create(
            user=u2, university_email="ahmed.samir@student.masar.edu",
            full_name="أحمد سمير", entry_year=2023, academic_level=2,
            department=cs, cgpa=2.30, total_hours_completed=24, status="enrolled",
        )
        StudentCourseHistory.objects.create(
            student=s2, course=courses["HU111"], numeric_score=85, letter_grade="A",
            status="completed", academic_year="2024/2025", semester="fall",
        )
        StudentCourseHistory.objects.create(
            student=s2, course=courses["CS112"], numeric_score=78, letter_grade="B",
            status="completed", academic_year="2024/2025", semester="fall",
        )
        StudentCourseHistory.objects.create(
            student=s2, course=courses["CS214"], numeric_score=45, letter_grade="F",
            status="failed", attempt_number=1, academic_year="2024/2025", semester="spring",
        )

        # ============================================================
        # Student 3 — synthetic, close to graduation (AI department)
        # ============================================================
        u3 = User.objects.create_user("mona_khaled", password="test1234")
        s3 = Student.objects.create(
            user=u3, university_email="mona.khaled@student.masar.edu",
            full_name="منى خالد", entry_year=2021, academic_level=4,
            department=ai, cgpa=3.80, total_hours_completed=120, status="enrolled",
        )
        for code in ["HU111", "MA111", "MA113", "ST121", "ST122", "CS111",
                     "CS112", "CS214", "CS316", "AI310", "AI330"]:
            StudentCourseHistory.objects.create(
                student=s3, course=courses[code], numeric_score=92, letter_grade="A+",
                status="completed", academic_year="2023/2024", semester="fall",
            )

        self.stdout.write(self.style.SUCCESS(
            "Seed complete: 4 departments, 19 courses, 9 prerequisites, "
            "9 grade bands, 3 students."
        ))