> Estado vigente C+F: corte exclusivo aplicado el 05/11/2026 a las 09:22:39 Ecuador.
> Dataset activo: `us30cash_m5_native_observations_20261105_01_dataset_02`.
> Evidencia auditada posterior al corte: 5 M1, 1 M5 propia verificada, 0 rechazos;
> warmup técnico 1/350, científico 0/350. No se adoptaron las 6 M5 anteriores.
> Roles futuros exclusivos verificados por decisión expresa; membership histórico
> desconocido permanece desconocido. Gate WAITING_FOR_EVIDENCE; entrenamiento BLOCKED.
> 63 regresiones PASS. [Aplicación y límites](CF_EXCLUSIVE_CUT_APPLIED.md).
> Recibos actuales: `research/studies/us30cash_m5_native_observations/exclusive_cut_v1/`.
> Los contadores de las secciones anteriores son históricos, no del dataset 02.

# Estado autoritativo de investigación — PC A

Corte: **2026-11-02 17:01 Ecuador**. Código revisado: `8b7394fa71db673c9d5f19973d8303fa7551b84f`
(HEAD previo a esta publicación; el JSON operativo identifica el HEAD vigente).
La evidencia inmutable de esta ejecución está en
`research/studies/master_mission_20261102_v1/`.

**No existe todavía un dataset independiente admitido para entrenar.**
La recolección activa no equivale a cobertura completa, independencia ni admisión.

## Datos separados y estado científico

| Conjunto | Evidencia y uso permitido |
|---|---|
| Histórico diagnóstico expuesto | 2024-01-02: 79.211 ticks, 1.376 M1, 276 M5; paridad nativa/Python publicada. No se repitió el ensayo en esta ejecución. |
| Histórico potencialmente independiente | Ningún intervalo demostrado admisible. Metadatos XM desde 2011 no prueban cobertura ni ausencia de exposición; no se abrieron periodos protegidos. |
| Captura propia original | `us30cap_15cbddec947f42c98219caa4cec978f2`, inicio UTC acotado documentado 2026-10-31T18:33:53.341916+00:00. 84.921 callbacks tick, 298 M1 y 16 M5 derivadas acumuladas, todas en cuarentena. |
| Ensayo de snapshots | `dbsnap_a5b5b6a8d777455d9cc63c8ca8690942`; productor separado. Consultas a base nativa, nunca prueba de recepción original ni warmup científico. Sus contadores vivos se publican por separado. |

`DATASET_ID=us30cash_m5_native_new_01_reserved` es una reserva de nombre.
`DATASET_HASH=null`, admitidos=0, BUY=0, SELL=0, warmup propio válido=0/350,
señales consecutivas=0/800, barras posteriores=0/100, evaluables=0/200,
BUY evaluables=0/80 y SELL evaluables=0/80. No hay fecha de madurez estimada.

La nueva auditoría verificó 14.928 ticks adicionales frente al último prefijo de
productor publicado, cero M5 completas adicionales y 23 M5 rechazadas nuevas;
una M5 abortada en frontera se informa por separado. Se verificaron los seis
segmentos y sus prefijos/membership de origen. Esto no resuelve el membership
científico histórico desconocido ni demuestra independencia de conjuntos con
intervalos no comparables. La diferencia 259/284 no se volvió a consultar.

## Requisitos y límites que siguen vigentes

- Cobertura exacta de callbacks frente a referencia nativa y semillas recursivas
  propias; OnTick no garantiza cada tick. No se ha probado que el productor
  original pueda reunir 350 M5 completas consecutivas.
- 350 M5 propias, primeras 800 señales consecutivas y 100 barras posteriores;
  mínimo 200 evaluables, 80 por lado y tres folds por lado. Sin reducción ni backfill.
- Membership independiente completo y causalidad conforme al contrato aplicable.
  La evidencia NTS/recepción no certifica el instante físico de generación XM.
- El ensayo de snapshots está autorizado para diagnóstico, **no para sustituir
  automáticamente la metodología de admisión**. Su progreso no resuelve por sí
  solo el bloqueo del productor original. Cualquier adopción científica requiere
  propuesta y aprobación específicas; no se aplica aquí.
- Legados irrecuperables permanecen desconocidos/excluidos. Esperar más ticks no
  recupera esos manifests ni autoriza a reinterpretar los roles congelados.
- Dataset sellado, protocolo/whitelist/presupuesto vinculados y autorización
  específica antes de cualquier entrenamiento. No se solicita esa autorización
  ahora: el paquete de datos aún no está completo.

