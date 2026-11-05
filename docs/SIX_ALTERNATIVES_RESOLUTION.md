# Resolución de las seis alternativas

Corte del 5 de noviembre de 2026, 07:27 Ecuador. Las seis rutas se ejecutaron
hasta el alcance autorizado. La matriz completa contiene IMPLEMENTED,
TESTED_WITH_REAL_DATA, VALID_M5, COVERAGE_PROVEN, INDEPENDENCE_PROVEN,
CAUSALITY_PROVEN, SCIENTIFICALLY_ADMISSIBLE, REMAINING_BLOCKER y RECOMMENDED.

[Matriz verificable](../research/studies/six_alternatives_resolution/comparison_matrix.json)

| Alternativa | Ensayo | Resultado medido | Admisión pendiente |
|---|---|---|---|
| A. Historial MT5 | Extracción aislada de exportaciones autorizadas y consultas API actuales | 79.211 cotizaciones, 1.376 M1 y 276 M5. Muestra API de 223 ticks en intervalo verificado. CopyRates devolvió datos fuera del rango solicitado y se rechazaron. | Histórico expuesto y membership protegido desconocido. |
| B. M1→M5 | Agregación cronológica contrastada con M5 nativa y cinta de ticks | OHLC y volumen coinciden en 276 grupos. 272 tienen sus cinco M1 y cuatro conservan minutos ausentes. La cinta difiere en volumen de diez M5. | Cobertura y fuente independiente por demostrar. |
| C. Productor experimental | Nueva identidad, rutas, manifest y cadena con el colector de base nativa existente | Dos M5 consecutivas y 14 M1 verificadas, cero rechazadas. Dos procesos reabrieron la base con idénticos contador, estado y hash. | Método de observaciones de base y asignación futura de roles requieren aprobación. |
| D. Tiempo | Cadena NTS, correlaciones y calendario nativo previamente capturado | 374 recibos de cadena íntegros. Última medición autenticada con cotas condicionales. Sesión observada de 23 horas, hasta 276 M5. | Generación UTC del broker, deriva/cuantización y vigencia/excepciones de calendario. |
| E. Independencia | Búsqueda de metadatos GitHub, historial de rutas exactas y ensayo de frontera futura | Cero manifiestos originales recuperados. La función contractual bloqueó la frontera por ledger incompleto y dominios/intervalos desconocidos. | Fuentes originales o decisión científica expresa sobre roles futuros. |
| F. Estudio nuevo | Paquete propuesto separado, hashes y pruebas sintéticas de dependencias y folds | 800 IDs sintéticos, cuatro folds purgados, rechazo de feature futura y de ejecución sin grant. | Aprobación del método, nueva captura y dataset suficiente admitido. |

Los resultados de A y B provienen exclusivamente del día diagnóstico autorizado
2024-01-02. La extracción usa bloques de 64 KiB, conserva los siete hashes de
origen y recibe un ID propio. La primera consulta experimental de ticks excluía
parte del último segundo. Se corrigió para consultar el límite entero y aplicar
un intervalo nativo semiabierto. La muestra corregida contiene 223 ticks.
El origen sigue siendo histórico previamente expuesto. Las cuatro M1 ausentes
se conservan como huecos y las diferencias de volumen permanecen registradas.

El nuevo productor C es `dbsnap_f96ae9399e304c738ccffd0592aaf581`. Reutiliza
`tools/native_database_snapshots.py` dentro de un proceso y raíz propios, con
fuentes fijadas por hashes. Registra primera observación, contador monotónico,
recepción Windows, identidad XM, símbolo, BID/ASK, flags, epoch y dos consultas
por intervalo. Los ticks recuperados se etiquetan como consultas a base nativa.
Las observaciones de consulta se persisten con transacciones y checkpoints.
En la muestra de recursos usó 13,84 MiB residentes, 252,05 MiB privados y
2,75 segundos de CPU acumulados. El ensayo tenía un máximo de 20 minutos y
terminó automáticamente tras las dos M5 verificadas. Sus datos permanecen en
cuarentena. El productor original conserva su identidad y sus restricciones.

[Captura y persistencia de C](../research/studies/six_alternatives_resolution/C_capture.json)

La documentación oficial explica que NewTick se coalesce cuando ya existe un
evento pendiente o en ejecución. CopyTicks puede sincronizar ticks ausentes
desde el servidor. Por ello las observaciones de la base y las recepciones
originales tienen garantías distintas. TimeCurrent usa tiempo de cotizaciones
del servidor. TimeTradeServer se calcula en el terminal y TimeGMT depende del
reloj local. Los recibos NTS aportan autenticación y cotas de recepción bajo sus
condiciones. La deriva, cuantización y demora de generación siguen sin cota
demostrada. Las vistas Ecuador/Nueva York se conservan para tiempos que dispongan
de semántica demostrada.

