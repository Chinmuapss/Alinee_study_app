import base64
import hashlib
import io
from datetime import datetime, timezone

import speech_recognition as sr
import streamlit as st
from deep_translator import GoogleTranslator
from pydub import AudioSegment, effects
from supabase import Client, create_client


st.set_page_config("JounaCord Studio", page_icon="🎙️", layout="wide")


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


@st.cache_resource
def init_supabase() -> Client:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["anon_key"]
    return create_client(url, key)


try:
    supabase = init_supabase()
except Exception as exc:
    st.error(f"Supabase initialization failed. Add valid supabase secrets to run the app: {exc}")
    st.stop()


def create_user(username: str, password: str) -> tuple[bool, str]:
    existing = (
        supabase.table("profiles")
        .select("id")
        .eq("username", username)
        .limit(1)
        .execute()
    )
    if existing.data:
        return False, "Username already exists. Please choose another username."

    auth_response = supabase.auth.sign_up(
        {
            "email": f"{username}@jounacord.local",
            "password": password,
            "options": {
                "data": {
                    "username": username,
                }
            },
        }
    )

    user = auth_response.user
    if not user:
        return False, "Unable to create account. Please try again."

    supabase.table("profiles").upsert(
        {
            "id": user.id,
            "username": username,
            "password_hash": hash_password(password),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    ).execute()

    return True, "Account created successfully. Please log in."


def authenticate_user(username: str, password: str) -> tuple[bool, str | None]:
    profile = (
        supabase.table("profiles")
        .select("id,password_hash")
        .eq("username", username)
        .limit(1)
        .execute()
    )

    if not profile.data:
        return False, None

    row = profile.data[0]
    if row.get("password_hash") != hash_password(password):
        return False, None

    user_id = row["id"]
    return True, user_id


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
    except Exception as exc:
        transcript = f"[Transcription failed: {exc}]"

    try:
        translation = GoogleTranslator(source=source_lang, target=target_lang).translate(transcript)
    except Exception as exc:
        translation = f"[Translation failed: {exc}]"

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


def save_audio_record(
    user_id: str,
    title: str,
    original_filename: str,
    audio_bytes: bytes,
    transcript: str,
    translation: str,
    edits: dict,
):
    supabase.table("audio_records").insert(
        {
            "user_id": user_id,
            "title": title,
            "original_filename": original_filename,
            "transcript": transcript,
            "translation": translation,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "audio_base64": base64.b64encode(audio_bytes).decode("utf-8"),
            "edits": edits,
        }
    ).execute()


def get_user_audio_records(user_id: str) -> list[dict]:
    try:
        response = (
            supabase.table("audio_records")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .execute()
        )
        return response.data or []
    except Exception as exc:
        st.error(f"Supabase error: {exc}")
        return []


if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user" not in st.session_state:
    st.session_state.user = ""
if "user_id" not in st.session_state:
    st.session_state.user_id = ""


if not st.session_state.logged_in:
    st.title("🎙️ JounaCord Studio")
    st.caption("Record or upload voice, translate content, and save everything to Supabase.")

    auth_tab_login, auth_tab_signup = st.tabs(["Login", "Sign Up"])

    with auth_tab_login:
        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")

        if st.button("Login", type="primary"):
            ok, user_id = authenticate_user(username.strip(), password)
            if ok and user_id:
                st.session_state.logged_in = True
                st.session_state.user = username.strip()
                st.session_state.user_id = user_id
                st.success("Logged in successfully.")
                st.rerun()
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
st.caption("Your saved recordings are tied to your account and will remain after logout/login.")

if st.button("Logout"):
    st.session_state.logged_in = False
    st.session_state.user = ""
    st.session_state.user_id = ""
    st.rerun()

create_tab, dashboard_tab = st.tabs(["Record + Translate", "My Saved Audio"])

with create_tab:
    st.subheader("1) Add audio")

    captured_audio_bytes = None
    if hasattr(st, "audio_input"):
        captured_audio = st.audio_input("Record audio")
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

        title = st.text_input("Audio title", value="My audio")

        if st.button("Translate and Save", type="primary"):
            try:
                source_audio = AudioSegment.from_file(io.BytesIO(raw_audio_bytes))
                transcript, translation = transcribe_and_translate(source_audio, source_lang, target_lang)
                final_audio_bytes = audiosegment_to_bytes(source_audio, export_format="mp3")

                st.subheader("Transcript")
                st.write(transcript)
                st.subheader("Translation")
                st.write(translation)
                st.audio(final_audio_bytes)

                save_audio_record(
                    user_id=st.session_state.user_id,
                    title=title,
                    original_filename=original_filename,
                    audio_bytes=final_audio_bytes,
                    transcript=transcript,
                    translation=translation,
                    edits={
                        "source_lang": source_lang,
                        "target_lang": target_lang,
                    },
                )
                st.success("Audio translated and saved to your account.")
            except Exception as exc:
                st.error(f"Unable to process audio: {exc}")

with dashboard_tab:
    st.subheader("Saved audios")
    user_records = get_user_audio_records(st.session_state.user_id)

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