Warmup histórico de indicadores y contexto diagnóstico nativo no sustituyen
warmup científico prospectivo. Se conservan contratos y originales. La causalidad
sintética/nativa previamente probada no convierte el `CAUSAL_AUDIT` global en PASS.

## Ejecución futura preparada, no ejecutada

Se reutiliza `tools/admitted_training.py` y el paquete congelado
`research/studies/us30cash_m5_native_pretrain_v1/`. La whitelist vigente contiene
solo stoch_k, delta_k_1, ATR, relative_volume_20, ha_direction y range_to_ATR.
Volume Profile, estructura, sesiones e intratrade no se incorporan como nuevas
features de entrenamiento por esta misión. Una configuración logística L2,
BUY/SELL separados, FOLLOW/INVERT, cuatro folds cronológicos con purga; máximo
ocho fits planificados y **cero autorizados**. No hay scoring ni entrenamiento.

## Automatización y comprobación de progreso

Se reutilizan collector, worker, observador, NTS, supervisor y tareas existentes.
El monitor supervisado actualiza cada 60 segundos
`outputs/status/AUTONOMOUS_RESEARCH_STATUS.json`; no depende del chat abierto.
No se añadió otra tarea ni proceso residente. El intento de registrar una tarea
adicional recibió acceso denegado; se descartó y se reutilizó el monitor existente.
Se reinició exclusivamente el reporter de metadatos para cargar la mejora.
No se reinició XM ni se alteraron cursores. No se cambió energía ni el otro proyecto.

Una comparación real de 130,59 segundos mostró 75 ticks nuevos, 104 registros
consumidos por el worker y un único worker sin instancias inesperadas; CPU media
1,71% de un núcleo en esa ventana. No prueba cobertura completa.

Comandos de una ejecución, desde la raíz del repositorio:

```powershell
.\tools\research_control.ps1 STATUS
.\tools\research_control.ps1 RESUME
```

RESUME comprueba el alcance de la tarea existente y reanuda solo el guardian
idempotente. STATUS refresca metadatos sin consultar históricos ni entrenar.
El JSON conserva hashes de los recibos leídos, contadores y bloqueos. Distingue
`PASS`, `FAIL`, `WAITING_FOR_DATA`, `WAITING_FOR_AUTHORIZATION` como presentación
del gate existente; no constituye una segunda vía de autorización. Errores,
evidencia corrupta o monitores obsoletos fallan de forma cerrada. Las ventanas
de frescura del monitor no son tolerancias de certificación temporal.

Próxima acción automática: continuar recolección y procesamiento en cuarentena,
registrar nuevos intervalos y actualizar madurez. No reauditar ventanas antiguas
sin evidencia nueva, no promover datos ni entrenar automáticamente. Para consultar
el estado vivo, usar STATUS o el JSON; este documento conserva el corte publicado.

`DISCOVERY_VALIDATION=BLOCKED`, `HISTORICAL_HOLDOUT=LOCKED`, `FINAL_TEST=LOCKED`,
`DEMO=DISABLED`, `LIVE_TRADING=false`. Intervención manual actual: ninguna.

## Actualización operativa — 2 de noviembre, 19:37 Ecuador

El corte anterior permanece en la evidencia v1; no representa los contadores
actuales. En la comprobación posterior había 20 M5 derivadas originales, pero
seguían sin warmup científico admitido. El reporte detectó correctamente FAIL:
el ensayo separado de snapshots no tenía productor/watchdog activos y su último
recibo era RETRYING, con `REAL_OR_UNKNOWN_OR_CHANGED_XM_IDENTITY`. La inspección
actual comprobó DEMO, servidor y carpeta esperados; no se reinterpretó ese error
pasado como prueba de una causa concreta de desconexión ni de reinicio físico.

Se demostró una omisión de recuperación: el guardian persistente no reponía el
watchdog separado tras perderse durante la misma sesión. Se añadió su arranque
solo cuando la captura separada está habilitada, con intervalo de reintento y
el mutex existente. No se cambió el productor ni su manifest/pin. Se recuperó
como época 17 con corte nuevo y sin rellenar el intervalo perdido. La evidencia
posterior se conserva en `research/studies/master_mission_20261102_v2/`.

## Revisión de admisión del 4 de noviembre

