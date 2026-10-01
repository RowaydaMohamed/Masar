import os
import joblib
from django.conf import settings

model_path = os.path.join(settings.BASE_DIR, 'ai_models', 'specialization_model (3).joblib')
SAVED_DATA = joblib.load(model_path)
AI_MODEL = SAVED_DATA['model']

def predict_specialization(grades_list):
    prediction = AI_MODEL.predict([grades_list])
    
    return prediction[0]