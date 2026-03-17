import io
import json
import base64
import urllib.request
import urllib.error
from datetime import datetime

import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import speech_recognition as sr
from deep_translator import GoogleTranslator
from pydub import AudioSegment
from streamlit_audiorec import st_audiorec

st.set_page_config(page_title="jounacord", page_icon="🎙️", layout="wide")

# ---------------- FIREBASE ADMIN ---------------- #

@st.cache_resource
def init_firebase():
    if not firebase_admin._apps:
        cred = credentials.Certificate(dict(st.secrets["firebase"]))
        firebase_admin.initialize_app(cred)
    return firestore.client()

db = init_firebase()

# ---------------- AUTH ---------------- #

def get_api_key():
    return st.secrets["firebase_web"]["web_api_key"]

def firebase_auth(endpoint, payload):
    api_key = get_api_key()
    url = f"https://identitytoolkit.googleapis.com/v1/{endpoint}?key={api_key}"

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req) as res:
            return json.loads(res.read())
    except urllib.error.HTTPError as e:
        raise RuntimeError(e.read().decode())

def signup(email, password):
    return firebase_auth("accounts:signUp", {
        "email": email,
        "password": password,
        "returnSecureToken": True
    })

def login(email, password):
    return firebase_auth("accounts:signInWithPassword", {
        "email": email,
        "password": password,
        "returnSecureToken": True
    })

# ---------------- AUDIO ---------------- #

def transcribe(audio: AudioSegment, lang: str):
    wav = io.BytesIO()
    audio.export(wav, format="wav")
    wav.seek(0)

    recognizer = sr.Recognizer()
    with sr.AudioFile(wav) as source:
        data = recognizer.record(source)

    return recognizer.recognize_google(data, language=lang)

# ---------------- SAVE ---------------- #

def save_record(user_id, transcript, translation, audio_bytes):
    db.collection("jounacord_audio").add({
        "user_id": user_id,
        "transcript": transcript,
        "translation": translation,
        "audio_base64": base64.b64encode(audio_bytes).decode(),
        "created_at": datetime.utcnow().isoformat(),
    })

# ---------------- SESSION ---------------- #

if "user" not in st.session_state:
    st.session_state.user = None

# ---------------- LOGIN UI ---------------- #

st.sidebar.title("🔐 Login")

if not st.session_state.user:

    mode = st.sidebar.radio("Mode", ["Login", "Sign Up"])
    email = st.sidebar.text_input("Email")
    password = st.sidebar.text_input("Password", type="password")

    if st.sidebar.button("Submit"):
        try:
            if mode == "Login":
                result = login(email, password)
            else:
                result = signup(email, password)

            st.session_state.user = {
                "uid": result["localId"],
                "email": result["email"],
                "token": result["idToken"],
            }

            st.rerun()

        except Exception as e:
            st.sidebar.error(str(e))

    st.stop()

else:
    st.sidebar.success(f"Logged in as {st.session_state.user['email']}")
    if st.sidebar.button("Logout"):
        st.session_state.user = None
        st.rerun()

# ---------------- MAIN APP ---------------- #

st.title("🎙️ jounacord")

mode = st.radio("Input Method", ["Upload", "Record"])

audio_data = None

if mode == "Upload":
    uploaded = st.file_uploader("Upload Audio", type=["mp3","wav","ogg","m4a"])
    if uploaded:
        audio_data = uploaded.read()
        st.audio(audio_data)

if mode == "Record":
    st.write("Click record 🎤")
    recorded = st_audiorec()
    if recorded:
        audio_data = recorded
        st.audio(audio_data)

if audio_data:

    source_lang = st.text_input("Source language", "en")
    target_lang = st.text_input("Translate to", "es")

    if st.button("Process"):

        try:
            audio = AudioSegment.from_file(io.BytesIO(audio_data))

            transcript = transcribe(audio, source_lang)

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
                file_name="audio.mp3",
                mime="audio/mpeg"
            )

            if st.button("Save to Firebase"):
                save_record(
                    st.session_state.user["uid"],
                    transcript,
                    translation,
                    final_audio
                )
                st.success("Saved successfully!")

        except Exception as e:
            st.error(str(e))
