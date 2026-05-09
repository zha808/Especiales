from __future__ import annotations

import argparse
import sys

import numpy as np

from .audio import cargar_audio_wav, grabar_audio
from .features import extraer_caracteristicas
from .keywords import contiene_palabra_clave, transcribir_audio
from .matching import mejor_coincidencia
from .storage import DatabaseError, cargar_dataset, guardar_usuario


PALABRA_CLAVE_POR_DEFECTO = "ábrete"


def _pedir_texto(mensaje: str, default: str | None = None) -> str:
    """Solicita texto por consola y aplica valor por defecto si viene vacio."""
    prompt = f"{mensaje}"
    if default is not None:
        prompt += f" [{default}]"
    prompt += ": "

    try:
        valor = input(prompt).strip()
    except EOFError as exc:
        print("\nEntrada finalizada. Saliendo...")
        raise SystemExit(0) from exc
    if valor:
        return valor
    return default or ""


def _pedir_float(mensaje: str, default: float) -> float:
    """Solicita un numero flotante con validacion basica."""
    while True:
        valor_txt = _pedir_texto(mensaje, default=str(default))
        try:
            return float(valor_txt)
        except ValueError:
            print("Entrada invalida. Debes escribir un numero.")


def _pedir_int(mensaje: str, default: int) -> int:
    """Solicita un entero con validacion basica."""
    while True:
        valor_txt = _pedir_texto(mensaje, default=str(default))
        try:
            return int(valor_txt)
        except ValueError:
            print("Entrada invalida. Debes escribir un numero entero.")


def _obtener_audio(duracion: float, sample_rate: int, audio_file: str | None) -> np.ndarray:
    """Obtiene audio desde microfono por defecto o desde un archivo WAV."""
    if audio_file is not None and audio_file.strip() != "":
        # Permite pegar rutas entre comillas desde el explorador/terminal.
        ruta_limpia = audio_file.strip().strip('"').strip("'")
        print(f"Procesando archivo WAV: {ruta_limpia}")
        return cargar_audio_wav(ruta_limpia, sample_rate)
    return grabar_audio(duracion, sample_rate)


def ejecutar_modo_interactivo() -> None:
    """Menu principal para ejecutar registrar/verificar sin argumentos CLI."""
    print("\n=== Autenticacion de voz (modo interactivo) ===")

    while True:
        print("\nElige una opcion:")
        print("  1) Registrar usuario")
        print("  2) Verificar identidad")
        print("  3) Salir")

        try:
            opcion = input("Opcion [1/2/3]: ").strip()
        except EOFError:
            print("\nEntrada finalizada. Saliendo...")
            return

        if opcion == "1":
            usuario = _pedir_texto("Usuario")
            if not usuario:
                print("Debes indicar un usuario.")
                continue

            duracion = _pedir_float("Duracion de grabacion (segundos)", 4.0)
            sample_rate = _pedir_int("Sample rate (Hz)", 16000)
            audio_file = _pedir_texto("Ruta archivo WAV (opcional, Enter para microfono)", "")

            registrar_usuario(
                usuario=usuario,
                duracion=duracion,
                sample_rate=sample_rate,
                audio_file=audio_file,
            )
        elif opcion == "2":
            duracion = _pedir_float("Duracion de grabacion (segundos)", 4.0)
            umbral = _pedir_float("Umbral de verificacion", 0.35)
            sample_rate = _pedir_int("Sample rate (Hz)", 16000)
            audio_file = _pedir_texto("Ruta archivo WAV (opcional, Enter para microfono)", "")
            palabra_clave = _pedir_texto("Palabra clave esperada", PALABRA_CLAVE_POR_DEFECTO)

            verificar_identidad(
                duracion=duracion,
                sample_rate=sample_rate,
                umbral=umbral,
                palabra_clave=palabra_clave,
                audio_file=audio_file,
            )
        elif opcion == "3":
            print("Saliendo...")
            return
        else:
            print("Opcion invalida. Elige 1, 2 o 3.")


def registrar_usuario(
    usuario: str,
    duracion: float,
    sample_rate: int,
    audio_file: str | None = None,
) -> None:
    """Graba una muestra y la guarda como perfil del usuario indicado."""
    try:
        dataset = cargar_dataset()
    except DatabaseError as exc:
        print(f"Error de base de datos: {exc}")
        return

    if usuario in dataset:
        print(f"Aviso: el usuario '{usuario}' ya existia y sera actualizado.")

    try:
        audio = _obtener_audio(duracion, sample_rate, audio_file)
    except FileNotFoundError as exc:
        print(f"Error: {exc}")
        print("Verifica la ruta del archivo WAV o usa Enter para grabar por microfono.")
        return
    perfil = extraer_caracteristicas(audio, sample_rate)

    if perfil["pitch_hz"] is None:
        print("No se pudo estimar el pitch. Intenta de nuevo con menos ruido.")
        return

    try:
        guardar_usuario(usuario, perfil)
    except DatabaseError as exc:
        print(f"Error de base de datos: {exc}")
        return

    print(f"Usuario '{usuario}' registrado correctamente.")
    print(f"Pitch estimado: {perfil['pitch_hz']:.2f} Hz")


