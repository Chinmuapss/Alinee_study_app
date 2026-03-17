import base64
import hashlib
import io
from datetime import datetime

import firebase_admin
import speech_recognition as sr
import streamlit as st
from deep_translator import GoogleTranslator
from firebase_admin import credentials, firestore
from pydub import AudioSegment, effects


st.set_page_config("JounaCord Studio", page_icon="🎙️", layout="wide")


@st.cache_resource
def init_firebase():
    if not firebase_admin._apps:
        cred = credentials.Certificate(dict(st.secrets["firebase"]))
        firebase_admin.initialize_app(cred)
    return firestore.client()


try:
    db = init_firebase()
except Exception as exc:
    st.error(f"Firebase initialization failed. Add valid firebase secrets to run the app: {exc}")
    st.stop()


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def create_user(username: str, password: str) -> tuple[bool, str]:
    existing = db.collection("jounacord_users").where("username", "==", username).limit(1).stream()
    if any(existing):
        return False, "Username already exists. Please choose another username."

    db.collection("jounacord_users").add(
        {
            "username": username,
            "password_hash": hash_password(password),
            "created_at": datetime.utcnow(),  # optional but good
        }
    )
    return True, "Account created successfully. Please log in."


def authenticate_user(username: str, password: str) -> bool:
    users = db.collection("jounacord_users").where("username", "==", username).limit(1).stream()
    user_doc = next(users, None)
    if not user_doc:
        return False

    data = user_doc.to_dict()
    return data.get("password_hash") == hash_password(password)


def audiosegment_to_bytes(audio: AudioSegment, export_format: str = "mp3") -> bytes:
    export_buffer = io.BytesIO()
    audio.export(export_buffer, format=export_format)
    return export_buffer.getvalue()


def transcribe_and_translate(audio: AudioSegment, source_lang: str, target_lang: str) -> tuple[str, str]:
    try:
        wav_io = io.BytesIO()
        audio.set_channels(1).set_frame_rate(16000).export(wav_io, format="wav")
        wav_io.seek(0)

        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_io) as source:
            recorded_audio = recognizer.record(source)

        transcript = recognizer.recognize_google(recorded_audio, language=source_lang)
    except Exception as e:
        transcript = f"[Transcription failed: {e}]"

    try:
        translation = GoogleTranslator(source=source_lang, target=target_lang).translate(transcript)
    except Exception as e:
        translation = f"[Translation failed: {e}]"

    return transcript, translation


def overlay_or_replace_segment(
    audio: AudioSegment,
    start_ms: int,
    end_ms: int,
    replacement_audio: AudioSegment | None,
) -> AudioSegment:
    if start_ms >= end_ms:
        return audio

    if replacement_audio is None:
        replacement_segment = AudioSegment.silent(duration=end_ms - start_ms)
    else:
        replacement_segment = replacement_audio.set_channels(audio.channels).set_frame_rate(audio.frame_rate)
        replacement_segment = replacement_segment[: end_ms - start_ms]
        if len(replacement_segment) < end_ms - start_ms:
            replacement_segment += AudioSegment.silent(duration=(end_ms - start_ms) - len(replacement_segment))

    return audio[:start_ms] + replacement_segment + audio[end_ms:]


def apply_audio_edits(
    audio: AudioSegment,
    enhance_audio: bool,
    speed_factor: float,
    replace_segment: bool,
    replace_start_sec: float,
    replace_end_sec: float,
    replacement_audio: AudioSegment | None,
    trim_start_sec: float,
    trim_end_sec: float,
    reverse_audio: bool,
) -> AudioSegment:
    edited = audio

    if enhance_audio:
        edited = effects.normalize(edited)
        edited = edited.high_pass_filter(100)
        edited = edited + 5

    if speed_factor != 1.0:
        edited = edited._spawn(edited.raw_data, overrides={"frame_rate": int(edited.frame_rate * speed_factor)})
        edited = edited.set_frame_rate(audio.frame_rate)

    start_trim_ms = max(0, int(trim_start_sec * 1000))
    end_trim_ms = max(0, int(trim_end_sec * 1000))
    if start_trim_ms + end_trim_ms < len(edited):
        edited = edited[start_trim_ms : len(edited) - end_trim_ms]

    if replace_segment:
        start_ms = max(0, int(replace_start_sec * 1000))
        end_ms = min(len(edited), int(replace_end_sec * 1000))
        edited = overlay_or_replace_segment(edited, start_ms, end_ms, replacement_audio)

    if reverse_audio:
        edited = edited.reverse()

    return edited


