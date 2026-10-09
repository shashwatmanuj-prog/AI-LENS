
from google import genai
from app.config import get_settings

settings = get_settings()

print("Model:", settings.gemma_model)
print("API key configured:", bool(settings.gemini_api_key))

try:
    client = genai.Client(
        api_key=settings.gemini_api_key,
        http_options={"timeout": 30000},
    )

    response = client.models.generate_content(
        model=settings.gemma_model,
        contents="Reply with exactly: Gemma works",
    )

    print("SUCCESS:", response.text)

except Exception as exc:
    print("ERROR TYPE:", type(exc).__name__)
    print("ERROR DETAILS:", str(exc))
