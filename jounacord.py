import base64
import io
import json
import urllib.error
import urllib.request
from datetime import datetime
from typing import Any

import firebase_admin
import speech_recognition as sr
import streamlit as st
from deep_translator import GoogleTranslator
from firebase_admin import credentials, firestore
from pydub import AudioSegment

st.set_page_config(page_title="jounacord", page_icon="🎙️", layout="wide")

# ---------------- FIREBASE ---------------- #

def get_web_api_key() -> str | None:
    try:
        return st.secrets["firebase"]["web_api_key"]
    except Exception:
        return None


def init_firebase() -> None:
    if "firebase_initialized" in st.session_state:
        return

    st.session_state.firebase_initialized = False
    st.session_state.db = None

    try:
        admin_config = st.secrets["firebase_admin"]

        if not firebase_admin._apps:
            firebase_admin.initialize_app(
                credentials.Certificate(dict(admin_config))
            )

        st.session_state.db = firestore.client()
        st.session_state.firebase_initialized = True

    except Exception:
        st.session_state.firebase_initialized = False


def firebase_ready() -> bool:
    return bool(
        st.session_state.get("firebase_initialized")
        and st.session_state.get("db")
    )

# ---------------- AUTH ---------------- #

def identity_request(endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
    api_key = get_web_api_key()
    if not api_key:
        raise RuntimeError("Missing firebase.web_api_key in Streamlit secrets.")

    url = f"https://identitytoolkit.googleapis.com/v1/{endpoint}?key={api_key}"

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        details = exc.read().decode("utf-8")
        try:
            error = json.loads(details).get("error", {}).get("message", details)
        except Exception:
            error = details
        raise RuntimeError(error)


def signup_user(email: str, password: str):
    return identity_request(
        "accounts:signUp",
        {"email": email, "password": password, "returnSecureToken": True},
    )


def login_user(email: str, password: str):
    return identity_request(
        "accounts:signInWithPassword",
        {"email": email, "password": password, "returnSecureToken": True},
    )


# ---------------- AUDIO ---------------- #

def transcribe_audio(audio: AudioSegment, language_code: str) -> str:
    wav_io = io.BytesIO()
    audio.export(wav_io, format="wav")
    wav_io.seek(0)

    recognizer = sr.Recognizer()
    with sr.AudioFile(wav_io) as source:
        data = recognizer.record(source)

    return recognizer.recognize_google(data, language=language_code)


# ---------------- SAVE ---------------- #

def save_audio_record(
    user_id: str,
    filename: str,
    original_text: str,
    translated_text: str,
    audio_bytes: bytes,
) -> None:
    if not firebase_ready():
        return

    payload = {
        "user_id": user_id,
        "filename": filename,
        "original_text": original_text,
        "translated_text": translated_text,
        "audio_base64": base64.b64encode(audio_bytes).decode("utf-8"),
        "created_at": datetime.utcnow().isoformat(),
    }

    st.session_state.db.collection("jounacord_audio").add(payload)


# ---------------- UI ---------------- #

def app():

    init_firebase()

    if "user" not in st.session_state:
        st.session_state.user = None

    st.title("🎙️ jounacord")
    st.caption("Transcribe • Translate • Edit • Save to Firebase")

    # -------- AUTH PANEL -------- #

    st.sidebar.subheader("🔐 Authentication")

    if st.session_state.user:
        st.sidebar.success(f"Logged in as {st.session_state.user['email']}")
        if st.sidebar.button("Logout"):
            st.session_state.user = None
            st.rerun()
        return

    mode = st.sidebar.radio("Mode", ["Login", "Sign Up"], horizontal=True)
    email = st.sidebar.text_input("Email")
    password = st.sidebar.text_input("Password", type="password")

    if st.sidebar.button(mode):
        if not email or not password:
            st.sidebar.error("Email and password required.")
        else:
            try:
                if mode == "Login":
                    payload = login_user(email, password)
                else:
                    payload = signup_user(email, password)

                st.session_state.user = {
                    "uid": payload["localId"],
                    "email": payload["email"],
                    "token": payload["idToken"],
                }

                st.rerun()

            except Exception as e:
                st.sidebar.error(str(e))

    if not st.session_state.user:
        st.info("Please login to continue.")
        return

    if not firebase_ready():
        st.warning("Firebase Admin not configured. Cloud saving disabled.")

    # -------- AUDIO UPLOAD -------- #

    uploaded = st.file_uploader(
        "Upload Audio",
        type=["mp3", "wav", "ogg", "m4a"],
    )

    if not uploaded:
        return

    source_audio = AudioSegment.from_file(io.BytesIO(uploaded.read()))
    st.audio(uploaded)

    # -------- TRANSLATION -------- #

    st.subheader("Transcribe & Translate")

    input_lang = st.text_input("Source language code (e.g., en)", "en")
    target_lang = st.text_input("Target language code (e.g., es)", "es")

    if st.button("Process"):

        try:
            original_text = transcribe_audio(source_audio, input_lang)

            translated_text = GoogleTranslator(
                source=input_lang,
                target=target_lang,
            ).translate(original_text)

            st.text_area("Transcript", original_text, height=150)
            st.text_area("Translation", translated_text, height=150)

            export_io = io.BytesIO()
            source_audio.export(export_io, format="mp3")
            audio_bytes = export_io.getvalue()

            st.download_button(
                "Download Audio",
                data=audio_bytes,
                file_name=f"edited_{uploaded.name}.mp3",
                mime="audio/mpeg",
            )

            if st.button("Save to Firebase"):
                save_audio_record(
                    st.session_state.user["uid"],
                    uploaded.name,
                    original_text,
                    translated_text,
                    audio_bytes,
                )
                st.success("Saved successfully!")

        except Exception as e:
            st.error(f"Error: {e}")


if __name__ == "__main__":
    app()
