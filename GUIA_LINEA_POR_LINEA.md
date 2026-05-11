# Guía Línea por Línea: Antes vs Después

Este documento muestra exactamente qué cambiar, dónde y cómo.

---

## CAMBIO 1: cli.py → Función verificar_identidad()

### UBICACIÓN
Archivo: [voice_auth/cli.py](voice_auth/cli.py)
Líneas: 195-210 (aproximadamente)

### ANTES (ACTUAL)
```python
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
```

### CAMBIOS NECESARIOS

#### PASO 1: Actualizar import
**Localización:** Línea 7-8 aprox.

ANTES:
```python
from .matching import mejor_coincidencia
```

DESPUÉS:
```python
from .matching import mejor_coincidencia, hacer_identificacion
```

---

#### PASO 2: Reemplazar bloque final (lineas 195-210)

ANTES (ELIMINAR ESTO):
```python
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
```

DESPUÉS (AGREGAR ESTO):
```python
    # Hacer la identificacion usando ambas validaciones
    resultado = hacer_identificacion(
        perfil_actual=perfil_actual,
        dataset=dataset,
        umbral_distancia=umbral,
        palabra_correcta=palabra_correcta,
        texto_escuchado=texto_escuchado,
        palabra_clave=palabra_clave,
    )
    
    # Mostrar resultados detallados
    print("\n=== RESULTADO DE VERIFICACION ===")
    print(f"Pitch muestra: {perfil_actual['pitch_hz']:.2f} Hz")
    print(f"Texto reconocido: '{texto_escuchado or 'no reconocido'}'")
    print(f"Palabra clave esperada: '{palabra_clave}'")
    print()
    print(f"Validacion de voz:")
    print(f"  - Distancia: {resultado['validaciones']['distancia_voz']:.4f}")
    print(f"  - Umbral: {resultado['validaciones']['umbral_distancia']:.4f}")
    print(f"  - Estado: {'✓ VALIDA' if resultado['validaciones']['voz_valida'] else '✗ INVALIDA'}")
    print()
    print(f"Validacion de palabra clave:")
    print(f"  - Detectada: {'✓ SI' if resultado['validaciones']['palabra_clave_valida'] else '✗ NO'}")
    print()
    
    if resultado['puede_identificarse']:
        print(f"✓✓ RESULTADO POSITIVO ✓✓")
        print(f"Usuario identificado: '{resultado['usuario_identificado']}'")
        print(f"Confianza general: {resultado['confianza_general']:.1%}")
    else:
        print(f"✗✗ RESULTADO NEGATIVO ✗✗")
        print(f"Usuario no identificado.")
        print(f"Confianza general: {resultado['confianza_general']:.1%}")
        if resultado['razon_rechazo']:
            print(f"Razon: {resultado['razon_rechazo']}")
```

---

## CAMBIO 2: matching.py → Agregar función

### UBICACIÓN
Archivo: [voice_auth/matching.py](voice_auth/matching.py)
Líneas: Después de `verificar_usuario()` (al final del archivo)

### QUÉ AGREGAR

Al final del archivo, después de la función `verificar_usuario()`, agregar:

