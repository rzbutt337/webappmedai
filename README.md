Speech-to-Text & EHR Summarizer

This is a small Flask web app that lets you:

1. Upload an audio file
2. Convert it to the right format with ffmpeg
3. Save it to Google Cloud Storage
4. Transcribe it with Google Speech-to-Text
5. Summarize it into an Electronic Health Record–style note using OpenAI
6. Store both the transcript and summary back in Google Cloud

---
What You’ll Need

- Python 3.10+
- ffmpeg installed
- Google Cloud project with:
  - Storage bucket
  - Speech-to-Text API enabled
  - Service account with Speech-to-Text + Storage permissions
- OpenAI API key

---
Environment Variables

BUCKET_NAME - Your Google Cloud Storage bucket name
OPENAI_API_KEY - Your OpenAI key
GOOGLE_CLOUD_CREDENTIALS_B64 - Base64-encoded service account JSON

Base64 encode your service account JSON:
Mac / Linux:
base64 -w0 service-account.json
Windows PowerShell:
[Convert]::ToBase64String([IO.File]::ReadAllBytes("service-account.json"))

---
Install & Run

1. Clone the project
2. Create virtual env + install dependencies:
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
3. Set environment variables:
   export BUCKET_NAME="your-bucket"
   export OPENAI_API_KEY="your-key"
   export GOOGLE_CLOUD_CREDENTIALS_B64="base64-string"
4. Start the app:
   python app.py
5. Visit http://localhost:5000

---
How to Use

- Upload audio file on homepage
- Wait for processing
- Get transcript + EHR summary

---
Where Files Go in Google Cloud Storage

audio/<uuid>.wav
transcripts/<uuid>_transcript.txt
summaries/<uuid>_summary.txt

---
Notes

- This is a demo — follow privacy laws for real data.
- For production, use gunicorn or Cloud Run.
- Large files may take longer to process.
