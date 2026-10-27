# Cloud preparation audit — 2026-10-27

Base auditada: `c9ad4aa35a391ca80bd3da371e0393c5c5282d58`, rama
`research/full-pipeline`, actualizada mediante fetch/checkout/pull --ff-only.
No se ejecutaron terminal MT5, órdenes, scoring, training, backfill ni lectura de
raw/outcomes de cohorte. No se modificaron estrategia ni datasets.

## Hallazgos y resolución

| Área | Verificación y resultado |
|---|---|
| Tiempo | API pública única `time_semantics.py` delega al mapping y guard existentes. Zonas IANA fijadas; health usa la misma vista New York. Fold DST se compara como UTC. |
| Causalidad | Exact equality aceptada; +1 ms futuro rechazado; stale, unidades, missing, naive y doble conversión cubiertos. Cinco segundos es límite de antigüedad, nunca tolerancia futura. |
| Clock | Captura externa Python/PowerShell; master read-only de reloj+sesiones; nonce nuevo, compilación/hashes, timeout, END y reportes sin sobrescritura. Mapping externo no inferido. |
| MAIN_K | PASS nativo previo: 960 filas, 930 ready y 30 warmup, cinco fixtures; max error 1.4210854715202004e-14 a tolerancia fija 1e-10. Se preservan código/evidencias. |
| Session calendar | PASS_WITH_RUNTIME_GUARD es contención operacional, no calendario histórico certificado. Viernes, weekend, DST, snapshot expirado y holiday unknown fallan cerrado según tests existentes. Master captura snapshot nuevo sin activarlo. |
| Collector | Código congelado intacto: cursor secuencial desde 2026-10-19, lock, staging, gzip hashes, atomic replace, recuperación de día huérfano y archivo de manifests. Tests sintéticos de idempotencia, no-backfill y crash/restart. Duplicados de timestamp se reportan, no se eliminan silenciosamente; duplicados de día se rechazan. |
| Maturity | Health usa solo metadata. No se recalculó la cohorte. El cambio de código/timezone exige un reporte futuro nuevo con hashes; no vuelve válido ningún reporte anterior. Metadata v1 MAIN_K no equivale a nativo; v2 preparado sigue sin activarse. |
| Evaluator | candidate_frozen=true y status FROZEN; hashes candidato/cohorte/maturity/protocolo/auditoría/código/tabla; autorización manual; nonce y par consumidos durablemente antes de parsear outcomes; ledger canónico no eludible cambiando audit path; output exclusivo; no retry. Solo fixtures ejecutados. |
| Drift | Productor común y whitelist v2 exacta para cinco features implementadas, bins fijos, builder TRAIN y comparador hash-bound. VP sin productor compartido se excluye explícitamente; v1 archivado. READY tooling, baseline real NO ajustado, stream NO conectado. |
| Shadow | Disabled, cero órdenes, allowlist read-only. Reserva SQLite antes de policy; duplicados/crash no repiten decisión. JSONL flush/fsync; reconnect/stale/session guards. |
| DEMO | READY_BUT_DISABLED_FULL significa mocks completos y persistencia; no adaptador broker ni activación automática. REAL/UNKNOWN hard fail y límites probados. |
| Manifest chain | Bytes disponibles en Git: VERIFIED/PARTIAL; no inventar antecesores. Herramienta local incorpora snapshots exactos por hash sin tocar raw ni ledger original; prefijo ausente UNVERIFIABLE_PRE_ANCHOR. |
| Docs | Status actuales consolidados; checkpoints contradictorios movidos a archive/pre_cloud_20261027 conservando bytes. Protocolo científico conservado byte-exact en archivo con seal; el documento actual añade solo nota operacional y nuevo seal. Candidatos/autorizaciones futuros deben enlazar el hash nuevo. |
| Portabilidad | Tests de seguridad usan límites sintéticos en lugar del manifest privado; el lector de rutas del smoke interpreta rutas Windows también en Linux. No se modifica el gate operacional de splits. |

## Límites conocidos que no se ocultan

La escritura del manifest y su sidecar del collector son dos reemplazos separados:
un crash intermedio puede producir mismatch y bloquear el siguiente run. Es
fail-closed; no se relaja ni reescribe el contrato congelado para recuperar
silenciosamente esa situación. El wrapper de colección conserva snapshots para
revisión/recuperación local con evidencia. Cambiar el source congelado del
collector invalidaría su identidad: no se cambió.

No existe candidato: 17 hipótesis, cero supervivientes. Los guards de evaluación
siguen cerrados. El viejo metadata de soporte no demuestra parity con el trigger
nativo. Ningún reloj correcto permite afirmar CAUSAL_AUDIT PASS ni activar el
metadata v2 preparado sin una revisión versionada de sus evidencias. Su texto
congelado conserva el antiguo pending parity; el PASS nativo posterior no lo activa
automáticamente ni subsana el mapping/causalidad restante.

La referencia NTP es diagnóstica y se corrobora con TLS; no se presenta como una
certificación criptográfica de timestamps broker. El mapping exige evidencia
externa exacta, intervalos acotados y revisión de autenticidad. El analizador
puede certificar integridad de captura/consistencia observada, no offsets por
intuición, vacaciones futuras o estabilidad de reloj a largo plazo.

La sesión local anteriormente activa y el Task Scheduler no son observables
Cloud. FUTURE_COLLECTION_ACTIVE=YES conserva el último estado informado. No se
actualizan recuentos de ticks, señales ni maturity desde aquí.

## Verificación reproducible

```text
python -m venv .venv
.venv/bin/python -m pip install -r requirements-cloud.txt
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m pytest -q
.venv/bin/python -m compileall -q python controller scripts tools tests
git diff --check
```

Resultados y skips exactos: `outputs/status/CLOUD_VERIFICATION.json`.
MQL5 compile/run, reloj Windows real, NTP/TLS desde esa PC, XM/MT5, Task Scheduler,
correspondencia externa native/UTC y revisión causal: **LOCAL_REQUIRED**.
Los tests C++ sintéticos disponibles en Linux no sustituyen esas pruebas.

Preparación completa significa código, mocks, pruebas Cloud, documentación y
handoff publicados; no ejecución nativa ni aceptación científica. Las cuatro
acciones agrupadas están en `docs/LOCAL_PC_FINAL_STEPS.md`.