```python


def hacer_identificacion(
    perfil_actual: Dict[str, object],
    dataset: Dict[str, Dict[str, object]],
    umbral_distancia: float,
    palabra_correcta: bool,
    texto_escuchado: str,
    palabra_clave: str,
) -> Dict[str, object]:
    """
    Realiza la decision final de identificacion segun AMBAS validaciones.
    
    Validaciones:
    1. Distancia bajo umbral (validacion de caracteristicas de voz)
    2. Palabra clave detectada correctamente (validacion de anti-spoofing)
    
    Args:
        perfil_actual: Vector de caracteristicas de la muestra actual
        dataset: Dataset de perfiles de usuarios registrados
        umbral_distancia: Umbral maximo permitido para distancia euclidea
        palabra_correcta: Boolean indicando si palabra clave fue detectada
        texto_escuchado: Transcripcion del audio capturado
        palabra_clave: Palabra clave esperada
    
    Returns:
        Dict con estructura:
        {
            "usuario_identificado": str | None,
            "confianza_general": float [0, 1],
            "validaciones": {
                "voz_valida": bool,
                "palabra_clave_valida": bool,
                "distancia_voz": float,
                "umbral_distancia": float,
                "texto_escuchado": str,
                "palabra_esperada": str,
            },
            "razon_rechazo": str | None,
            "puede_identificarse": bool,
        }
    """
    
    # Paso 1: Buscar mejor coincidencia de voz
    mejor_usuario, mejor_dist = mejor_coincidencia(perfil_actual, dataset)
    
    # Paso 2: Validar distancia contra umbral
    voz_valida = mejor_dist <= umbral_distancia if mejor_usuario else False
    
    # Paso 3: Validar palabra clave
    palabra_clave_valida = palabra_correcta
    
    # Paso 4: Calcular confianza general
    # Confianza de voz: inversa de la distancia normalizada
    if voz_valida:
        confianza_voz = max(0.0, 1.0 - (mejor_dist / umbral_distancia))
    else:
        confianza_voz = 0.0
    
    # Confianza de palabra clave: 1.0 si correcta, 0.0 si no
    confianza_palabra = 1.0 if palabra_clave_valida else 0.0
    
    # Confianza general: producto ponderado (ambas deben cumplirse)
    confianza_general = confianza_voz * confianza_palabra
    
    # Paso 5: Tomar decision
    usuario_identificado = None
    razon_rechazo = None
    
    if voz_valida and palabra_clave_valida:
        usuario_identificado = mejor_usuario
    else:
        if not voz_valida:
            razon_rechazo = (
                f"Distancia de voz fuera de rango "
                f"({mejor_dist:.4f} > {umbral_distancia:.4f})"
            )
        if not palabra_clave_valida:
            if razon_rechazo:
                razon_rechazo += " AND "
            else:
                razon_rechazo = ""
            razon_rechazo += (
                f"Palabra clave no detectada "
                f"(esperado: '{palabra_clave}', escuchado: '{texto_escuchado}')"
            )
    
    return {
        "usuario_identificado": usuario_identificado,
        "confianza_general": float(confianza_general),
        "validaciones": {
            "voz_valida": bool(voz_valida),
            "palabra_clave_valida": bool(palabra_clave_valida),
            "distancia_voz": float(mejor_dist),
            "umbral_distancia": float(umbral_distancia),
            "texto_escuchado": str(texto_escuchado),
            "palabra_esperada": str(palabra_clave),
        },
        "razon_rechazo": razon_rechazo,
        "puede_identificarse": bool(usuario_identificado is not None),
    }
```

---

## CAMBIO 3: keywords.py → Agregar funciones

### UBICACIÓN
Archivo: [voice_auth/keywords.py](voice_auth/keywords.py)
Líneas: Después de `transcribir_audio()` (al final del archivo)

### QUÉ AGREGAR

Al final del archivo, después de la función `transcribir_audio()`, agregar:

```python


def palabra_normalizada_en_texto(texto_norm: str, palabra_norm: str) -> bool:
    """Indica si la palabra normalizada esta en el texto normalizado."""
    if not texto_norm or not palabra_norm:
        return False
    return palabra_norm in texto_norm


def analizar_transcripcion(
    texto: str,
    palabra_clave: str,
) -> Dict[str, object]:
    """
    Analiza la transcripcion detectando validaciones adicionales.
    
    Retorna dict con:
    - contiene_palabra: bool - Si la palabra clave esta presente
    - confianza_transcripcion: float [0, 1] - Estimacion de calidad de transcripcion
    - texto_normalizado: str - Texto normalizado para comparacion
    - es_valido: bool - Si la transcripcion es valida (no vacia, suficientemente larga)
    - longitud_tokens: int - Cantidad de palabras en la transcripcion
    
    Notas:
    - Transcripciones muy cortas (<1 token) tienen baja confianza
    - Transcripciones vacias se consideran invalidas
    - La palabra clave puede ser parte de una palabra mas grande
    """
    texto_norm = normalizar_texto(texto)
    palabra_norm = normalizar_texto(palabra_clave)
    
    # Validar si transcripcion es valida
    tokens = texto_norm.split() if texto_norm else []
    es_valido = len(texto_norm) > 0 and len(tokens) > 0
    
    # Detectar si contiene la palabra clave
    contiene_palabra = palabra_normalizada_en_texto(texto_norm, palabra_norm)
    
    # Estimar confianza de transcripcion
    if not es_valido:
        confianza = 0.0  # Transcripcion vacia = sin confianza
    elif len(tokens) >= 3:
        confianza = 0.9  # Texto completo
    elif len(tokens) >= 2:
        confianza = 0.7  # Texto corto pero valido
    else:
        confianza = 0.4  # Una palabra solamente
    
    # Aumentar confianza si contiene la palabra clave
    if contiene_palabra and es_valido:
        confianza = min(1.0, confianza * 1.1)  # Bonus pequeño
    
    return {
        "contiene_palabra": bool(contiene_palabra),
        "confianza_transcripcion": float(confianza),
        "texto_normalizado": str(texto_norm),
        "es_valido": bool(es_valido),
        "longitud_tokens": int(len(tokens)),
        "texto_original": str(texto),
    }
```

