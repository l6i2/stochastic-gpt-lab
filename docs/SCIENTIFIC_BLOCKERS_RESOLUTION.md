# Resolución incremental de bloqueos científicos

Corte: **1 de noviembre de 2026, 13:47:56 Ecuador**. Este documento registra
solo evidencia adicional respecto de `SCIENTIFIC_PREPARATION_CLOSURE.md`;
no sustituye contratos, datasets ni informes anteriores.

Evidencia: `research/studies/scientific_blockers_resolution_20261101_v4/`.

| Campo | Resultado verificable |
|---|---|
| MEMBERSHIP_VERIFIED | Cinco intervalos nativos declarados en el ledger, 28 IDs diagnósticos publicados, dos IDs censurados en cuarentena y prefijo nuevo postfrontera con hashes/cursor. Son alcances parciales, no independencia certificada. |
| MEMBERSHIP_UNKNOWN | Cinco entradas con límites/roles abiertos o desconocidos; faltan IDs y fronteras purgadas de los splits originales y reserva exacta de holdout. |
| TEMPORAL_MAPPING_VERIFIED | Orden de fuente y derivados, diferencias de contadores locales, bracket de activación existente y mediciones NTS autenticadas verificadas en cadena. Ninguna conversión de timestamps XM. |
| TEMPORAL_MAPPING_UNRESOLVED | Generación XM→UTC, mapping histórico, error de resolución/deriva dentro de segmentos y calendario histórico exacto. |
| INCIDENTS_ADJUDICATED | 43 hechos clasificados: 4 VERIFIED_CAUSE como contribución de energía, 9 PROBABLE_CAUSE y 30 UNKNOWN_CAUSE. |
| INCIDENTS_UNRESOLVED | 39 sin causa raíz definitiva; los 27 gaps conservan cobertura desconocida, incluidos los cuatro con causa contribuyente verificada. |
| CAUSAL_FEATURE_AUDIT | Prueba sintética nativa anterior conservada; cero nuevas features reales. CAUSAL_AUDIT global sigue FAIL. |
| DATASET_ADMISSION | BLOCKED; cero intervalos admitidos y DATASET_HASH=null. |
| TRAINING_READINESS | BLOCKED. |

## Bloqueos parciales cerrados

**Membership:** el freeze publicado identifica primera/última señal del master
como etiquetas del servidor `2023.12.20 02:05:00` y `2026.10.12 23:40:00`.
Se recuperaron como envolvente declarada, sin reinterpretarlas como UTC ni
atribuirles membership por fila. La búsqueda de nombres de manifests en outputs
no encontró originales; el historial Git alcanzable solo contiene una plantilla
de cohort, que no sustituye un manifest real. No se leyeron conjuntos protegidos.

**Incidentes:** 105 registros derivados se descomponen en 27 alertas de gap y
78 observaciones DISCONNECTED; corresponden a 84 observaciones de fuente distintas,
no a 105 interrupciones independientes. El monitor nativo conserva 27 gaps,
ocho inicios observados de desconexión y ocho reconexiones: 43 hechos.
Cada hecho se contrastó con sus bytes nativos verificados y cada registro
derivado con un prefijo SQLite sellado. La clasificación nueva es un overlay;
no reescribe incidentes ni modifica cobertura/admisión.

Los cuatro VERIFIED_CAUSE contienen episodios completos de energía Windows
del mismo boot dentro del intervalo observado, sin salto de reloj registrado
en ese intervalo. Se verifica una **causa contribuyente**, no que explique todo
el retraso ni que demuestre pérdida de ticks. Contexto parcial, cambio de reloj
o vínculo de boot incompleto impiden esa clasificación y quedan PROBABLE.
Observar desconectado/conectado no identifica por sí solo la causa de red.
Se revisaron también 86 eventos NetworkProfile y 188 WLAN. Seis entradas WLAN
incluyen razones de desconexión: cinco reportan una directiva que deshabilita
autoconexión y una una desconexión por el controlador. Dos hechos de desconexión
XM tienen ese contexto dentro de su ventana y pasan de UNKNOWN a PROBABLE;
no se prueba qué interfaz transportaba XM ni se cambia la política de red.
Los 27 gaps conservan su desglose: cuatro contribuciones verificadas, siete
probables y dieciséis desconocidas.