[OnTick](https://www.mql5.com/en/docs/event_handlers/ontick),
[CopyTicks](https://www.mql5.com/en/docs/series/copyticks),
[TimeCurrent](https://www.mql5.com/en/docs/dateandtime/timecurrent),
[TimeTradeServer](https://www.mql5.com/en/docs/dateandtime/timetradeserver),
[TimeGMT](https://www.mql5.com/en/docs/dateandtime/timegmt).

La evidencia del mismo servidor XMGlobalSC-MT5 5, observada el 28 de octubre,
indica cotización 00:00–23:00. Ese horario admite 276 M5 por sesión, inferior
a 350. Si se mantiene el reset obligatorio entre sesiones de esa duración,
el warmup no puede completarse en una sesión. Su vigencia posterior y las
excepciones requieren verificación antes de aplicar una continuidad entre
sesiones. La propuesta F mantiene 350/800/100/200/80/80 y solicita una definición
de continuidad respaldada por calendario y evidencia de supervisión.

La búsqueda E devolvió cero coincidencias en la consulta conectada de la rama
por defecto, cero workflows PR en la página del HEAD consultado y ningún commit
con las tres rutas exactas de manifiestos. La rama main conserva la referencia
del análisis previo. Los tres originales se clasifican UNKNOWN porque la PC
anterior o su respaldo podrían conservarlos. El membership derivado nuevo tiene
identidad propia. Una fecha UTC futura carece de prueba de no solapamiento
cuando los límites protegidos y el dominio nativo son desconocidos.

F propone `US30CASH_M5_NATIVE_OBSERVATIONS_20261105_PROPOSED`, con dataset y
productor futuros reservados, primera observación pendiente y hash de dataset
nulo. Conserva Stochastic 5/3/3, MAIN_K 20/80, BUY/SELL, FOLLOW/INVERT,
TP240/SL180/TIME_EXIT100 y la whitelist de seis features. Planifica logística L2,
cuatro folds cronológicos con purga y hasta ocho ajustes, con cero autorizados.
El validador comprueba hashes, umbrales y estrategia, y rechaza alteraciones
aunque se recalcule el índice del paquete. Las pruebas usaron metadatos
sintéticos. La autorización científica debe integrar el contrato aprobado
antes de que el ejecutor vigente acepte un grant de ese estudio.

[Propuesta completa y criterios](../research/studies/six_alternatives_resolution/proposed_study/PROPOSAL_ES.md)

La mejor ruta técnica es C por su paridad nativa observada, persistencia exacta,
procedencia explícita y coste medido. F proporciona la vía científica propuesta.
La elección usa esos criterios operativos y metodológicos. Las métricas
financieras históricas quedan fuera de la selección.

El productor original registró 147.003 callbacks, 557 M1 y 30 M5 acumuladas,
con 179 M5 rechazadas. Su racha técnica era cero y su máximo observado cuatro.
El warmup científico es 0/350, señales consecutivas 0/800, barras posteriores
0/100, evaluables 0/200 y soporte BUY/SELL 0/80 por lado. Las señales históricas
diagnósticas siguen siendo 13 BUY y 15 SELL. El ensayo C aporta cero barras al
warmup científico original. El ledger global conserva CAUSAL_AUDIT en FAIL y
TRAINING_ADMISSION_GATE en WAITING_FOR_DATA. Se mantienen cero datasets admitidos
y cero entrenamientos ejecutados.

La captura habitual, el worker, NTS y el guardian siguen supervisados por las
tareas existentes. C terminó de manera controlada y conserva su base para
reproducción. Las siguientes acciones automáticas son captura y procesamiento
en cuarentena. Para admitir un dataset faltan cobertura y semillas propias,
membership independiente y autorización del contrato aplicable. La asignación
de roles futuros y la metodología de base nativa requieren una decisión
científica específica. Se conserva la propuesta sellada para esa revisión.

Se completaron 25 pruebas sintéticas y de regresión, más la extracción histórica,
el contraste de las tres fuentes y la persistencia con datos reales de C.

Comandos de reproducción desde la raíz del repositorio:

```powershell
.venv\Scripts\python.exe tools/six_routes_experiments.py --out outputs/six_routes_reproduction_new
.venv\Scripts\python.exe tools/audit_native_database_trial.py --base outputs/six_alternatives_experiment --out outputs/six_routes_c_reproduction_new
.venv\Scripts\python.exe tools/prepare_six_routes_study.py --verify
.\tools\research_control.ps1 STATUS
```

Las rutas nuevas de salida preservan los recibos anteriores. Los datos grandes
permanecen en la PC y sus hashes se publican. Los contratos congelados y las
reservas protegidas conservan sus restricciones. DISCOVERY_VALIDATION=BLOCKED,
HISTORICAL_HOLDOUT=LOCKED, FINAL_TEST=LOCKED, DEMO=DISABLED, LIVE_TRADING=false.
