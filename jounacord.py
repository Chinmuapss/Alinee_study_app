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

# ---------------- PAGE ---------------- #

st.set_page_config("jounacord", page_icon="🎙️", layout="wide")

# ---------------- FIREBASE ---------------- #

@st.cache_resource
def init_firebase():
    if not firebase_admin._apps:
        cred = credentials.Certificate(dict(st.secrets["firebase"]))
        firebase_admin.initialize_app(cred)
    return firestore.client()

db = init_firebase()

# ---------------- LOGIN SYSTEM ---------------- #

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# -------- LOGIN PAGE -------- #

if not st.session_state.logged_in:

    st.title("🎙️ jounacord")
    st.subheader("Please Login to Continue")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):

        # Simple demo login (you can upgrade later)
        if username and password:
            st.session_state.logged_in = True
            st.session_state.user = username
            st.rerun()
        else:
            st.error("Please enter username and password")

    st.stop()  # Prevent app from loading until logged in

# ---------------- MAIN APP ---------------- #

st.title("🎙️ jounacord")
st.success(f"Welcome {st.session_state.user}")

if st.button("Logout"):
    st.session_state.logged_in = False
    st.rerun()

# ---------------- AUDIO RECORDING ---------------- #

class AudioProcessor(AudioProcessorBase):
    def __init__(self):
        self.frames = []

    def recv(self, frame: av.AudioFrame) -> av.AudioFrame:
        self.frames.append(frame.to_ndarray())
        return frame

webrtc_ctx = webrtc_streamer(
    key="record",
    audio_processor_factory=AudioProcessor,
    media_stream_constraints={"audio": True, "video": False},
)

audio_data = None

if webrtc_ctx.audio_processor:
    if st.button("Stop Recording"):
        frames = webrtc_ctx.audio_processor.frames
        if frames:
            audio_data = b"".join([frame.tobytes() for frame in frames])

# ---------------- PROCESS ---------------- #

if audio_data:

    st.audio(audio_data)

    source_lang = st.text_input("Source language", "en")
    target_lang = st.text_input("Translate to", "es")

    if st.button("Transcribe & Translate"):

        try:
            audio = AudioSegment(
                data=audio_data,
                sample_width=2,
                frame_rate=48000,
                channels=1
            )

            wav_io = io.BytesIO()
            audio.export(wav_io, format="wav")
            wav_io.seek(0)

            recognizer = sr.Recognizer()
            with sr.AudioFile(wav_io) as source:
                data = recognizer.record(source)

            transcript = recognizer.recognize_google(
                data,
                language=source_lang
            )

            translation = GoogleTranslator(
                source=source_lang,
                target=target_lang
            ).translate(transcript)

            st.subheader("Transcript")
            st.write(transcript)

            st.subheader("Translation")
            st.write(translation)

            # Save to Firebase
            export = io.BytesIO()
            audio.export(export, format="mp3")
            final_audio = export.getvalue()

            db.collection("jounacord_audio").add({
                "user": st.session_state.user,
                "transcript": transcript,
                "translation": translation,
                "created_at": datetime.utcnow().isoformat(),
                "audio_base64": base64.b64encode(final_audio).decode()
            })

            st.success("Saved to Firebase!")

        except Exception as e:
            st.error(str(e))