def save_audio_record(user: str, title: str, original_filename: str, audio_bytes: bytes, transcript: str, translation: str, edits: dict):
    db.collection("jounacord_audio").add(
        {
            "user": user,
            "title": title,
            "original_filename": original_filename,
            "transcript": transcript,
            "translation": translation,
            "created_at": datetime.utcnow(),  # ✅ FIXED
            "audio_base64": base64.b64encode(audio_bytes).decode("utf-8"),
            "edits": edits,
        }
    )

def get_user_audio_records(user: str) -> list[dict]:
    try:
        docs = (
            db.collection("jounacord_audio")
            .where("user", "==", user)
            .order_by("created_at", direction=firestore.Query.DESCENDING)
            .stream()
        )
        return [doc.to_dict() for doc in docs]
    except Exception as e:
        import traceback
        st.error(f"Firestore error:\n{traceback.format_exc()}")
        return []


if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "user" not in st.session_state:
    st.session_state.user = ""


if not st.session_state.logged_in:
    st.title("🎙️ JounaCord Studio")
    st.caption("Record or upload voice/music, translate content, edit audio, and save everything to Firebase.")

    auth_tab_login, auth_tab_signup = st.tabs(["Login", "Sign Up"])

    with auth_tab_login:
        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")

        if st.button("Login", type="primary"):
            if authenticate_user(username.strip(), password):
                st.session_state.logged_in = True
                st.session_state.user = username.strip()
                st.success("Logged in successfully.")
                st.rerun()
            else:
                st.error("Invalid username or password.")

    with auth_tab_signup:
        new_username = st.text_input("Create Username", key="signup_username")
        new_password = st.text_input("Create Password", type="password", key="signup_password")
        confirm_password = st.text_input("Confirm Password", type="password", key="signup_password_confirm")

        if st.button("Sign Up"):
            if not new_username.strip() or not new_password:
                st.error("Username and password are required.")
            elif new_password != confirm_password:
                st.error("Passwords do not match.")
            else:
                success, message = create_user(new_username.strip(), new_password)
                if success:
                    st.success(message)
                else:
                    st.error(message)

    st.stop()


st.title("🎙️ JounaCord Studio")
st.success(f"Welcome, {st.session_state.user}")

if st.button("Logout"):
    st.session_state.logged_in = False
    st.session_state.user = ""
    st.rerun()

create_tab, dashboard_tab = st.tabs(["Create / Edit Audio", "Dashboard"])