El recibo reproducible `research/studies/final_mission_20261104_v1/offline_receipt.json`
vincula siete exportaciones permitidas de MT5 del 2 de enero de 2024 con su inventario
sellado. `tools/offline_study_receipt.py --out <archivo_nuevo>` verifica sus hashes,
reconstruye M1/M5 y reproduce las trayectorias congeladas en Python. El día aportó
79.211 cotizaciones, 1.376 M1 y 276 M5. Coincidieron OHLC y coordenadas nativas de
las barras. Hay cuatro saltos M1 y diez discrepancias de volumen en cada escala.
Se verificaron 13 BUY, 15 SELL, 56 trayectorias y 3.279 llegadas de decisión.
FOLLOW e INVERT cerraron 19 trayectorias cada uno y censuraron nueve por modo.
Sus sumas cerradas fueron +472,12 y −999,06 unidades de precio, respectivamente.

El replay comprobó el primer tick de entrada en la M5 siguiente y los límites
nativos declarados de features en 28 señales, incluidos los de Volume Profile
y Heikin Ashi. El calendario y los horarios históricos de Ecuador siguen sin
atestación. La causalidad completa exige bytes y semillas verificables en un
dataset independiente. La whitelist congelada rige las features de entrenamiento.

La matriz de períodos usa exclusivamente metadatos de exposición y procedencia.
La cadena del ledger se verificó. Siguen faltando membership original, límites
exactos del holdout y evidencia de no solapamiento en dominios comparables.
El día recuperado está expuesto. El ensayo separado verificó 47 M5 y 343 M1
en su corte, con cero contribución al warmup original. Los tres dominios siguen
separados: histórico diagnóstico, observaciones en cuarentena y datos admitidos.

El paquete preregistrado conserva la reserva de ID y un hash de dataset nulo.
El ejecutor preparado aplica logística BUY/SELL, FOLLOW/INVERT y walk-forward
cronológico con purga. El presupuesto preregistrado prevé hasta ocho ajustes,
con cero autorizados. La condición crítica es demostrar y sellar un intervalo
independiente con cobertura y causalidad. Los productores programados acumulan
evidencia. La alternativa offline requiere admisión metodológica específica
antes de que su evidencia pueda alimentar un estudio. `STATUS` expone el corte
vivo y el recibo de este diagnóstico. El gate permanece `WAITING_FOR_DATA`.

## Evidencia incremental del 4 de noviembre, 22:09 Ecuador

El [recibo de avance](../research/studies/admission_progress_20261104_v1/receipt.json)
verificó 3.585 entradas derivadas originales y 2.166 registros del ensayo de
snapshots contra sus prefijos publicados. Se conservó la matriz de períodos
anterior y se vinculó su hash. La comprobación de presencia de los tres
manifiestos esperados confirmó que master, splits y el manifiesto de la cohorte
reservada siguen ausentes. Las filas de los conjuntos protegidos quedaron fuera
de la revisión.

El corte registró 144.456 callbacks, 543 M1, 30 M5 originales acumuladas y 172
M5 rechazadas. La racha técnica era de una barra, con máximo observado de cuatro.
El ensayo separado registró 382 M1 y 52 M5. El warmup científico sigue en 0/350,
las señales consecutivas en 0/800, las barras posteriores en 0/100 y las
evaluables en 0/200, incluidas 0 BUY y 0 SELL frente al mínimo de 80 por lado.

`TRAINING_ADMISSION_GATE=WAITING_FOR_DATA`. Hay cero paquetes admitidos y cero
grants. Para una admisión faltan un intervalo con independencia demostrable,
cobertura exacta, causalidad con semillas verificadas y los umbrales anteriores.
Los metadatos pendientes son membership original de splits y señales, reserva
exacta de Historical Holdout, cierre o no solapamiento de la reserva prospectiva
legada, conciliación de dominios temporales e historial de exposición externo.
La metodología de snapshots sigue pendiente de autorización científica propia.
Las tres tareas programadas de UTC, cuarentena y recuperación estaban activas.
El corte de salud fue limpio. La adquisición continúa en cuarentena.

Para reproducir la verificación incremental con el corte disponible, ejecutar
`.venv\Scripts\python.exe tools/admission_progress_receipt.py --out <archivo_nuevo>`.

## Rescate de seis alternativas del 5 de noviembre

Se completaron A, extracción histórica aislada; B, agregación M1→M5; C, productor
experimental con identidad propia; D, verificación temporal con NTS; E, búsqueda
de metadatos y ensayo de frontera independiente; y F, estudio propuesto sellado
con validación sintética. Los resultados y su matriz están en el informe de las
seis alternativas y en `research/studies/six_alternatives_resolution/`.

[Informe de seis alternativas](SIX_ALTERNATIVES_RESOLUTION.md)

