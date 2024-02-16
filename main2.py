import os
import uuid
import subprocess
from flask import Flask, request, jsonify, render_template
from google.cloud import speech, storage, secretmanager
from waitress import serve  # Import the serve function
from gunicorn import util


app = Flask(__name__)

LOCAL_UPLOADS_FOLDER = "uploads"

# Ensure these directories exist
os.makedirs(LOCAL_UPLOADS_FOLDER, exist_ok=True)

def access_secret_version(secret_id, version_id="latest"):
    """Accesses the payload of the secret version."""
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT_ID")  # This must match the environment variable you set
    if not project_id:
        raise Exception("The environment variable GOOGLE_CLOUD_PROJECT_ID is not set.")
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{project_id}/secrets/{secret_id}/versions/{version_id}"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8")
y
def get_storage_client():
    return storage.Client()

def get_speech_client():
    return speech.SpeechClient()

@app.route('/')
def index():
    return render_template('index.html')

def upload_blob(bucket_name, source_file_path, destination_blob_name):
    """Uploads a file to the specified bucket."""
    storage_client = get_storage_client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)
    try:
        blob.upload_from_filename(source_file_path)
        print(f"File {source_file_path} uploaded to {destination_blob_name}.")
    except Exception as e:
        print(f"Failed to upload to Google Cloud Storage: {e}")
        raise

@app.route('/upload', methods=['POST'])
def upload_audio():
    OPENAI_API_KEY = access_secret_version("webaikey")
    BUCKET_NAME = access_secret_version("audioforweb")

    file = request.files.get('audioFile')
    if not file:
        return jsonify({'error': 'No audio file provided'}), 400

    unique_id = uuid.uuid4().hex
    raw_local_filename = f"{unique_id}_raw.wav"
    raw_local_filepath = os.path.join(LOCAL_UPLOADS_FOLDER, raw_local_filename)
    file.save(raw_local_filepath)

    local_filename = f"{unique_id}.wav"
    local_filepath = os.path.join(LOCAL_UPLOADS_FOLDER, local_filename)
    ffmpeg_command = [
        'ffmpeg', '-i', raw_local_filepath,
        '-acodec', 'pcm_s16le', '-ar', '44100', '-ac', '1', local_filepath
    ]
    subprocess.run(ffmpeg_command, check=True)

    cloud_filename = f"audio/{local_filename}"
    upload_blob(BUCKET_NAME, local_filepath, cloud_filename)

    transcript = transcribe_audio(f"gs://{BUCKET_NAME}/{cloud_filename}", OPENAI_API_KEY)
    
    transcript_filename = f"{unique_id}_transcript.txt"
    transcript_filepath = os.path.join(LOCAL_UPLOADS_FOLDER, transcript_filename)
    with open(transcript_filepath, 'w') as transcript_file:
        transcript_file.write(transcript)
    upload_blob(BUCKET_NAME, transcript_filepath, f"transcripts/{transcript_filename}")

    summary = summarize_text(transcript, OPENAI_API_KEY)

    summary_filename = f"{unique_id}_summary.txt"
    summary_filepath = os.path.join(LOCAL_UPLOADS_FOLDER, summary_filename)
    with open(summary_filepath, 'w') as summary_file:
        summary_file.write(summary)
    upload_blob(BUCKET_NAME, summary_filepath, f"summaries/{summary_filename}")
    
    return jsonify({'transcript': transcript, 'summary': summary})

def transcribe_audio(gcs_uri, api_key):
    """Transcribes the given audio file using Google Cloud Speech-to-Text."""
    client = get_speech_client()
    audio = speech.RecognitionAudio(uri=gcs_uri)
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=44100,
        language_code="en-US",
        enable_automatic_punctuation=True
    )

    operation = client.long_running_recognize(config=config, audio=audio)
    response = operation.result(timeout=90)

    return " ".join(result.alternatives[0].transcript for result in response.results)

def summarize_text(text, api_key):
    import openai
    openai.api_key = api_key
    response = openai.Completion.create(
        engine="gpt-3.5-turbo-instruct",
        prompt=f"Summarize this text: {text}",
        temperature=0.7,
        max_tokens=150,
        top_p=1.0,
        frequency_penalty=0.0,
        presence_penalty=0.0
    )
    return response.choices[0].text.strip()

if __name__ == "__main__":
    serve(app, host="0.0.0.0", port=8080)
