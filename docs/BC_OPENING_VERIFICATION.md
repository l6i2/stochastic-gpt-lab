# Verificación real de apertura B+C — 8 de noviembre de 2026

**WAITING_FOR_MARKET. No se confirmó apertura ni una cotización nueva.** La adquisición real se ejecutó y no hizo consultas históricas: el límite nativo sigue null y el último tick continúa siendo anterior al corte.

Servidor nativo verificado: XMGlobalSC-MT5 5, US30Cash, conexión de investigación y trading deshabilitado. Última observación del worker: 2026-11-08T16:24:21.942-05:00 Ecuador (etiqueta del host; UTC original conservado en JSON). Tick original `time_msc=1794009599968`, BID=51290.37, ASK=51296.37. Es el mismo ancla anterior; FIRST_NEW_NATIVE_QUOTE=null. No se lo presenta como un evento nuevo ni se le asigna UTC certificado.

## Especificación actual y próxima ventana

Se ejecutó una vez el SessionCalendarProbe existente, sin instalar ni compilar nada. Su fuente y EX5 coinciden con los hashes aprobados. El log nuevo recuperó START, CLOCK, QUOTE/TRADE de cinco días y END, con servidor/símbolo correctos. Las sesiones de cotización semanales observadas son lunes a viernes 01:00–24:00 nativo XM; no hay sesión dominical registrada. La negociación comienza 01:05; termina 23:55 de lunes a jueves y 23:50 el viernes.

Próxima ventana semanal nominal: **lunes 9, 01:00 XM para cotizaciones; 01:05 XM para negociación**. Como referencia operativa, la diferencia de reloj calculada observada en esta consulta produce **domingo 8, 18:00 Ecuador / Nueva York EST, 23:00 UTC** para cotizaciones, y cinco minutos después para negociación. **La equivalencia es orientativa y condicional**, no un mapping XM→UTC certificado ni una garantía frente a excepciones. El cálculo usa la observación actual, no un offset fijo impuesto al historial. TimeTradeServer no se trata como fuente UTC independiente.

La vigilancia no se programa por esa equivalencia: el worker ya comprueba ticks cada cinco minutos y exige una cotización nativa realmente nueva antes de vincular el primer intervalo. No se modificó el módulo horario aprobado ni la normalización de timestamps. Calendario histórico y excepciones siguen PARTIAL; esta especificación semanal no autoriza puentes científicos por sí sola.

## Resultados efectivamente obtenidos

| Campo | Resultado |
|---|---|
| FIRST_NEW_NATIVE_QUOTE | null |
| MARKET_SESSION_STATUS | WAITING_FOR_MARKET |
| BARS_M1 | 0 |
| BARS_M5 | 0 |
| TRAIN_CONTEXT_PROGRESS | 0/350 |
| TRAIN_SIGNALS | 0/800 |
| DATASET_ADMISSION | WAITING_FOR_DATA |

El episodio transitorio de interfaz sin respuesta se recuperó sin reiniciar XM ni Windows; la consulta IPC y el probe terminaron. Se verificó el checkpoint/cadena B+C y el cierre C+F mediante el recuperador existente. Eso no demuestra un apagado físico ni adquisición de barras después de un reinicio: no se realizó esa prueba y no hay datos posteriores al corte que puedan certificarse todavía.

No se redescargaron históricos antiguos, no se sumaron barras ajenas ni se generaron fixtures para inflar contadores. La adquisición exige rangos completos dentro de la reserva B+C; mientras native_floor=null no consulta CopyRates/CopyTicksRange. Los controles de BID/ASK, volumen, M1/M5, hashes, timestamps y membership se ejecutarán sobre los nuevos artefactos reales cuando existan. Los oráculos propios esperan los hitos 15/30/276/350 y la auditoría de madurez se actualiza con cambios reales.

La tarea existente continúa cada cinco minutos y al inicio de sesión, IgnoreNew y lock de archivo. El guardian mantiene recuperación y revisión de admisión. No se creó otro capturador ni se repitieron las 54 regresiones previamente aprobadas. Pendientes: primera cotización, datos propios suficientes, paridad de prefijos, calendario/excepciones verificados y admisión seguida de grant específico. Ningún entrenamiento ni scoring protegido se ejecutó; cero órdenes.

Recibos y hashes: [índice](../research/studies/bc_train_future_eval_v1/opening_verification_20261108/index.json). La apertura quedará demostrada únicamente por una nueva observación nativa y sus artefactos, no por el horario nominal.
