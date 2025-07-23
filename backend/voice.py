import os
import base64
from flask import Flask, request, jsonify
from flask_cors import CORS

# Imports for Google Cloud services
from google.cloud import texttospeech
from google.cloud import speech

# --- CONFIGURATION ---
# This line should be at the top to ensure credentials are set before clients are created.
# os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/Users/anshukumarmandal/Documents/agent/google_json_key.json"

# --- VOICE SERVICE FUNCTIONS ---
# These are the functions that were missing. Now they are defined directly in this file.

def text_to_speech(text: str) -> str:
    """Converts plain text to Base64 encoded audio."""
    try:
        # Instantiates a client
        client = texttospeech.TextToSpeechClient()

        # Set the text input to be synthesized
        synthesis_input = texttospeech.SynthesisInput(text=text)

        # Build the voice request, select a language code ("en-US") and the ssml voice gender
        voice = texttospeech.VoiceSelectionParams(
            language_code="en-IN", ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
        )

        # Select the type of audio file you want returned
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3
        )

        # Perform the text-to-speech request on the text input with the selected
        # voice parameters and audio file type
        response = client.synthesize_speech(
            input=synthesis_input, voice=voice, audio_config=audio_config
        )

        # The response's audio_content is binary. Encode it to Base64
        audio_b64 = base64.b64encode(response.audio_content).decode('utf-8')
        return audio_b64
    except Exception as e:
        print(f"Error in text_to_speech: {e}")
        return None


def speech_to_text(audio_content: bytes) -> str:
    """Transcribes audio content to text."""
    try:
        client = speech.SpeechClient()

        audio = speech.RecognitionAudio(content=audio_content)
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.WEBM_OPUS, # Common encoding from browsers
            sample_rate_hertz=48000, # Common sample rate
            language_code="en-US",
        )

        # Detects speech in the audio file
        response = client.recognize(config=config, audio=audio)

        if response.results:
            return response.results[0].alternatives[0].transcript
        else:
            return ""
    except Exception as e:
        # This handles cases where the audio format might be different.
        # You can add more specific encoding types if needed.
        print(f"Error in speech_to_text: {e}")
        return None

# --- FLASK WEB SERVER ---
# This is your original Flask code, which was already correct.

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

@app.route('/transcribe_audio', methods=['POST'])
def handle_transcribe():
    if 'audio' not in request.files:
        return jsonify({"error": "No audio file"}), 400

    transcribed_text = speech_to_text(request.files['audio'].read())

    if transcribed_text is not None:
        return jsonify({"status": "success", "text": transcribed_text})
    else:
        return jsonify({"status": "error", "message": "Could not transcribe audio"}), 400

@app.route('/synthesize_speech', methods=['POST'])
def handle_synthesize():
    text_to_speak = request.json.get('text')
    if not text_to_speak:
        return jsonify({"error": "No text provided"}), 400

    audio_b64 = text_to_speech(text_to_speak)

    if audio_b64:
        return jsonify({"status": "success", "audio_base64": audio_b64})
    else:
        return jsonify({"status": "error", "message": "Could not generate audio"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)