**Reloj:** Windows registra tres ajustes: −2,9691 ms, −9,7401 ms y
**+8 h 48 min 25,1210484 s** durante una reanudación. Se conservan sus RecordIds,
OldTime y NewTime. El gap máximo, 43.442.235 ms, tiene contexto de suspensión,
hibernación y corrección de reloj; permanece PROBABLE_CAUSE. No se interpola
a través de esa discontinuidad ni se inventa un offset del servidor.

Se verificaron 157 registros de la cadena NTS y 229 mediciones autenticadas
válidas según el cliente fijado. Autenticidad de captura y hashes locales no
equivalen a una reproducción criptográfica pública de claves de sesión, ni
autentican el reloj del broker. Se reutilizó la calibración existente comprobando
su hash, el código que la produjo y su prefijo NTS; no se recalibraron los mismos
datos. Sus modelos factibles siguen siendo condicionales, no certificados UTC
del evento ni cotas demostradas de deriva instantánea.

Se acotó además el **orden de muestreo local** de TimeGMT entre el contador
nativo leído antes de esa llamada y el contador Python posterior a leer la línea
completa, dentro del mismo boot. La ventana más ancha observada fue
11.483.203 ms. Puede incluir espera del escritor o lector, scheduling y suspensión;
no es latencia de generación ni latencia pura de red. La resolución de esos
contadores sigue sin calibración absoluta. Un único timestamp de recepción
no puede tratarse como si fuera el instante del callback o el del evento.

Los logs MT5 de 31/10 y 01/11 corroboran que existen entradas de conexión y
desconexión. Solo se publican categoría, etiqueta horaria y hash de línea;
se omiten cuentas y mensajes originales. Su semántica temporal no se utilizó
para inventar un alineamiento UTC o adjudicar con precisión gaps desconocidos.

## Prueba que falta y fuente necesaria

| Requisito pendiente | Prueba concreta ausente | Fuente que puede aportarla |
|---|---|---|
| Splits históricos | IDs exactos, límites purgados y hash del dataset padre; conteos/fechas no bastan | Manifests originales del productor de `stochastic_master_v1`, código base `ced3b6d9e469dadf76a4771049c994e476f19329` |
| Holdout y roles abiertos | Reservas exactas, cierre autorizado y dominio comparable de dependencias | Manifests originales de reserva/split y su ledger de gobernanza |
| Generación XM→UTC | Vínculo independiente del mismo evento con UTC y error acotado | Traza o atestación específica del servidor XM; alternativa externa solo si prueba identidad y relación temporal de generación/transporte, no mera similitud de precios |
| Cotas de recepción UTC | Resolución real de contadores, variación del oscilador entre mediciones y error absoluto de la referencia no demostrados | Calibración trazable de la referencia y de los contadores del boot; una frecuencia nominal o una recta factible entre NTS no sustituyen esas cotas |
| Mapping/calendario histórico | Sesiones, DST y excepciones del servidor/símbolo para cada periodo | Registros históricos específicos de XM; sesiones observadas actuales no sustituyen historia |
| Causas desconocidas | Traza de scheduling, red o terminal del intervalo pasado | Logs/ETW Windows y MT5 retenidos del momento; si nunca existieron, el dato puede ser irrecuperable |
| Admisión nueva | Ticks, barras completas, warmup/semillas propios, continuidad, membership y causalidad certificados | Captura prospectiva aislada y verificaciones aprobadas; nuevos datos no reparan retroactivamente gaps |

Se prepararon el índice de membership conocido/desconocido, la clasificación
por incidente con referencias OS, los brackets locales y las fuentes exactas
pendientes. **21 tests relevantes PASS.** No se repitieron probes MT5,
auditorías de features aprobadas, instalaciones, energía ni entrenamiento.
La verificación del prefijo nuevo fue necesaria para vincular la evidencia
OS y los incidentes a bytes realmente capturados.

NEXT_STATE: mantener captura y procesamiento en cuarentena, conservar los gaps
y recuperar procedencia original antes de admisión. La evidencia disponible no
permite cerrar ninguno de los cinco bloqueos globales por completo. No se pide
autorización ni intervención manual ahora; los artefactos indican exactamente
qué evidencia externa tendría que recuperarse. Ningún umbral, timestamp,
estrategia, contrato o proyecto ajeno fue modificado.

DISCOVERY_VALIDATION=BLOCKED; HISTORICAL_HOLDOUT=BLOCKED; FINAL_TEST=LOCKED;
DEMO=DISABLED; LIVE_TRADING=false. Sin entrenamiento, scoring o backfill.
