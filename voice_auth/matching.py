from __future__ import annotations

from typing import Dict, Optional, Tuple

import numpy as np


def _vectorizar(atributos: Dict[str, object], num_armonicos: int = 5) -> Optional[np.ndarray]:
    """Convierte un perfil de voz a vector para comparar con distancia euclidea."""
    pitch = atributos.get("pitch_hz")
    armonicos = atributos.get("armonicos", [])

    if pitch is None:
        return None

    pitch_norm = float(pitch) / 300.0

    amps = np.zeros(num_armonicos, dtype=np.float32)
    if isinstance(armonicos, list):
        for h in armonicos:
            if not isinstance(h, dict):
                continue
            orden = int(h.get("orden", 0))
            if 1 <= orden <= num_armonicos:
                amps[orden - 1] = float(h.get("amplitud_rel", 0.0))

    vec = np.concatenate(([pitch_norm], amps))
    return vec.astype(np.float32)


def distancia_perfiles(a: Dict[str, object], b: Dict[str, object]) -> float:
    """Calcula distancia entre dos perfiles de voz."""
    va = _vectorizar(a)
    vb = _vectorizar(b)
    if va is None or vb is None:
        return float("inf")
    return float(np.linalg.norm(va - vb))


def mejor_coincidencia(
    perfil_actual: Dict[str, object],
    dataset: Dict[str, Dict[str, object]],
) -> Tuple[Optional[str], float]:
    """Busca en el dataset el usuario con distancia minima al perfil actual."""
    mejor_usuario = None
    mejor_dist = float("inf")

    for usuario, perfil_ref in dataset.items():
        dist = distancia_perfiles(perfil_actual, perfil_ref)
        if dist < mejor_dist:
            mejor_dist = dist
            mejor_usuario = usuario

    return mejor_usuario, mejor_dist


def verificar_usuario(
    usuario: str,
    perfil_actual: Dict[str, object],
    dataset: Dict[str, Dict[str, object]],
    umbral: float,
) -> Tuple[bool, float]:
    """Verifica si la muestra pertenece al usuario reclamado segun umbral."""
    perfil_ref = dataset.get(usuario)
    if perfil_ref is None:
        return False, float("inf")

    dist = distancia_perfiles(perfil_actual, perfil_ref)
    return dist <= umbral, dist
