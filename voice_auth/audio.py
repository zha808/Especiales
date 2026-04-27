from __future__ import annotations

from pathlib import Path

import numpy as np
import sounddevice as sd
from scipy.io import wavfile
from scipy.signal import resample_poly


def grabar_audio(duracion: float, sample_rate: int) -> np.ndarray:
    """Graba audio mono durante la duracion indicada en segundos."""
    num_muestras = int(duracion * sample_rate)

    print(f"Grabando {duracion:.1f}s... Habla ahora.")
    audio = sd.rec(num_muestras, samplerate=sample_rate, channels=1, dtype="float32")
    sd.wait()
    print("Grabacion finalizada.")

    return audio.flatten()


def cargar_audio_wav(ruta_wav: str | Path, sample_rate_objetivo: int) -> np.ndarray:
    """
    Carga un .wav desde disco, convierte a mono y ajusta sample rate si hace falta.
    """
    ruta = Path(ruta_wav)
    if not ruta.exists():
        raise FileNotFoundError(f"No existe el archivo WAV: {ruta}")

    fs_origen, audio = wavfile.read(str(ruta))

    # Convierte tipos enteros a float32 en rango aproximado [-1, 1].
    if np.issubdtype(audio.dtype, np.integer):
        max_int = max(abs(np.iinfo(audio.dtype).min), np.iinfo(audio.dtype).max)
        audio = audio.astype(np.float32) / float(max_int)
    else:
        audio = audio.astype(np.float32)

    # Si el WAV tiene mas de un canal, promediamos a mono.
    if audio.ndim > 1:
        audio = np.mean(audio, axis=1)

    if fs_origen != sample_rate_objetivo:
        # Remuestreo con relacion racional para buena calidad.
        audio = resample_poly(audio, up=sample_rate_objetivo, down=fs_origen).astype(np.float32)

    return audio.flatten()