**IMPORTANTE:** Agregar import de Dict al inicio del archivo:
```python
from typing import Dict, Optional, Tuple
```

---

## CAMBIO 4: storage.py → Actualizar inicializar_esquema()

### UBICACIÓN
Archivo: [voice_auth/storage.py](voice_auth/storage.py)
Líneas: Función `inicializar_esquema()` aprox. línea 35-50

### ANTES
```python
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
```

### DESPUÉS
```python
def inicializar_esquema(conn: psycopg2.extensions.connection) -> None:
    """Crea las tablas de usuarios y auditoría si aun no existen."""
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
        
        # Tabla de auditoría para registrar verificaciones
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS biometria_db.verificaciones (
                id SERIAL PRIMARY KEY,
                usuario_identificado TEXT,
                usuario_reclamado TEXT,
                fecha_verificacion TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                distancia_voz FLOAT NOT NULL,
                palabra_detectada BOOLEAN NOT NULL,
                confianza_general FLOAT NOT NULL,
                resultado_final BOOLEAN NOT NULL,
                texto_escuchado TEXT,
                palabra_esperada TEXT
            )
            """
        )
        
        conn.commit()
```

### AGREGAR AL FINAL (después de obtener_usuario())

```python


def guardar_verificacion(
    usuario_identificado: str | None,
    usuario_reclamado: str | None,
    distancia_voz: float,
    palabra_detectada: bool,
    confianza_general: float,
    resultado_final: bool,
    texto_escuchado: str = "",
    palabra_esperada: str = "",
) -> None:
    """Registra una verificacion en la tabla de auditoría."""
    with conectar_db() as conn:
        inicializar_esquema(conn)
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO biometria_db.verificaciones
                (usuario_identificado, usuario_reclamado, distancia_voz,
                 palabra_detectada, confianza_general, resultado_final,
                 texto_escuchado, palabra_esperada)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    usuario_identificado,
                    usuario_reclamado,
                    distancia_voz,
                    palabra_detectada,
                    confianza_general,
                    resultado_final,
                    texto_escuchado,
                    palabra_esperada,
                ),
            )
        conn.commit()


def obtener_historial_verificaciones(
    usuario: str | None = None,
    limite: int = 50,
) -> list:
    """Obtiene historial de verificaciones de la auditoría."""
    with conectar_db() as conn:
        inicializar_esquema(conn)
        with conn.cursor() as cursor:
            if usuario:
                cursor.execute(
                    """
                    SELECT * FROM biometria_db.verificaciones
                    WHERE usuario_identificado = %s OR usuario_reclamado = %s
                    ORDER BY fecha_verificacion DESC
                    LIMIT %s
                    """,
                    (usuario, usuario, limite),
                )
            else:
                cursor.execute(
                    """
                    SELECT * FROM biometria_db.verificaciones
                    ORDER BY fecha_verificacion DESC
                    LIMIT %s
                    """,
                    (limite,),
                )
            return cursor.fetchall()
```

---

## Resumen de Cambios

| Archivo | Líneas | Acción | Tipo |
|---------|--------|--------|------|
| cli.py | 7-8 | Actualizar import | 1 línea |
| cli.py | 195-210 | Reemplazar bloque | ~40 líneas |
| matching.py | EOF | Agregar función | ~80 líneas |
| keywords.py | EOF | Agregar funciones | ~40 líneas |
| storage.py | 35-50 | Actualizar función | +8 líneas |
| storage.py | EOF | Agregar 2 funciones | +60 líneas |

**Total: ~230 líneas de código nuevo/modificado**

---

## ✅ Verificación Después de Cambios

Para verificar que los cambios funcionan:

```bash
# 1. Verificar sintaxis
python -m py_compile voice_auth/cli.py
python -m py_compile voice_auth/matching.py
python -m py_compile voice_auth/keywords.py
python -m py_compile voice_auth/storage.py

# 2. Probar verificación
python -m voice_auth.cli verificar --duracion 4 --palabra-clave "ábrete"

# 3. Ver que la salida tenga la nueva estructura
```
