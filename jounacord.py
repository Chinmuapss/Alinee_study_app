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

SUPPORTED_TRANSLATION_LANGUAGES = {
    "English": "en",
    "Spanish": "es",
    "French": "fr",
    "German": "de",
    "Portuguese": "pt",
    "Indonesian": "id",
    "Arabic": "ar",
    "Hindi": "hi",
    "Japanese": "ja",
    "Korean": "ko",
    "Chinese (Simplified)": "zh-CN",
}


def get_firebase_secrets() -> dict[str, Any] | None:
    try:
        return dict(st.secrets.get("firebase", {}))
    except Exception:
        return None


def init_firebase() -> None:
    if "firebase_initialized" in st.session_state:
        return

    st.session_state.firebase_initialized = False
    st.session_state.db = None

    config = get_firebase_secrets()
    if not config:
        return

    try:
        if not firebase_admin._apps:
            firebase_admin.initialize_app(credentials.Certificate(config))
        st.session_state.db = firestore.client()
        st.session_state.firebase_initialized = True
    except Exception:
        st.session_state.firebase_initialized = False


def firebase_ready() -> bool:
    return bool(st.session_state.get("firebase_initialized", False) and st.session_state.get("db"))


def identity_request(endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
    firebase_config = get_firebase_secrets() or {}
    api_key = firebase_config.get("web_api_key")
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
        except json.JSONDecodeError:
            error = details
        raise RuntimeError(error) from exc


def signup_user(email: str, password: str) -> dict[str, Any]:
    return identity_request("accounts:signUp", {"email": email, "password": password, "returnSecureToken": True})


def login_user(email: str, password: str) -> dict[str, Any]:
    return identity_request("accounts:signInWithPassword", {"email": email, "password": password, "returnSecureToken": True})


def auth_panel() -> None:
    st.sidebar.subheader("🔐 Login")
    if st.session_state.user:
        st.sidebar.success(f"Signed in as {st.session_state.user['email']}")
        if st.sidebar.button("Logout"):
            st.session_state.user = None
            st.rerun()
        return

    mode = st.sidebar.radio("Mode", ["Login", "Sign Up"], horizontal=True)
    email = st.sidebar.text_input("Email")
    password = st.sidebar.text_input("Password", type="password")

    if st.sidebar.button(mode):
        if not email or not password:
            st.sidebar.error("Email and password are required.")
            return
        try:
            payload = login_user(email, password) if mode == "Login" else signup_user(email, password)
            st.session_state.user = {
                "uid": payload["localId"],
                "email": payload["email"],
                "token": payload["idToken"],
            }
            st.sidebar.success(f"{mode} successful")
            st.rerun()
        except Exception as exc:
            st.sidebar.error(str(exc))


def transcribe_audio(audio: AudioSegment, language_code: str) -> str:
    wav_io = io.BytesIO()
    audio.export(wav_io, format="wav")
    wav_io.seek(0)

    recognizer = sr.Recognizer()
    with sr.AudioFile(wav_io) as source:
        data = recognizer.record(source)

    return recognizer.recognize_google(data, language=language_code)


def replace_time_range(base_audio: AudioSegment, replacement_audio: AudioSegment, start_ms: int, end_ms: int) -> AudioSegment:
    prefix = base_audio[:start_ms]
    suffix = base_audio[end_ms:]
    return prefix + replacement_audio + suffix


def remove_time_range(audio: AudioSegment, start_ms: int, end_ms: int) -> AudioSegment:
    return audio[:start_ms] + audio[end_ms:]


def save_audio_record(user_id: str, filename: str, original_text: str, translated_text: str, audio_bytes: bytes) -> None:
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


def app() -> None:
    init_firebase()
    if "user" not in st.session_state:
        st.session_state.user = None

    st.title("🎙️ jounacord")
    st.caption("Journalist-focused audio workflow: transcribe, translate, remove clips, replace clips, and save to Firebase.")

    auth_panel()

    if not st.session_state.user:
        st.info("Please login/sign up from the sidebar to continue.")
        return

    if not firebase_ready():
        st.warning("Firebase admin is not configured. You can still edit/translate audio, but cloud save is disabled.")

    uploaded = st.file_uploader("Upload audio clip", type=["mp3", "wav", "ogg", "m4a"])
    if not uploaded:
        return

    source_audio = AudioSegment.from_file(io.BytesIO(uploaded.read()))
    st.audio(uploaded)

    duration_seconds = round(len(source_audio) / 1000, 2)
    st.write(f"Duration: {duration_seconds} seconds")

    st.subheader("1) Edit audio")
    start_sec = st.number_input("Start second", min_value=0.0, max_value=float(duration_seconds), value=0.0, step=0.1)
    end_sec = st.number_input("End second", min_value=0.0, max_value=float(duration_seconds), value=min(2.0, float(duration_seconds)), step=0.1)

    edited_audio = source_audio
    col1, col2 = st.columns(2)

    with col1:
        if st.button("Remove selected part"):
            if end_sec <= start_sec:
                st.error("End second must be greater than start second.")
            else:
                edited_audio = remove_time_range(source_audio, int(start_sec * 1000), int(end_sec * 1000))
                st.success("Selected segment removed.")

    with col2:
        replacement = st.file_uploader("Replacement clip", type=["mp3", "wav", "ogg", "m4a"], key="replacement")
        if st.button("Replace selected part"):
            if not replacement:
                st.error("Upload a replacement clip first.")
            elif end_sec <= start_sec:
                st.error("End second must be greater than start second.")
            else:
                replacement_audio = AudioSegment.from_file(io.BytesIO(replacement.read()))
                edited_audio = replace_time_range(source_audio, replacement_audio, int(start_sec * 1000), int(end_sec * 1000))
                st.success("Selected segment replaced.")

    st.subheader("2) Transcribe + translate")
    input_lang_name = st.selectbox("Audio language", list(SUPPORTED_TRANSLATION_LANGUAGES.keys()), index=0)
    target_lang_name = st.selectbox("Translate to", list(SUPPORTED_TRANSLATION_LANGUAGES.keys()), index=1)

    if st.button("Transcribe and translate"):
        try:
            original_text = transcribe_audio(edited_audio, SUPPORTED_TRANSLATION_LANGUAGES[input_lang_name])
            translated_text = GoogleTranslator(
                source=SUPPORTED_TRANSLATION_LANGUAGES[input_lang_name],
                target=SUPPORTED_TRANSLATION_LANGUAGES[target_lang_name],
            ).translate(original_text)
            st.text_area("Transcript", value=original_text, height=140)
            st.text_area("Translation", value=translated_text, height=140)

            export_io = io.BytesIO()
            edited_audio.export(export_io, format="mp3")
            audio_bytes = export_io.getvalue()

            st.download_button("Download edited audio", data=audio_bytes, file_name=f"edited_{uploaded.name}.mp3", mime="audio/mpeg")

            if st.button("Save audio + transcript to Firebase"):
                save_audio_record(
                    st.session_state.user["uid"],
                    uploaded.name,
                    original_text,
                    translated_text,
                    audio_bytes,
                )
                st.success("Saved to Firebase collection: jounacord_audio")
        except Exception as exc:
            st.error(f"Failed to transcribe/translate: {exc}")


if __name__ == "__main__":
    app()
