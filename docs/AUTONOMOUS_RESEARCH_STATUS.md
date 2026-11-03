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
