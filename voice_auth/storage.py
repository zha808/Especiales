from __future__ import annotations

import json
from pathlib import Path
from typing import Dict


DEFAULT_DATASET_PATH = Path("saved_models") / "voice_dataset.json"


def cargar_dataset(path: Path) -> Dict[str, Dict[str, object]]:
    """Carga el dataset de perfiles desde JSON; si no existe devuelve vacio."""
    if not path.exists():
        return {}

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        return {}

    return data


def guardar_dataset(path: Path, dataset: Dict[str, Dict[str, object]]) -> None:
    """Guarda el dataset de perfiles en formato JSON legible."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(dataset, f, ensure_ascii=False, indent=2)
