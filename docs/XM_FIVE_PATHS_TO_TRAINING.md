# Cinco rutas hacia el primer entrenamiento

Se recomienda la ruta B, con adquisición diferenciada C y reutilización D/E. Es una propuesta inactiva: no existe hoy un intervalo histórico exacto elegible para un nuevo TRAIN. No se ejecutaron entrenamientos, scoring ni consultas históricas adicionales.

| Ruta | Resultado verificable | Decisión |
|---|---|---|
| A: histórico actual | B comparte reserva C+F; legacy no permite resolver membership completo | No usar para nuevo TRAIN |
| B: TRAIN histórico y evaluación futura | Permite separar desarrollo expuesto y evaluación realmente independiente | Recomendada, condicionada a reserva y admisión |
| C: híbrida | Diferencia recepción original y recuperación; no crea independencia por descarga | Apoya B, contrato nuevo inactivo |
| D: recuperador existente | 246.397 ticks, 1.295 M1, 251 M5 en 302 intervalos únicos; 320 intentos conservados | Reutilizar, sin repetir consultas |
| E: entrenador | 25 tests sintéticos PASS, estimadores simulados; cero fits científicos | Preparación técnica completada |

La matriz estructurada contiene las once columnas solicitadas: [five_paths.json](../research/studies/first_training_five_paths_20261108/five_paths.json).

## Respuestas científicas

1. Es posible metodológicamente entrenar con un histórico autorizado y evaluar datos nuevos sin contaminarlos. **No podemos iniciarlo ahora**: falta TRAIN admitido y grant específico. Exposición declarada de desarrollo no equivale por sí sola a prohibición; TRAIN agotado, conjuntos protegidos y reservas incompatibles sí impiden estos usos.
2. Ningún intervalo exacto actual está demostrado elegible. No se inventa DATASET_ID ni DATASET_HASH. El histórico B sigue siendo copia diagnóstica de C+F; el intervalo legacy conocido tampoco tiene un rol TRAIN nuevo demostrado.
3. B+C es la ruta mejor sustentada para reducir dependencia de PC A encendida durante la adquisición de TRAIN. No hay fecha verificable de finalización ni garantía de ser la más rápida en días. La evaluación futura, cobertura, sesiones y semillas siguen siendo necesarias. El recuperador no prueba recepción original.
4. Falta una decisión conjunta sobre método y reserva futura exclusiva. El corte debe producirse después de aprobarla. No se reasignan datos anteriores. Después todavía harán falta admisión por hashes y autorización específica de entrenamiento.
5. Continúan productor C+F en cuarentena, guardian, NTS/UTC, recuperador diagnóstico y monitores existentes. Los recibos locales son automáticos; publicar futuras revisiones en GitHub requiere una sesión o credencial autorizada.

## Datos y limitaciones

STATUS actual: epoch 39_398136265, 88 M5 acumuladas, 0 consecutivas y 0 de warmup científico; BUY=0 y SELL=0. No sumar las 251 M5 B a las 88 A. El contador acumulado sobrevive a interrupciones; la continuidad no se presume.

Se conserva la auditoría anterior de 251 M5 contra M1 y 1.295 M1 contra ticks, incluidos volumen BID y precios. Dieciocho intentos sustituidos permanecen preservados. Los 60 M1 ausentes coinciden con el cierre QUOTE observado; esto no certifica todas las excepciones históricas. La ventana de 30 M5 diagnósticas tiene MAIN_K exacto, 17 comparaciones ATR candidato exactas y 30 Heikin Ashi exactas; son datos retrospectivos, no 350 barras propias ni causalidad global PASS.

El horario nativo observado permite 276 M5 por sesión completa; 350 requieren continuidad entre sesiones demostrada o una definición histórica nueva aprobada. La propuesta explicita 350 barras de contexto antes de la primera señal: mínimo teórico 1.250 M5 para 800 señales y 100 barras posteriores si hubiese una señal en cada barra. No es una predicción de frecuencia ni una reinterpretación de C+F.

## Reparaciones de software

El gate comprueba ahora árbol de trabajo limpio, vincula esquema/plan/origen/presupuesto al grant y rechaza límites observados ausentes o inválidos antes de cargar el dataset. Las filas deben estar dentro de los límites y ordenadas. El runner verifica soporte purgado mínimo antes del primer fit. Estos checks numéricos no sustituyen el certificado de causalidad, membership ni cobertura.

Se preparó un callback opcional para retener los modelos BUY/SELL del fold 4 prefijado, sin selección por rendimiento ni noveno fit. No se conectó a un entrenamiento real ni a evaluación automática. Su uso prospectivo pertenece al método propuesto. Las listas de autoridad y admisión permanecen vacías.

Los tests prueban rechazo por cambios locales, límites inválidos, filas fuera de rango, soporte insuficiente y conservación de exactamente ocho fits simulados. No se ejecutaron fits sklearn reales ni se leyeron conjuntos protegidos.

Fuentes: [status sellado](../research/studies/first_training_five_paths_20261108/status.json), [recuperación previa](../research/studies/xm_historical_recovery_20261108/results.json), [propuesta](PROPOSED_FIRST_TRAINING_STUDY.md), [plan](TRAINING_ADMISSION_ACTION_PLAN.md). Los hashes de los archivos fuente se incluyen en index.json; describen evidencia, no certifican un dataset.
