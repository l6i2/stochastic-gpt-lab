# Max bars, historia XM y replay fijo — PC A

Corte: 2 noviembre2026,16:45:56 Ecuador. El valor real de la instancia XM pasó de
**500.000 a20.000**, confirmado tanto por la GUI como por `terminal_info().maxbars`,
equivalente al [TERMINAL_MAXBARS oficial](https://www.mql5.com/en/docs/constants/environment_state/terminalstatus).
No fue necesario reiniciar: PID23100 conservado. Solo se cambió Charts/MaxBars.

## Memoria y elección

PC:7.927MiB físicos;1.247MiB disponibles inicialmente (84,3% usados),1.075MiB al
corte final. Se evaluaron10.000 y20.000: dos arrays MqlRates64bytes de esos tamaños
representan aproximadamente1,22MiB/2,44MiB, sin contar índices, otros símbolos,
indicadores o terminal. Se eligió20.000 como límite inicial, muy inferior a500.000.
No es un límite universal de RAM ni se atribuyen las variaciones globales de memoria
a este cambio. Working set XM60,14→11,70MiB, susceptible de trimming de Windows.
El tester aislado notificó93MiB, incluidos24MiB de historia y64MiB de ticks.

## Profundidad anunciada y barras accesibles

Un script MQL5 read-only compilado con0errores/0warnings se ejecutó únicamente en el
terminal portátil diagnóstico existente, con el mismo límite20.000; no se instaló
otro EA en XM activo. Consultó Bars/SeriesInfoInteger y solo pidió contenido del día
expresamente permitido2024-01-02. Los contadores aislados fueron **20.000M1 y20.316M5**.
No se afirma que las cachés de ambas instancias sean idénticas ni se fuerza/trunca el
exceso de316barras. Estos son contadores nativos, no una lectura de conjuntos bloqueados.

La metadata del servidor anuncia inicio **2011-08-10**; la base local, **2022-06-03**.
Primera barra de las series consultadas: M1 **2026-10-13 12:19**, M5 **2026-07-22 05:35**.
Son etiquetas nativas originales, no UTC certificado. No prueban continuidad ni que
toda esa profundidad siga descargable. Según [MetaQuotes](https://www.mql5.com/en/docs/python_metatrader5/mt5copyratesfrompos_py),
las barras proporcionadas a Python dependen de la historia disponible en gráficos y
de Max bars. El límite local no define la retención total del broker.

CopyRates nativo para enero2024, fuera de la ventana de gráfico20k, devolvió4401.
La consulta directa Python del día permitido produjo timestamps fuera del rango:
se rechazó antes de persistir o utilizar las barras. No se corrigieron fechas ni se
aceptó otra ventana. No se descargaron indiscriminadamente años que puedan solapar
Discovery Validation/Holdout/Final Test. El controlador solo permite este smoke fijo;
ampliar el periodo necesita alcance diagnóstico científicamente aprobado.

## Descarga y reproducción realizadas

El Strategy Tester aislado, mediante el controlador aprobado, recuperó para el día
2024-01-02 **79.211ticks,1.376M1 y276M5**. Run `diag_d17cbe6aedfc`, sin optimización,
cloud, órdenes o entrenamiento. Su historia precargada2023 es el contexto del replay
técnico ya autorizado; no se convierte en un conjunto nuevo ni en warmup prospectivo.
Max bars del gráfico no impide el mecanismo de historia del tester ni limita toda
su RAM: por eso se midió su consumo separado.

Datos copiados con manifest/hashes propios bajo `outputs/historical_downloads_v1/diag_d17cbe6aedfc/`.
Nada de esta ruta alimenta las capturas prospectivas. Los originales y manifiestos
anteriores permanecen intactos. Una nueva descarga del mismo día sigue siendo dato
previamente expuesto, no independencia científica.

Comparación fresca MT5/Python:

- OHLC exacto:1.376/1.376M1 y276/276M5; volumen BID sin discrepancias en este replay.
- MAIN_K5/3/3:268barras comparadas; error máximo1,421e-14 dentro del bound heredado1e-10,
  sin tolerancias nuevas.27señales comparadas y1fila temprana excluida por seed corto.
-28señales totales:13BUY/15SELL;56caminos FOLLOW/INVERT. Replay PASS,18censurados.
- Los ocho outputs principales fueron idénticos byte a byte al run nativo aprobado.
- Paridad del **exportador virtual congelado frente a Python**, no prueba del motor
  de fills de órdenes, rentabilidad futura o certificación UTC externa.

7tests de restricciones del diagnóstico PASS; script nativo compilado/ejecutado y
backtest real local completados. Fuente MQL5, metadata, hashes y replay publicados;
arrays crudos, caché de cuenta, binarios grandes e informes con datos privados no.

## Captura y gobernanza

La GUI/log mostró que el observador anterior había sido retirado antes de cambiar
Max bars. Se recuperó ejecutando su lanzador preexistente y aprobado, con Algo Trading
deshabilitado. Nuevo segmento automático, mismo captureID/cursores históricos
preservados, sin backfill de la interrupción. Collector ACTIVE_QUARANTINED al corte.

Warmup prospectivo original **0/350**; científicamente admitido0 e históricos
importados0. Los contadores del productor alternativo de snapshots siguen separados.
TRAINING_READINESS=BLOCKED: cobertura, seeds propios, membresía, causalidad, madurez,
dataset admitido y grant específico pendientes. CAUSAL_AUDIT global no se elevó aPASS.

DISCOVERY_VALIDATION=BLOCKED; HISTORICAL_HOLDOUT/FINAL_TEST=LOCKED;
DEMO=DISABLED; LIVE_TRADING=false. Estrategia/contratos intactos; otro proyecto sin
modificaciones. No hay acción manual necesaria ahora. Para restaurar el límite de
capacidad anterior: Opciones→Gráficos→Max bars500000; no se revierte automáticamente.
