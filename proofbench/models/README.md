# Models

Models are provider-independent behind `base.py`. The default real provider is Gemini through the official `google-genai` SDK. Mock providers exist for smoke tests and CI-like local checks.

Set `GEMINI_API_KEY` before running the real provider.

