from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import numpy as np
from scipy.signal import find_peaks, get_window


def preprocesar_audio(audio: np.ndarray) -> np.ndarray:
    """Centra y normaliza la senal para hacerla mas estable numericamente."""
    audio = audio.astype(np.float32)
    audio = audio - np.mean(audio)

    max_abs = np.max(np.abs(audio))
    if max_abs > 1e-8:
        audio = audio / max_abs

    return audio


def calcular_espectro_fft(audio: np.ndarray, sample_rate: int) -> Tuple[np.ndarray, np.ndarray]:
    """Calcula frecuencias y magnitud usando FFT real con ventana Hann."""
    if len(audio) < 32:
        raise ValueError("La senal es demasiado corta para analizar.")

    ventana = get_window("hann", len(audio), fftbins=True)
    audio_win = audio * ventana

    fft_vals = np.fft.rfft(audio_win)
    mag = np.abs(fft_vals)
    mag = mag / (np.sum(ventana) + 1e-12)

    freqs_hz = np.fft.rfftfreq(len(audio), d=1.0 / sample_rate)
    return freqs_hz, mag


def estimar_pitch_y_armonicos(
    freqs_hz: np.ndarray,
    mag: np.ndarray,
    min_f0: float = 80.0,
    max_f0: float = 350.0,
    num_armonicos: int = 5,
) -> Tuple[Optional[float], List[Dict[str, float]]]:
    """Estima la fundamental (pitch) y armónicos principales desde el espectro."""
    mascara_f0 = (freqs_hz >= min_f0) & (freqs_hz <= max_f0)
    freqs_f0 = freqs_hz[mascara_f0]
    mag_f0 = mag[mascara_f0]

    if len(freqs_f0) == 0:
        return None, []

    umbral = max(np.max(mag_f0) * 0.15, 1e-8)
    indices_picos, _ = find_peaks(mag_f0, height=umbral)

    if len(indices_picos) == 0:
        idx_local = int(np.argmax(mag_f0))
    else:
        alturas = mag_f0[indices_picos]
        idx_local = int(indices_picos[int(np.argmax(alturas))])

    f0 = float(freqs_f0[idx_local])

    armonicos: List[Dict[str, float]] = []
    resolucion_hz = freqs_hz[1] - freqs_hz[0] if len(freqs_hz) > 1 else 1.0

    for orden in range(1, num_armonicos + 1):
        objetivo = orden * f0
        margen = max(2.5 * resolucion_hz, 8.0 + 1.2 * orden)
        mask = (freqs_hz >= objetivo - margen) & (freqs_hz <= objetivo + margen)

        if not np.any(mask):
            continue

        freqs_loc = freqs_hz[mask]
        mag_loc = mag[mask]
        idx_peak = int(np.argmax(mag_loc))

        armonicos.append(
            {
                "orden": float(orden),
                "frecuencia_hz": float(freqs_loc[idx_peak]),
                "amplitud": float(mag_loc[idx_peak]),
            }
        )

    return f0, armonicos


def extraer_caracteristicas(audio: np.ndarray, sample_rate: int) -> Dict[str, object]:
    """Pipeline de extraccion de pitch y armonicos relativos."""
    audio_proc = preprocesar_audio(audio)
    freqs_hz, mag = calcular_espectro_fft(audio_proc, sample_rate)
    f0, armonicos = estimar_pitch_y_armonicos(freqs_hz, mag)

    if f0 is None:
        return {"pitch_hz": None, "armonicos": []}

    amp_base = armonicos[0]["amplitud"] if armonicos else 1e-8
    amp_base = max(float(amp_base), 1e-8)

    armonicos_rel = []
    for h in armonicos:
        armonicos_rel.append(
            {
                "orden": int(h["orden"]),
                "frecuencia_hz": float(h["frecuencia_hz"]),
                "amplitud_rel": float(h["amplitud"] / amp_base),
            }
        )

    return {
        "pitch_hz": float(f0),
        "armonicos": armonicos_rel,
    }
