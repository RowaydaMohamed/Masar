import os
import joblib
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from academics.models import StudentCourseHistory, GradeScale

# بيتحمّل مرة واحدة بس لما السيرفر يشتغل، مش في كل request
MODEL_PATH = os.path.join(os.path.dirname(__file__), 'specialization_model.joblib')
_model_data = joblib.load(MODEL_PATH)
_model = _model_data['model']
_features = _model_data['features']   # ترتيب أسامي الـ 24 مادة اللي الموديل مدرّب عليها


def _score_to_gpa_points(numeric_score):
    """بيحول درجة رقمية (0-100) لنقاط GPA (0-4) باستخدام جدول GradeScale بتاع يمنى."""
    band = GradeScale.objects.filter(
        min_score__lte=numeric_score, max_score__gte=numeric_score
    ).first()
    return float(band.gpa_points) if band else 0.0


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def recommend_specialization(request):
    student = request.user.student

    # درجات الطالب في المواد المكتملة، مفهرسة بالاسم الإنجليزي للمادة
    history = {
        h.course.name_en: h.numeric_score
        for h in StudentCourseHistory.objects
            .filter(student=student, status='completed')
            .select_related('course')
    }

    # نبني الـ input vector بنفس ترتيب الـ features اللي الموديل اتدرب عليه بالظبط
    feature_vector = [
        _score_to_gpa_points(history[name]) if name in history else 0.0
        for name in _features
    ]

    prediction = _model.predict([feature_vector])[0]
    confidence = round(max(_model.predict_proba([feature_vector])[0]), 3)

    # الـ reason: أعلى مادتين درجة من غير الأصفار (مواد ماخدهاش)
    scored = sorted(
        [(name, val) for name, val in zip(_features, feature_vector) if val > 0],
        key=lambda x: x[1], reverse=True
    )
    top_courses = [name for name, _ in scored[:2]]
    reason = f"أداء قوي في {' و'.join(top_courses)}" if top_courses else "لا توجد بيانات كافية بعد"

    return Response({
        "recommended": prediction,
        "confidence": confidence,
        "reason": reason,
    })