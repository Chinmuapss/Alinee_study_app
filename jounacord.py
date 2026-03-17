import io
import base64
from datetime import datetime

import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import speech_recognition as sr
from deep_translator import GoogleTranslator
from pydub import AudioSegment

st.set_page_config(page_title="jounacord", page_icon="🎙️", layout="wide")

# ---------------- FIREBASE ---------------- #

@st.cache_resource
def init_firebase():
    if not firebase_admin._apps:
        cred = credentials.Certificate(dict(st.secrets["firebase"]))
        firebase_admin.initialize_app(cred)
    return firestore.client()

db = init_firebase()

# ---------------- AUDIO FUNCTIONS ---------------- #

def transcribe_audio(audio: AudioSegment, language_code: str) -> str:
    wav_io = io.BytesIO()
    audio.export(wav_io, format="wav")
    wav_io.seek(0)

    recognizer = sr.Recognizer()
    with sr.AudioFile(wav_io) as source:
        data = recognizer.record(source)

    return recognizer.recognize_google(data, language=language_code)


def save_to_firestore(filename, transcript, translation, audio_bytes):
    payload = {
        "filename": filename,
        "transcript": transcript,
        "translation": translation,
        "audio_base64": base64.b64encode(audio_bytes).decode("utf-8"),
        "created_at": datetime.utcnow().isoformat(),
    }

    db.collection("jounacord_audio").add(payload)

# ---------------- UI ---------------- #

st.title("🎙️ jounacord")
st.caption("Upload → Transcribe → Translate → Save to Firebase")

uploaded = st.file_uploader("Upload Audio", type=["mp3", "wav", "ogg", "m4a"])

if uploaded:

    audio = AudioSegment.from_file(io.BytesIO(uploaded.read()))
    st.audio(uploaded)

    st.subheader("Transcription")

    source_lang = st.text_input("Source language code", "en")
    target_lang = st.text_input("Translate to language code", "es")

    if st.button("Process"):

        try:
            transcript = transcribe_audio(audio, source_lang)

            translation = GoogleTranslator(
                source=source_lang,
                target=target_lang
            ).translate(transcript)

            st.text_area("Transcript", transcript, height=150)
            st.text_area("Translation", translation, height=150)

            export_io = io.BytesIO()
            audio.export(export_io, format="mp3")
            audio_bytes = export_io.getvalue()

            st.download_button(
                "Download Edited Audio",
                data=audio_bytes,
                file_name=f"edited_{uploaded.name}.mp3",
                mime="audio/mpeg"
            )

            if st.button("Save to Firebase"):
                save_to_firestore(
                    uploaded.name,
                    transcript,
                    translation,
                    audio_bytes
                )
                st.success("Saved to Firestore successfully!")

        except Exception as e:
            st.error(f"Error: {e}")
