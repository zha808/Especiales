# Código a Agregar para Reconocimiento con Palabra Clave

Este documento contiene el código específico que debe agregarse en cada archivo para completar el flujo de reconocimiento de persona usando palabra clave.

---

## 1. AGREGAR A: matching.py

Agregar esta función después de `verificar_usuario()`:

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
    Realiza la decision final de identificacion segun AMBAS validaciones:
    
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

## 2. MEJORAR: keywords.py

Agregar esta funcion después de `contiene_palabra_clave()`:

```python
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


def palabra_normalizada_en_texto(texto_norm: str, palabra_norm: str) -> bool:
    """Indica si la palabra normalizada esta en el texto normalizado."""
    if not texto_norm or not palabra_norm:
        return False
    return palabra_norm in texto_norm
```

---

## 3. ACTUALIZAR: cli.py

En la función `verificar_identidad()`, reemplazar la seccion de decision (las lineas de print al final) con:

**VIEJO:**
```python
    if palabra_correcta and mejor_dist <= umbral:
        print(f"Resultado: usuario identificado -> '{mejor_usuario}'.")
    else:
        print("Resultado: usuario no identificado con suficiente confianza.")
        if not palabra_correcta:
            print(f"La palabra clave '{palabra_clave}' no fue detectada.")
        if mejor_dist > umbral:
            print(f"La voz no coincide lo suficiente (distancia {mejor_dist:.4f} > {umbral:.4f}).")
```

**NUEVO:**
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

Tambien agregar el import:
```python
from .matching import mejor_coincidencia, hacer_identificacion
```

---

## 4. AGREGAR DOCUMENTACION MATEMATICA: features.py

En cada funcion, agregar comentarios con ecuaciones. Ejemplo:

**En `preprocesar_audio()`:**
```python
def preprocesar_audio(audio: np.ndarray) -> np.ndarray:
    """
    Centra y normaliza la senal para hacerla mas estable numericamente.
    
    Proceso matematico (Seccion 2 del documento):
    
    2.1) Eliminacion de componente DC:
        mu = (1/N) * sum_{n=0..N-1} x[n]
        x1[n] = x[n] - mu
    
    2.2) Normalizacion de amplitud:
        A = max_n |x1[n]|
        x2[n] = x1[n] / A   (si A > 0)
    
    Salida aproximadamente en rango [-1, 1].
    """
```

**En `calcular_espectro_fft()`:**
```python
def calcular_espectro_fft(audio: np.ndarray, sample_rate: int) -> Tuple[np.ndarray, np.ndarray]:
    """
    Calcula frecuencias y magnitud usando FFT real con ventana Hann.
    
    Proceso matematico (Seccion 3 del documento):
    
    3.1) Ventana de Hann:
        xw[n] = x2[n] * w[n]
        w[n] = 0.5 - 0.5*cos(2*pi*n/(N-1))
    
    3.2) Transformada rapida de Fourier (rFFT):
        X[k] = sum_{n=0..N-1} xw[n] * exp(-j*2*pi*k*n/N)
        f_k = k * Fs / N
    
    3.3) Espectro de magnitud normalizado:
        M[k] = |X[k]|
        M_norm[k] = M[k] / (sum_n w[n] + eps)
    
    Retorna:
        freqs_hz: Array de frecuencias en Hz
        mag: Array de magnitudes normalizadas
    """
```

**En `estimar_pitch_y_armonicos()`:**
```python
def estimar_pitch_y_armonicos(
    freqs_hz: np.ndarray,
    mag: np.ndarray,
    min_f0: float = 80.0,
    max_f0: float = 350.0,
    num_armonicos: int = 5,
) -> Tuple[Optional[float], List[Dict[str, float]]]:
    """
    Estima la fundamental (pitch) y armonicos principales desde el espectro.
    
    Proceso matematico (Secciones 4 y 5 del documento):
    
    4) Estimacion de Pitch (F0):
        - Busca fundamental en rango [80, 350] Hz
        - umbral = max(0.15 * max(M_rango), 1e-8)
        - Selecciona pico de mayor magnitud
    
    5) Extraccion de Armonicos:
        - Para cada orden m = 1..H (H=5):
          f_m,ideal = m * F0
          delta_m = max(2.5*resolucion, 8.0 + 1.2*m)
          Busca maximo en [f_m,ideal - delta_m, f_m,ideal + delta_m]
    
    Retorna:
        f0: Frecuencia fundamental estimada en Hz
        armonicos: Lista de dicts con orden, frecuencia y amplitud
    """
```

**En `extraer_caracteristicas()`:**
```python
def extraer_caracteristicas(audio: np.ndarray, sample_rate: int) -> Dict[str, object]:
    """
    Pipeline completo de extraccion de caracteristicas de voz.
    
    Proceso matematico (Secciones 1-7 del documento):
    
    1. Entrada de audio: x[n]
    2. Preprocesamiento: centrado y normalizacion
    3. FFT con ventana Hann
    4. Estimacion de pitch F0
    5. Extraccion de armonicos {a_1, a_2, ..., a_H}
    6. Normalizacion: r_m = a_m / a_1 (amplitudes relativas)
    7. Vector de caracteristicas:
       v = [F0/300, r_1, r_2, ..., r_H]
    
    Nota: F0 se divide por 300 para normalizar escala.
    
    Retorna dict con:
        pitch_hz: Fundamental estimada
        armonicos: Lista de armonicos con amplitudes relativas
    """
```

---

## 5. AGREGAR A: storage.py

Despues de la tabla `usuarios_voz`, agregar tabla de auditoría en `inicializar_esquema()`:

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

Tambien agregar funciones para guardar verificaciones:

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

| Archivo | Cambio | Tipo |
|---------|--------|------|
| matching.py | Agregar `hacer_identificacion()` | Función crítica |
| keywords.py | Agregar `analizar_transcripcion()` | Mejora |
| cli.py | Actualizar salida de verificacion | Mejora |
| features.py | Agregar documentación matemática | Documentación |
| storage.py | Agregar tabla de auditoría | Base de datos |

---

## Dependencias

El código nuevo no requiere librerías adicionales:
- `matching.py`: usa `numpy` (ya importado)
- `keywords.py`: usa strings (built-in)
- `cli.py`: usa módulos internos
- `storage.py`: usa `psycopg2` (ya instalado)
