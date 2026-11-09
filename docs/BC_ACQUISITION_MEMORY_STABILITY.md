# Estabilidad de memoria en la adquisición B+C

El aplazamiento anterior fue el guard de recursos. La medición inmediata registró unos **284 MiB** disponibles frente al mínimo de **384 MiB**, con más de 40 GiB libres en disco. Cuando volvió el margen se reanudó el mismo cursor. La presión coincidió con un conjunto de trabajo elevado de Chrome. Las mediciones disponibles no atribuyen la presión a un proceso concreto ni muestran una fuga de XM, Python o SQLite.

Se limitó la tarea existente a dos M5 por ejecución. Cuando el guard aplaza la adquisición, el worker deja cerradas la sesión IPC y SQLite, comprueba el margen hasta tres veces en 15 segundos y admite un solo reintento de una M5. El mínimo sigue en 384 MiB y 2 GiB libres en disco. La revisión lee JSONL línea a línea y descarta los ticks de cada intervalo al terminarlo. Los triggers y el mutex se conservaron. El parche reside fuera de los archivos congelados del productor.

| Medición | Resultado |
|---|---:|
| XM RSS máximo muestreado | 17.3 MiB |
| XM pico de conjunto de trabajo desde el arranque del proceso | 218.7 MiB |
| Python/worker pico de conjunto de trabajo con adquisición | 42.7 MiB |
| Python/worker memoria privada al final | 250.9 MiB |
| SQLite máximo de su asignador en el worker | 194,528 bytes |
| RAM del sistema disponible al inicio y al cierre de la adquisición | 534.5 y 589.5 MiB |
| Mínimo de RAM disponible observado durante el muestreo | 425.4 MiB |

El SQLite medido vive dentro de Python. El valor del asignador no incluye la caché de archivos de Windows. El worker anterior, medido sin barra nueva, alcanzó 38.9 MiB de conjunto de trabajo. Las cargas de los dos ensayos difieren. En una comparación sobre el mismo archivo real, leer 944 ticks línea a línea mantuvo las filas idénticas y redujo el pico de asignaciones Python un 15.5% (950,268 a 803,412 bytes).

La ejecución parcheada procesó 1 M5 reales. Otra ejecución conservó el cursor, la cantidad de M5 y los hashes de los vintages. La revisión verificó una sola entrada por intervalo, el checkpoint y la cadena. El corte registró **4154 ticks**, **25 M1** y **5 M5** verificadas. Contexto consecutivo **5/350**. Los 26 tests B+C pasaron. La recuperación con presión persistente se ensayó mediante mocks; la adquisición en vivo se realizó con margen suficiente.

La tarea mantiene los disparadores existentes y los oráculos 15/30/276/350. El historial dentro de B+C sigue en cuarentena. Continúan pendientes los umbrales científicos, la admisión y el grant de entrenamiento. Los conjuntos protegidos siguen cerrados. DEMO está deshabilitado y LIVE_TRADING es false. Cero órdenes y cero entrenamientos.

[Mediciones, auditoría y hashes](../research/studies/bc_train_future_eval_v1/memory_stability_20261108/sha256.json).