A preservó 79.211 cotizaciones, 1.376 M1 y 276 M5 del día diagnóstico autorizado.
La muestra API corregida contiene 223 ticks. B confirmó OHLC y volumen de 276
agregados contra M5 nativa; 272 contienen cinco M1 y cuatro conservan huecos.
C produjo dos M5 consecutivas y 14 M1 sin rechazos, con doble lectura exacta y
estado conservado tras reapertura en procesos independientes. El ensayo finalizó
de forma controlada y dejó su base en cuarentena. Las pruebas sumaron 25 PASS.

El corte original de las 07:27 Ecuador registra 147.003 callbacks, 557 M1 y
30 M5 completas acumuladas, 179 M5 rechazadas y racha cero. El warmup científico
es 0/350, señales 0/800, barras posteriores 0/100 y evaluables 0/200, con soporte
BUY/SELL de cero frente a 80 por lado. C aporta cero barras al contador original.
El estado de salud del corte fue limpio y el gate permanece WAITING_FOR_DATA.

La mejor vía técnica es el productor C por su procedencia explícita, paridad,
persistencia y coste medido. La vía científica es F, un estudio nuevo pendiente
de aprobación. Conserva estrategia y umbrales y propone la admisión offline de
observaciones nativas y continuidad entre sesiones solo con cobertura y horario
demostrados. La sesión de 23 horas observada en el servidor admite 276 M5; un
reset obligatorio entre esas sesiones impide alcanzar 350 dentro de una sesión.
La vigencia y las excepciones del horario siguen pendientes de certificación.

El ledger no prueba independencia frente a reservas de límites desconocidos.
Para avanzar científicamente se necesita evidencia original de membership y
roles o una decisión explícita sobre la asignación futura de roles, junto con
el contrato aprobado de observaciones nativas. Después se requerirán datos
suficientes con semillas, cobertura y causalidad verificadas. El dataset sigue
sin admisión y con hash nulo. El protocolo de entrenamiento planifica hasta ocho
ajustes y autoriza cero. El productor original, worker, NTS y guardian mantienen
su supervisión programada. Los conjuntos protegidos conservan sus restricciones.


## Estudio C + F activado — 5 de noviembre de 2026, Ecuador

Contrato nuevo `CF_NATIVE_OBSERVATIONS_CONTRACT_V1_20261105`, autorizado
expresamente; contratos anteriores intactos. Productor científico separado
`cfprod_5c64f0781dc148e5896391b1492ba144`, captura
`dbsnap_e35f302e858e4b0a82c73821bef5667b`.

Corte operativo auditado: **17 M1, 2 M5 reales, 2 M5 consecutivas técnicas,
0 rechazadas**. Paridad exacta M1/M5 en ambas; prefijo preservado entre auditorías,
con avance de 1 a 2 M5. Dos inicios de proceso registrados; el reinicio técnico
abre epoch 2 sin backfill, conserva primera observación y datos de epoch 1.
Warmup técnico 2/350; warmup científicamente admitido 0/350. BUY=0, SELL=0,
primeras señales 0/800, barras posteriores 0/100, evaluables 0/200,
BUY/SELL evaluables 0/80 y folds evaluables 0/3 por lado.

NEW_STUDY_DATASET_ADMISSION=WAITING_FOR_EVIDENCE. Membership de artefactos
propios trazado; exclusividad y no solapamiento aún no demostrados frente a
reservas antiguas con extremo desconocido. Una única solicitud científica está en
`research/studies/us30cash_m5_native_observations/RESERVATION_SCOPE_DECISION_REQUEST.md`.
No se aplicó la decisión. Calendario PARTIAL, ninguna transición entre sesiones
certificada. Semillas propias y paridad nativa iATR pendientes. La disponibilidad
física registrada precede al uso offline; no prueba la entrada original en vivo
ni la generación física UTC. CAUSAL_AUDIT global permanece FAIL sin reinterpretarlo.

DATASET_HASH=null; datos científicos admitidos=0. Entrenamiento, scoring,
Discovery Validation, Historical Holdout, Final Test y DEMO siguen cerrados.
LIVE_TRADING=false y terminal_trade_allowed=false verificado. La automatización
existente mantiene adquisición, checkpoints, NTS, estado y recuperación sin
backfill. No se reinició XM ni Windows. La prueba de reinicio físico sigue futura.

56 tests relevantes PASS. Informe y recibos reproducibles:
`docs/NEW_STUDY_C_F_ACTIVATION.md` y
`research/studies/us30cash_m5_native_observations/operational_receipt.json`.
El estado vivo puede avanzar después de este corte; no se presenta como dataset
sellado. Próximo estado: seguir capturando en cuarentena, reunir evidencia de
calendario y resolver el alcance futuro de reservas antes de admisión.
