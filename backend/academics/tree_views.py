from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from academics.engine import (
    student_plan, compute_course_statuses, counted_attempts, cgpa
)
from academics.models import Semester, CourseOffering, StudentSemesterRecord, Enrollment
from collections import deque

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def curriculum_tree(request):
    """Tree 1: الخطة الدراسية الخاصة بالطالب مع حالة كل مادة."""
    student = request.user.student
    current_sem = Semester.objects.filter(is_current=True).first()
    plan = student_plan(student)
    statuses = compute_course_statuses(student, current_sem)
    
    nodes = []
    for cid, info in plan.items():
        course = info['course']
        prereqs = {}
        for p in course.prerequisite_links.all():
            prereqs.setdefault(p.group, []).append(p.prerequisite.code)
        
        unlocks = [u.course.code for u in course.unlocks_links.all()]
        
        nodes.append({
            "code": course.code,
            "name": course.name,
            "name_ar": course.name_ar,
            "credits": course.credit_hours,
            "level": course.min_level,
            "requirement_group": info['group'],
            "requirement_type": info['type'],
            "status": statuses.get(cid, "locked"),
            "prerequisites": list(prereqs.values()),
            "unlocks": unlocks
        })
    return Response(nodes)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def requirements_progress(request):
    """متطلبات التخرج وتتبع الإنجاز (144 ساعة)."""
    student = request.user.student
    plan = student_plan(student)
    attempts = counted_attempts(student)
    current_sem = Semester.objects.filter(is_current=True).first()
    
    registered_cids = []
    if current_sem:
        # التعديل هنا: استخدام Enrollment مباشرة للأمان
        registered_cids = Enrollment.objects.filter(
            student=student, status='registered', offering__semester=current_sem
        ).values_list('offering__course_id', flat=True)

    progress = {
        "general": {"compulsory": {"earned": 0, "registered": 0, "required": 6}, "elective": {"earned": 0, "registered": 0, "required": 6}},
        "faculty": {"compulsory": {"earned": 0, "registered": 0, "required": 63}, "elective": {"earned": 0, "registered": 0, "required": 9}},
        "department": {"compulsory": {"earned": 0, "registered": 0, "required": 39}, "elective": {"earned": 0, "registered": 0, "required": 21}},
        "total_earned": 0,
        "total_required": 144
    }

    if not student.department_id:
        progress["department"]["required"] = 0

    for cid, info in plan.items():
        grp = info['group']
        typ = info['type']
        hrs = info['course'].credit_hours
        
        if cid in attempts and attempts[cid].status == 'completed':
            progress[grp][typ]["earned"] += hrs
            progress["total_earned"] += hrs
        elif cid in registered_cids:
            progress[grp][typ]["registered"] += hrs

    return Response(progress)

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def graduation_path(request):
    """مسار التخرج الديناميكي (Tree 3) مع خوارزمية التوزيع على الأترام."""
    student = request.user.student
    plan = student_plan(student)
    attempts = counted_attempts(student)
    current_sem = Semester.objects.filter(is_current=True).first()
    
    passed_cids = {cid for cid, e in attempts.items() if e.status == 'completed'}
    
    # التعديل هنا: استبعاد المواد المسجلة في الترم الحالي من خطة الأترام القادمة
    registered_cids = set()
    if current_sem:
        registered_cids = set(Enrollment.objects.filter(
            student=student, status='registered', offering__semester=current_sem
        ).values_list('offering__course_id', flat=True))
    
    remaining_courses = {}
    for cid, info in plan.items():
        # إذا لم ينجح فيها ولم يسجلها حالياً
        if cid not in passed_cids and cid not in registered_cids:
            remaining_courses[cid] = info['course']
            
    graph = {}
    in_degree = {cid: 0 for cid in remaining_courses}
    
    for cid, course in remaining_courses.items():
        prereqs = course.prerequisite_links.values_list('prerequisite_id', flat=True)
        active_prereqs = [p for p in prereqs if p in remaining_courses]
        
        in_degree[cid] += len(active_prereqs)
        for p in active_prereqs:
            graph.setdefault(p, []).append(cid)

    available_queue = [cid for cid, deg in in_degree.items() if deg == 0]
    
    semesters_plan = []
    max_credits_per_sem = 18
    
    while available_queue:
        current_sem_courses = []
        current_sem_credits = 0
        next_available = []
        
        available_queue.sort(key=lambda c: len(graph.get(c, [])), reverse=True)
        
        for cid in available_queue:
            course = remaining_courses[cid]
            if current_sem_credits + course.credit_hours <= max_credits_per_sem:
                current_sem_courses.append({
                    "code": course.code,
                    "name": course.name_en,
                    "credits": course.credit_hours
                })
                current_sem_credits += course.credit_hours
            else:
                next_available.append(cid)
                
        semesters_plan.append({
            "term": f"الترم المتوقع {len(semesters_plan) + 1}",
            "credits": current_sem_credits,
            "courses": current_sem_courses
        })
        
        for item in current_sem_courses:
            cid_planned = next((c for c, obj in remaining_courses.items() if obj.code == item['code']), None)
            for dependent in graph.get(cid_planned, []):
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    next_available.append(dependent)
                    
        available_queue = next_available
        
        if not current_sem_courses and next_available:
            break 

    return Response({
        "remaining_hours": sum(c.credit_hours for c in remaining_courses.values()),
        "estimated_semesters": len(semesters_plan),
        "semesters": semesters_plan
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def student_history(request):
    """السجل الأكاديمي فصلاً بفصل."""
    records = StudentSemesterRecord.objects.filter(student=request.user.student).order_by('semester__start_date')
    history = []
    for r in records:
        # التعديل هنا: استخدام Enrollment مباشرة للأمان
        enrollments = Enrollment.objects.filter(
            student=request.user.student, offering__semester=r.semester, status__in=['completed', 'failed']
        ).select_related('offering__course')
        
        courses = [{
            "code": e.offering.course.code,
            "name": e.offering.course.name_en,
            "score": e.score,
            "grade": e.grade_letter,
            "points": e.grade_points
        } for e in enrollments]
        
        history.append({
            "semester": r.semester.label,
            "level_then": r.level_at_time,
            "semester_gpa": r.semester_gpa,
            "cumulative_gpa": r.cumulative_gpa,
            "credits_earned": r.credits_earned,
            "courses": courses
        })
    return Response(history)