def verificar_identidad(
    duracion: float,
    sample_rate: int,
    umbral: float,
    palabra_clave: str,
    audio_file: str | None = None,
) -> None:
    """Identifica al hablante comparando su voz contra todos los usuarios del dataset."""
    try:
        dataset = cargar_dataset()
    except DatabaseError as exc:
        print(f"Error de base de datos: {exc}")
        return
    if not dataset:
        print("No hay usuarios registrados. Primero registra usuarios en la base de datos.")
        return

    try:
        audio = _obtener_audio(duracion, sample_rate, audio_file)
    except FileNotFoundError as exc:
        print(f"Error: {exc}")
        print("Verifica la ruta del archivo WAV o usa Enter para grabar por microfono.")
        return
    perfil_actual = extraer_caracteristicas(audio, sample_rate)

    if perfil_actual["pitch_hz"] is None:
        print("No se pudo estimar el pitch en la muestra actual.")
        return

    try:
        texto_escuchado = transcribir_audio(audio, sample_rate)
    except RuntimeError as exc:
        print(f"Error al reconocer la palabra clave: {exc}")
        return

    palabra_correcta = contiene_palabra_clave(texto_escuchado, palabra_clave)

    mejor_usuario, mejor_dist = mejor_coincidencia(perfil_actual, dataset)
    if mejor_usuario is None:
        print("No fue posible encontrar coincidencias en el dataset.")
        return

    print(f"Pitch muestra: {perfil_actual['pitch_hz']:.2f} Hz")
    print(f"Texto reconocido: '{texto_escuchado or 'no reconocido'}'")
    print(f"Mejor coincidencia: {mejor_usuario} (distancia={mejor_dist:.4f}, umbral={umbral:.4f})")

    if palabra_correcta and mejor_dist <= umbral:
        print(f"Resultado: usuario identificado -> '{mejor_usuario}'.")
    else:
        print("Resultado: usuario no identificado con suficiente confianza.")
        if not palabra_correcta:
            print(f"La palabra clave '{palabra_clave}' no fue detectada.")
        if mejor_dist > umbral:
            print(f"La voz no coincide lo suficiente (distancia {mejor_dist:.4f} > {umbral:.4f}).")


def construir_parser() -> argparse.ArgumentParser:
    """Crea la CLI con comandos de registro y verificacion."""
    parser = argparse.ArgumentParser(
        description="Autenticacion de voz basica con FFT, reconocimiento de palabra clave y PostgreSQL"
    )

    parser.add_argument(
        "--sample-rate",
        type=int,
        default=16000,
        help="Frecuencia de muestreo en Hz (recomendado: 16000)",
    )

    subparsers = parser.add_subparsers(dest="comando", required=True)

    p_reg = subparsers.add_parser("registrar", help="Registrar o actualizar un usuario")
    p_reg.add_argument("--usuario", type=str, required=True, help="Nombre/ID del usuario")
    p_reg.add_argument(
        "--duracion", type=float, default=4.0, help="Duracion de grabacion en segundos"
    )
    p_reg.add_argument(
        "--audio-file",
        type=str,
        default=None,
        help="Ruta a archivo WAV para registrar (si se omite, usa microfono por defecto)",
    )

    p_ver = subparsers.add_parser(
        "verificar", help="Identificar usuario automaticamente a partir de la voz"
    )
    p_ver.add_argument(
        "--duracion", type=float, default=4.0, help="Duracion de grabacion en segundos"
    )
    p_ver.add_argument(
        "--umbral",
        type=float,
        default=0.35,
        help="Distancia maxima permitida para validar identidad",
    )
    p_ver.add_argument(
        "--audio-file",
        type=str,
        default=None,
        help="Ruta a archivo WAV para verificar (si se omite, usa microfono por defecto)",
    )
    p_ver.add_argument(
        "--palabra-clave",
        type=str,
        default=PALABRA_CLAVE_POR_DEFECTO,
        help="Palabra clave esperada durante la verificacion",
    )

    return parser


def main() -> None:
    """Punto de entrada de la aplicacion."""
    parser = construir_parser()

    # Si se ejecuta sin argumentos, iniciamos modo interactivo.
    if len(sys.argv) == 1:
        ejecutar_modo_interactivo()
        return

    args = parser.parse_args()

    if args.comando == "registrar":
        registrar_usuario(
            usuario=args.usuario,
            duracion=float(args.duracion),
            sample_rate=int(args.sample_rate),
            audio_file=args.audio_file,
        )
    elif args.comando == "verificar":
        verificar_identidad(
            duracion=float(args.duracion),
            sample_rate=int(args.sample_rate),
            umbral=float(args.umbral),
            palabra_clave=str(args.palabra_clave),
            audio_file=args.audio_file,
        )
    else:
        raise ValueError("Comando no soportado")
