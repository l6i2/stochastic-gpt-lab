# Madurez del nuevo dataset — corte del 31 octubre 2026

## Decisión ejecutiva

**NOT_READY. Cero datos admitidos; DATASET_HASH=null.** La captura y sus monitores continúan activos en cuarentena. No se solicitó intervención humana ni se repitieron pruebas de instalación, energía o supervisión. No hubo entrenamiento, scoring, acceso a filas protegidas, cambio de estrategia ni modificación del otro proyecto.

NEW_CAPTURE_ID: `us30cap_15cbddec947f42c98219caa4cec978f2`. Inicio Ecuador **2026-10-31T13:33:53.341916-05:00**; estimación UTC **2026-10-31T18:33:53.341916+00:00**, con intervalo autenticado NTS [2026-10-31T18:33:52.983025+00:00, 2026-10-31T18:33:53.700806+00:00]. La cota es condicional a la precisión anunciada por la fuente; no certifica generación UTC de eventos XM.

## Datos acumulados y cobertura

Al corte: **2571 heartbeats, 0 callbacks tick**, cero registros propios M1/M5, cero registros de señales BUY/SELL y cero features. Los ceros de señales significan **ninguna señal verificada/almacenada**, no que MAIN_K no produjera señales en el mercado. No se calcularon MAIN_K ni labels con caché/historia anterior.

Duración desde activación según uptime del mismo boot: **05:10:17.563**, incluyendo suspensiones. Envolvente entre primer y último callback: 05:10:07.734. Suma de intervalos cortos entre callbacks: **03:33:33.296**. Ocho gaps suman **01:36:34.438**; mayor 01:07:46.484. El límite de diagnóstico es el ya existente de dos timers nominales de 5 segundos, nunca una tolerancia de admisión. Las sumas son apoyo observacional por uptime; no son tiempo efectivo de mercado certificado, y los extremos de gaps no localizan exactamente un fallo o desconexión.

Una sesión nativa y un segmento; cero cambios de segmento/reinicios observados en runtime. Dos transiciones a desconectado; 27 registros con flag DISCONNECTED. Reconexión no acredita pérdida cero de ticks. Cero sesiones operativas completas certificadas, cero días UTC completos certificados; también cero días calendario completos entre extremos parciales del host. No existe un mínimo de días UTC en el protocolo de este estudio: no se introduce uno nuevo ni se hereda el de otra cohorte.

`segments.json` contiene ventanas de 300000 ms ancladas a uptime de cada segmento, con callbacks, gaps y tiempos de extremos desconectados. **No son velas M5 ni sesiones XM ni conversiones UTC.** Toda ventana permanece QUARANTINED; cobertura científica certificada=0. No se inferieron horarios US30Cash de NYSE ni cierre de mercado por ausencia de ticks.

## Integridad y pertenencia

Se verificó cada fila del journal hasta el checkpoint durable: hash encadenado, ID/índice, bytes nativos idénticos al archivo fuente, cadena y secuencia nativas, identidad, contador de recepción, estado completo y cursores. Verificados manifiesto principal y autorización, evidencia de activación y ledger de decisiones; primer manifiesto de segmento coincide con su referencia inicial. No se alteraron originales, no se adoptó el prefijo anterior y no hubo CopyTicks/CopyRates ni backfill. El snapshot identifica prefijo exacto y hash: el archivo vivo puede crecer después.

Membership nuevo: sesión `pc_a_prospective_utc_v1_144295453_86572951924106_12318`, secuencias 139–2709 del segmento `obs_850c9ced05834b38b6e4c9e351a49f86`. IDs duplicados: cero; timestamps tick repetidos: cero porque no hay ticks. Coherencia OHLC/volumen no evaluable por falta de barras. Futuro respecto de UTC no evaluable sin semántica certificada; no se declara aprobado por ausencia de datos. Fuente de callbacks es el observador compartido, no un feed independiente ni una segunda muestra independiente por copiarlo.

