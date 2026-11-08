# Checklist de admisión B+C

La tabla es generada desde el recibo real; PASS de una condición no admite el dataset.

| Gate | Estado actual |
|---|---|
| ATR_seed | WAITING_FOR_EVIDENCE |
| BID_ASK | WAITING_FOR_EVIDENCE |
| HA_seed | WAITING_FOR_EVIDENCE |
| OHLC | WAITING_FOR_EVIDENCE |
| calendar | WAITING_FOR_EVIDENCE |
| causality | WAITING_FOR_EVIDENCE |
| exclusivity | PASS |
| exit_horizons | WAITING_FOR_EVIDENCE |
| features | WAITING_FOR_EVIDENCE |
| folds | WAITING_FOR_EVIDENCE |
| hashes | WAITING_FOR_EVIDENCE |
| historical_continuity | WAITING_FOR_EVIDENCE |
| independence | PASS |
| membership | WAITING_FOR_EVIDENCE |
| no_leakage | WAITING_FOR_EVIDENCE |
| provenance | PASS |
| reproducibility | PASS |
| tick_coverage | WAITING_FOR_EVIDENCE |

Umbrales invariables: 350 contexto; 800 señales base; 100 posteriores; 200 evaluables después de purga; 80 BUY; 80 SELL; tres folds evaluables por lado. No sumarlos entre segmentos incompatibles.

Los certificados de calendario requieren verificación independiente y registro por hash; la lista está vacía. Las semillas requieren oráculo de este prefijo/vintage. Ningún booleano de readiness ni un contador promueve datos.

DATOS: WAITING_FOR_DATA. ADMISION: no concedida. AUTORIZACION DE ENTRENAMIENTO: no solicitada. El paquete solo candidato está en cuarentena; ambas allowlists científicas siguen vacías. [Plan de ejecución](BC_FIRST_TRAINING_EXECUTION_PLAN.md).


## Estados de revisión — schema 2

WAITING_FOR_DATA: faltan umbrales. WAITING_FOR_EVIDENCE: los umbrales existen pero falta prueba. FAIL: una condición falla o se excede la muestra fija. READY_FOR_ADMISSION_REVIEW: paquete técnico completo, aún sin admisión. En todos los estados training_authorized=false; la autorización de entrenamiento sigue separada. El cache valida también el paquete candidato y su versión inmutable. [Auditoría de cierre](BC_FINAL_PREMARKET_AUDIT.md).