with create_tab:
    st.subheader("1) Add audio")

    captured_audio_bytes = None
    if hasattr(st, "audio_input"):
        captured_audio = st.audio_input("Record audio (voice/music)")
        if captured_audio:
            captured_audio_bytes = captured_audio.read()

    uploaded_file = st.file_uploader("Or upload audio", type=["wav", "mp3", "ogg", "m4a", "flac"], key="main_audio_uploader")

    raw_audio_bytes = captured_audio_bytes
    original_filename = "recorded_audio.wav"

    if uploaded_file is not None:
        raw_audio_bytes = uploaded_file.read()
        original_filename = uploaded_file.name

    if raw_audio_bytes:
        st.audio(raw_audio_bytes)

        st.subheader("2) Configure translation")
        language_options = {
            "English": "en",
            "Spanish": "es",
            "French": "fr",
            "German": "de",
            "Italian": "it",
            "Filipino": "tl",
            "Japanese": "ja",
            "Korean": "ko",
            "Chinese (Simplified)": "zh-CN",
            "Arabic": "ar",
            "Hindi": "hi",
        }
        source_lang_name = st.selectbox("Source language", options=list(language_options), index=0)
        target_lang_name = st.selectbox("Target language", options=list(language_options), index=1)
        source_lang = language_options[source_lang_name]
        target_lang = language_options[target_lang_name]

        st.subheader("3) Audio manipulation")
        enhance_audio = st.checkbox("Enhance audio (normalize + clarity boost)", value=True)
        speed_factor = st.slider("Playback speed", min_value=0.5, max_value=1.5, value=1.0, step=0.1)

        replace_segment = st.checkbox("Replace a segment with silence")
        replace_start = st.number_input("Replace start (seconds)", min_value=0.0, value=0.0, step=0.5)
        replace_end = st.number_input("Replace end (seconds)", min_value=0.0, value=2.0, step=0.5)
        replacement_file = st.file_uploader(
            "Optional: upload replacement audio for that segment",
            type=["wav", "mp3", "ogg", "m4a", "flac"],
            key="replacement_audio_uploader",
        )
        trim_start = st.number_input("Trim from start (seconds)", min_value=0.0, value=0.0, step=0.5)
        trim_end = st.number_input("Trim from end (seconds)", min_value=0.0, value=0.0, step=0.5)
        reverse_audio = st.checkbox("Reverse final audio", value=False)

        title = st.text_input("Audio title", value="My audio")

        if st.button("Process, Translate, and Save", type="primary"):
            try:
                source_audio = AudioSegment.from_file(io.BytesIO(raw_audio_bytes))
                replacement_segment = (
                    AudioSegment.from_file(io.BytesIO(replacement_file.read())) if replacement_file is not None else None
                )
                edited_audio = apply_audio_edits(
                    audio=source_audio,
                    enhance_audio=enhance_audio,
                    speed_factor=speed_factor,
                    replace_segment=replace_segment,
                    replace_start_sec=replace_start,
                    replace_end_sec=replace_end,
                    replacement_audio=replacement_segment,
                    trim_start_sec=trim_start,
                    trim_end_sec=trim_end,
                    reverse_audio=reverse_audio,
                )

                transcript, translation = transcribe_and_translate(edited_audio, source_lang, target_lang)
                final_audio_bytes = audiosegment_to_bytes(edited_audio, export_format="mp3")

                st.subheader("Transcript")
                st.write(transcript)
                st.subheader("Translation")
                st.write(translation)
                st.audio(final_audio_bytes)

                save_audio_record(
                    user=st.session_state.user,
                    title=title,
                    original_filename=original_filename,
                    audio_bytes=final_audio_bytes,
                    transcript=transcript,
                    translation=translation,
                    edits={
                        "enhance_audio": enhance_audio,
                        "speed_factor": speed_factor,
                        "replace_segment": replace_segment,
                        "replace_start_sec": replace_start,
                        "replace_end_sec": replace_end,
                        "replacement_audio_uploaded": replacement_file is not None,
                        "trim_start_sec": trim_start,
                        "trim_end_sec": trim_end,
                        "reverse_audio": reverse_audio,
                    },
                )
                st.success("Audio processed and saved to Firebase.")
            except Exception as exc:
                st.error(f"Unable to process audio: {exc}")

with dashboard_tab:
    st.subheader("Saved audios")
    user_records = get_user_audio_records(st.session_state.user)

    if not user_records:
        st.info("No saved audios yet.")
    else:
        for idx, record in enumerate(user_records, start=1):
            with st.expander(f"{idx}. {record.get('title', 'Untitled')} • {record.get('created_at', '')}"):
                st.write(f"**Original file:** {record.get('original_filename', 'N/A')}")
                st.write(f"**Transcript:** {record.get('transcript', '')}")
                st.write(f"**Translation:** {record.get('translation', '')}")
                st.json(record.get("edits", {}))

                audio_b64 = record.get("audio_base64")
                if audio_b64:
                    st.audio(base64.b64decode(audio_b64), format="audio/mp3")
