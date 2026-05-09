from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict

import psycopg2


DatabaseError = psycopg2.Error


DEFAULT_LEGACY_DATASET_PATH = Path("saved_models") / "voice_dataset.json"
DEFAULT_DB_CONFIG = {
    "dbname": os.getenv("VOICE_AUTH_DB_NAME", "biometria_db"),
    "user": os.getenv("VOICE_AUTH_DB_USER", "postgres"),
    "password": os.getenv("VOICE_AUTH_DB_PASSWORD", "miguelo74"),
    "host": os.getenv("VOICE_AUTH_DB_HOST", "localhost"),
    "port": int(os.getenv("VOICE_AUTH_DB_PORT", "5432")),
}


def _config_db() -> Dict[str, object]:
    """Devuelve la configuracion de conexion a PostgreSQL."""
    return dict(DEFAULT_DB_CONFIG)


def conectar_db() -> psycopg2.extensions.connection:
    """Abre una conexion a PostgreSQL usando la configuracion por defecto."""
    return psycopg2.connect(**_config_db())


def inicializar_esquema(conn: psycopg2.extensions.connection) -> None:
    """Crea la tabla de usuarios si aun no existe."""
    with conn.cursor() as cursor:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS biometria_db.usuarios_voz (
                nombre TEXT PRIMARY KEY,
                huella_espectral TEXT NOT NULL,
                creado_en TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                actualizado_en TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )


def _serializar_perfil(perfil: Dict[str, object]) -> str:
    return json.dumps(perfil, ensure_ascii=False)


def _deserializar_perfil(huella_espectral: object) -> Dict[str, object] | None:
    if isinstance(huella_espectral, str):
        perfil = json.loads(huella_espectral)
    else:
        perfil = huella_espectral

    return perfil if isinstance(perfil, dict) else None


def _importar_dataset_legacy(conn: psycopg2.extensions.connection, path: Path) -> int:
    """Importa un dataset JSON antiguo al almacenamiento en PostgreSQL."""
    if not path.exists():
        return 0

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        return 0

    with conn.cursor() as cursor:
        for nombre, perfil in data.items():
            cursor.execute(
                """
                INSERT INTO biometria_db.usuarios_voz (nombre, huella_espectral, creado_en, actualizado_en)
                VALUES (%s, %s, NOW(), NOW())
                ON CONFLICT (nombre)
                DO UPDATE SET
                    huella_espectral = EXCLUDED.huella_espectral,
                    actualizado_en = NOW()
                """,
                (nombre, _serializar_perfil(perfil)),
            )

    conn.commit()
    return len(data)


def cargar_dataset(path: Path | None = None) -> Dict[str, Dict[str, object]]:
    """Carga los perfiles desde PostgreSQL; migra el JSON legado si existe."""
    del path

    with conectar_db() as conn:
        inicializar_esquema(conn)

        with conn.cursor() as cursor:
            cursor.execute("SELECT nombre, huella_espectral FROM usuarios_voz ORDER BY nombre")
            filas = cursor.fetchall()

        if not filas:
            _importar_dataset_legacy(conn, DEFAULT_LEGACY_DATASET_PATH)
            with conn.cursor() as cursor:
                cursor.execute("SELECT nombre, huella_espectral FROM biometria_db.usuarios_voz ORDER BY nombre")
                filas = cursor.fetchall()

    dataset: Dict[str, Dict[str, object]] = {}
    for nombre, huella_espectral in filas:
        perfil = _deserializar_perfil(huella_espectral)
        if perfil is not None:
            dataset[str(nombre)] = perfil

    return dataset


def guardar_dataset(path: Path | None, dataset: Dict[str, Dict[str, object]]) -> None:
    """Guarda o actualiza un conjunto de perfiles en PostgreSQL."""
    del path

    with conectar_db() as conn:
        inicializar_esquema(conn)
        with conn.cursor() as cursor:
            for nombre, perfil in dataset.items():
                cursor.execute(
                    """
                    INSERT INTO biometria_db.usuarios_voz (nombre, huella_espectral, creado_en, actualizado_en)
                    VALUES (%s, %s, NOW(), NOW())
                    ON CONFLICT (nombre)
                    DO UPDATE SET
                        huella_espectral = EXCLUDED.huella_espectral,
                        actualizado_en = NOW()
                    """,
                    (nombre, _serializar_perfil(perfil)),
                )


def guardar_usuario(nombre: str, perfil: Dict[str, object]) -> None:
    """Guarda o actualiza un perfil individual en PostgreSQL."""
    guardar_dataset(None, {nombre: perfil})


def obtener_usuario(nombre: str) -> Dict[str, object] | None:
    """Devuelve el perfil almacenado para un usuario, si existe."""
    with conectar_db() as conn:
        inicializar_esquema(conn)
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT huella_espectral FROM biometria_db.usuarios_voz WHERE nombre = %s",
                (nombre,),
            )
            fila = cursor.fetchone()

    if fila is None:
        return None

    return _deserializar_perfil(fila[0])
