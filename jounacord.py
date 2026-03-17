import io
import base64
from datetime import datetime

import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import speech_recognition as sr
from deep_translator import GoogleTranslator
from pydub import AudioSegment

from streamlit_webrtc import webrtc_streamer, AudioProcessorBase
import av

st.set_page_config(page_title="jounacord", page_icon="🎙️", layout="wide")

# ---------------- FIREBASE ---------------- #

@st.cache_resource
def init_firebase():
    if not firebase_admin._apps:
        cred = credentials.Certificate(dict(st.secrets["firebase"]))
        firebase_admin.initialize_app(cred)
    return firestore.client()

db = init_firebase()

# ---------------- AUDIO PROCESSOR ---------------- #

class AudioProcessor(AudioProcessorBase):
    def __init__(self):
        self.frames = []

    def recv(self, frame: av.AudioFrame) -> av.AudioFrame:
        self.frames.append(frame.to_ndarray())
        return frame

# ---------------- TRANSCRIPTION ---------------- #

def transcribe_audio(audio: AudioSegment, language_code: str):
    wav_io = io.BytesIO()
    audio.export(wav_io, format="wav")
    wav_io.seek(0)

    recognizer = sr.Recognizer()
    with sr.AudioFile(wav_io) as source:
        data = recognizer.record(source)

    return recognizer.recognize_google(data, language=language_code)

# ---------------- SAVE ---------------- #

def save_record(transcript, translation, audio_bytes):
    db.collection("jounacord_audio").add({
        "transcript": transcript,
        "translation": translation,
        "audio_base64": base64.b64encode(audio_bytes).decode(),
        "created_at": datetime.utcnow().isoformat(),
    })

# ---------------- UI ---------------- #

st.title("🎙️ jounacord (WebRTC Version)")
st.caption("Record → Transcribe → Translate → Save")

# Microphone Recorder
webrtc_ctx = webrtc_streamer(
    key="audio",
    audio_processor_factory=AudioProcessor,
    media_stream_constraints={"audio": True, "video": False},
)

audio_data = None

if webrtc_ctx.audio_processor:
    if st.button("Stop & Process Recording"):
        frames = webrtc_ctx.audio_processor.frames

        if frames:
            # Combine audio frames
            audio_bytes = b"".join([frame.tobytes() for frame in frames])

            audio_data = audio_bytes

# If audio exists
if audio_data:

    audio = AudioSegment(
        data=audio_data,
        sample_width=2,
        frame_rate=48000,
        channels=1
    )

    st.audio(audio_data)

    source_lang = st.text_input("Source language", "en")
    target_lang = st.text_input("Translate to", "es")

    if st.button("Transcribe & Translate"):

        try:
            transcript = transcribe_audio(audio, source_lang)

            translation = GoogleTranslator(
                source=source_lang,
                target=target_lang
            ).translate(transcript)

            st.text_area("Transcript", transcript, height=150)
            st.text_area("Translation", translation, height=150)

            export = io.BytesIO()
            audio.export(export, format="mp3")
            final_audio = export.getvalue()

            st.download_button(
                "Download Audio",
                final_audio,
                file_name="recording.mp3",
                mime="audio/mpeg"
            )

            if st.button("Save to Firebase"):
                save_record(transcript, translation, final_audio)
                st.success("Saved successfully!")

        except Exception as e:
            st.error(str(e))
