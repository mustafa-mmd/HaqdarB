import vertexai
from vertexai.generative_models import GenerativeModel
import os

PROJECT_ID = "haqdar-ai"
LOCATION = "us-central1"

vertexai.init(project=PROJECT_ID, location=LOCATION)

models_to_test = [
    "gemini-2.5-flash",
    "gemini-2.5-pro",
    "gemini-2.5-flash-001",
    "gemini-3-flash",
]

for model_name in models_to_test:
    try:
        model = GenerativeModel(model_name)
        response = model.generate_content("hello")
        print(f"{model_name}: OK")
    except Exception as e:
        print(f"{model_name}: FAILED - {e}")
