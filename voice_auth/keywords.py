from __future__ import annotations

import io
import unicodedata

import numpy as np
import speech_recognition as sr
from scipy.io import wavfile


def normalizar_texto(texto: str) -> str:
    """Normaliza texto para comparar palabras clave sin depender de tildes ni mayusculas."""
    texto = unicodedata.normalize("NFKD", texto.casefold())
    texto = "".join(caracter for caracter in texto if not unicodedata.combining(caracter))
    texto = "".join(caracter if caracter.isalnum() or caracter.isspace() else " " for caracter in texto)
    return " ".join(texto.split())


def contiene_palabra_clave(texto: str, palabra_clave: str) -> bool:
    """Indica si la transcripcion contiene la palabra clave esperada."""
    texto_normalizado = normalizar_texto(texto)
    palabra_normalizada = normalizar_texto(palabra_clave)
    if not texto_normalizado or not palabra_normalizada:
        return False
    return palabra_normalizada in texto_normalizado


def _audio_a_int16(audio: np.ndarray) -> np.ndarray:
    """Convierte una senal flotante o entera a PCM int16."""
    audio = np.asarray(audio)
    if np.issubdtype(audio.dtype, np.integer):
        return audio.astype(np.int16).flatten()

    audio = np.clip(audio.astype(np.float32), -1.0, 1.0)
    return np.int16(audio * 32767.0).flatten()


def transcribir_audio(audio: np.ndarray, sample_rate: int, language: str = "es-ES") -> str:
    """Transcribe una grabacion usando SpeechRecognition y Google Speech."""
    audio_int16 = _audio_a_int16(audio)
    byte_io = io.BytesIO()
    wavfile.write(byte_io, sample_rate, audio_int16)
    byte_io.seek(0)

    recognizer = sr.Recognizer()
    with sr.AudioFile(byte_io) as source:
        audio_data = recognizer.record(source)

    try:
        return recognizer.recognize_google(audio_data, language=language).lower()
    except sr.UnknownValueError:
        return ""
    except sr.RequestError as exc:
        raise RuntimeError(f"No fue posible usar el servicio de reconocimiento: {exc}") from exc