Se verificó la cadena del ledger de exposición y su hash congelado. `exposure.json` añade un overlay encadenado de este acceso a metadata/raw post-inicio, sin reemplazar el ledger original ni abrir datos protegidos. La autorización y decisiones cierran nuevas incorporaciones científicas a la reserva anterior desde la frontera y reservan provisionalmente la nueva captura. Esto resuelve la decisión prospectiva de rol, **no reconstruye** memberships originales ni convierte dominios de tiempo desconocidos en comparables.

Siguen pendientes los IDs/splits originales del master, reserva exacta de Historical Holdout, reconciliación de dominios y exposición externa completa. El faltante legado de cierre/nonoverlap se conserva como historial: existe ahora cierre forward-only, pero no certificado retrospectivo de pertenencia. TRAIN agotado, Discovery Validation, Historical Holdout y Final Test permanecen bloqueados. No se leyó ninguna de sus filas para esta auditoría.

## Madurez congelada y soporte que falta

Protocolo SHA256 `ce5ab48ab95cbf4d6c07cb9b1cc9a13ab7f14ab7d14792b494ae2d19a21d45d9` intacto. Requiere **350 M5 propios cerrados de warmup**, semillas ATR/HA propias demostradas, **primeras 800 señales base consecutivas** y luego **100 barras M5 observadas** tras la última entrada. Faltan todos esos componentes; no se fija fecha ni se extiende un periodo según resultados. Las 100 barras no equivalen automáticamente a 500 minutos de reloj.

Soporte evaluable mínimo preregistrado: **200 señales total, 80 BUY, 80 SELL, tres folds por lado**. El soporte admitido actual es cero: faltan al menos esos conteos. No se evaluaron labels, purging, resultados ni potencia; estos son déficits frente a los mínimos, no garantía de poder estadístico ni una predicción del reparto BUY/SELL de las 800 señales.

Las seis dependencias congeladas se mantienen: stoch_k (7 barras mínimas, piso de snapshot 20), delta_k_1 (8, piso 20), relative_volume_20 (21), HA ready a 276 desde seed propio y toda su recurrencia, ATR nativo con inicialización completa, range_to_ATR heredando esa dependencia. Todas se calculan con barra cerrada shift 1 y deben estar listas antes de la decisión del siguiente callback M5, con orden de llegada/etapa para empates. No hay bytes de feature, contexto de decisión ni semillas nuevas para comprobar causalidad real. Se conserva la evidencia sintética/nativa aprobada sin repetirla ni elevar el CAUSAL_AUDIT global.

## Bloqueos y pasos automáticos siguientes

El capturador actual persiste callbacks crudos; **no exporta por sí solo barras M1/M5 ni contextos MAIN_K/features**. Esperar más heartbeats no completa un dataset de estudio. Los siguientes pasos seguros son continuar los callbacks/NTS/monitores ya activos, preservar cada sesión/gap y ejecutar una nueva auditoría con `tools/audit_dataset_maturity.py --out <directorio_nuevo>` solamente cuando exista evidencia material nueva. No se añadió otro supervisor ni tarea periódica redundante.

Cuando existan ticks reales, todavía se necesitarán barras propias verificables y un productor/diagnóstico nativo de features con seeds aislados o replay causal admitido con sus limitaciones, sin caché protegida ni backfill prospectivo. No se activó ese flujo adicional dentro de una auditoría. Después resolver membership/independencia, cobertura y procedencia/causalidad bajo el contrato aplicable; sellar dataset y solicitar autorización hash-bound antes de cualquier entrenamiento. No se presenta ahora una solicitud científica prematura.

Nueva herramienta de auditoría validada con **7 tests sintéticos PASS**: heartbeats no cuentan como ticks/barras/señales, gaps/desconexión conservados, ticks no inventan barras/features, bytes alterados y journal alterado rechazados, appends posteriores al checkpoint no adoptados y reparto temporal entre ventanas conservado. Ninguna prueba usa datos protegidos.

Estado final: CAUSAL_AUDIT=FAIL, TRAINING_READINESS=BLOCKED, DISCOVERY_VALIDATION=BLOCKED, HISTORICAL_HOLDOUT=BLOCKED, FINAL_TEST=LOCKED, DEMO=DISABLED, LIVE_TRADING=false. Captura provisional observacional, ningún dataset admitido. Próximo estado: seguir en cuarentena, sin backfill y sin fecha inventada de madurez.
