# UTC externo autenticado: mediciones NTS en PC A

Se resolvió el bloqueo de autenticidad para mediciones externas observadas. No se certifica el reloj Windows de forma continua ni la generación del tick XM. America/Guayaquil sigue como vista principal; no se cambia el módulo horario aprobado ni los timestamps originales.

## Resultado real

El snapshot contiene tres registros encadenados y cinco mediciones NTP autenticadas: Cloudflare y TimeNL respondieron en las dos primeras ejecuciones; la tercera obtuvo Cloudflare y conservó el timeout de TimeNL. No se reemplaza una respuesta NTS fallida por NTP sin autenticación etiquetado como autenticado. El registro inicial exploratorio, separado, se conserva localmente.

La causa del rechazo TLS previo en Cloudflare fue verify_code=20, unable to get local issuer certificate. Se utilizó un paquete certifi con raíces Mozilla en un directorio aislado, sin importar certificados a Windows, desactivar validaciones o cambiar settings de seguridad. Los seis wheels y sus hashes se contrastaron con metadata oficial PyPI por HTTPS. El manifiesto fija versiones, URLs, hashes de wheels, CA y 194 assets del runtime. No se instaló nada en el entorno de entrenamiento. La preparación reproducible es `python tools/prepare_nts_runtime.py`.

## Autenticación del protocolo

`python/nts_external.py` realiza el subconjunto cliente NTPv4 de [RFC 8915](https://www.rfc-editor.org/info/rfc8915/): TLS 1.3, cadena de confianza y hostname verificados, ALPN ntske/1, negociación única de protocolo 0 y AEAD15, exporter estándar con contextos direccionales C2S/S2C, identificador aleatorio de 256 bits, origen coincidente y autenticador AES-SIV de respuesta. Se rechazan estado no sincronizado/stratum inválido, replay/UID diferente, origen diferente, extensiones truncadas o datos modificados. Los primitives son de pyOpenSSL/cryptography aislados, no una implementación criptográfica casera. Se comprobó el vector determinista RFC5297 y respuestas de servidores reales. Esto no es una certificación de producto ni una auditoría externa del cliente nuevo.

Las fuentes están documentadas por [Cloudflare](https://developers.cloudflare.com/time-services/nts/) y [TimeNL/SIDN](https://nts.time.nl/). Se usan time.cloudflare.com y ntppool2.time.nl; no el servidor piloto de TimeNL. Netnod no fue accesible en los intentos acotados. El proof-of-concept antiguo de Netnod se revisó como referencia de protocolo, pero no se ejecutó ni se instaló como servicio.

Las claves del exporter y cookies NTS permanecen efímeras en memoria; no se serializan ni publican. Se conserva el hash de la respuesta, fingerprint del certificado, IDs, veredicto local de autenticación y procedencia del código/dependencias. NTS autentica simétricamente durante la conexión, no aporta una firma pública transferible del tiempo: un auditor puede reproducir el procedimiento y obtener una medición nueva, pero los registros publicados no permiten reconstruir una sesión TLS pasada sin sus claves. Los hashes locales tampoco constituyen por sí solos autenticación del servidor.

## Offset e incertidumbre

Cada medición registra t1/t4 del host, t2/t3 autenticados del servidor, RTT monotónico, procesamiento, stratum, leap, root delay/dispersion, precisión anunciada, capture_id, certificado/hash de paquete y hash encadenado. El modelo conserva explícitamente offset servidor menos host, sin corregir el reloj: [t3-t4-E, t2-t1+E]. E procede de root delay no negativo/2, dispersion, precisión y redondeo numérico del timestamp. No se añade una tolerancia escogida para aceptar datos. Los intervalos y RTT exactos quedan en authenticated_records.json; la primera medición Cloudflare situó el reloj local aproximadamente 0,76–0,87 segundos adelantado bajo ese modelo.

Ese intervalo es condicional: el error anunciado es una estimación del servidor y la ecuación necesita estabilidad del reloj local durante la consulta. La diferencia elapsed del host frente a perf_counter se registra, no se oculta. Los brackets de uptime permiten relacionar la recepción con callbacks reales bajo el supuesto declarado de deriva cero. No hay aún una cota calibrada de cuantización/deriva entre muestras ni del retraso entre generación del broker y callback. Por tanto la incertidumbre absoluta y la certificación causal permanecen BLOCKED. Autenticar el emisor no significa sincronizar Windows; el servicio w32time no se reconfigura y su estado anterior se conserva como observación independiente.

## Periodicidad e integridad

`tools/authenticated_utc_station.py` corre como subprocess aislado del monitor ya programado cada minuto; solo mide cuando corresponde, cada cinco minutos tras éxito. En fallos usa backoff exponencial acotado, sin reintentos intensivos. Registra éxitos y fallos, verifica hashes del runtime antes de importarlo, conserva archivos exclusivos y cadena de registros anclada por state. El verificador de historia rechaza cambios, pérdidas, ciclos y huérfanos sin reinterpretarlos. No se borra ni rellena una captura. El monitor sigue registrando ticks aunque falle la ruta NTS; el error no se transforma en autenticación exitosa.

Se observó ejecución del monitor con código 0 y la captura nativa continuó activa. Una respuesta NTS autenticada es puntual; ni el intervalo entre muestras ni el uptime de sesiones distintas se declaran certificados. La preparación usa exclusivamente archivos de cuarentena ya protegidos contra I/O de TRAIN. El EA nativo no se recompiló ni reinició y los históricos no se consultaron ni alteraron.

## Segmentos y auditoría

Cada modelo de recepción conserva el ID NTS y el prefijo/hash de la sesión nativa real. No se impone un offset a time_msc ni se igualan recepción y generación. Los segmentos sin prueba suficiente siguen QUARANTINED, incluidos los que no muestran gaps. CERTIFIED_SEGMENTS sigue vacío. Con la nueva evidencia material se revisó el guard causal: NATIVE_UTC_MAPPING_UNVERIFIED, cero filas normalizadas admitidas. No se ejecutó entrenamiento ni se abrieron datos bloqueados.

33 tests afectados PASS, incluyendo autenticador/header/UID/origen alterados, truncamiento, replay, vector RFC5297, integridad de historia, intervalos con demora asimétrica, continuidad y contratos causales existentes. Fuente externa autenticada: PASS para las mediciones observadas. CLOCK_UNCERTAINTY: cotas condicionales, sin certificación absoluta. CAUSAL_AUDIT=FAIL; TRAINING_READINESS=BLOCKED_BY_RESEARCH_GOVERNANCE.

Dependencia externa restante: evidencia de generación del evento XM y cotas de demora/cola, más continuidad del reloj con incertidumbre calibrada (por ejemplo una fuente local disciplinada y caracterizada con trazabilidad y enlace al contador, sin suponer que basta con instalar un cliente NTS). Se mantiene además el requisito del calendario fechado del servidor. No se exige una acción humana para continuar las mediciones periódicas. DISCOVERY_VALIDATION=BLOCKED, FINAL_TEST=LOCKED, DEMO=DISABLED, LIVE_TRADING=false.
