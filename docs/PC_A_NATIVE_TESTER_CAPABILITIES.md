# MT5 nativo: diagnóstico causal y revisión de requisitos

Estado: diagnóstico técnico reproducible; ninguna admisión científica ni cambio de gobernanza. Reportes actuales se presentan en America/Guayaquil. El intervalo histórico indicado abajo conserva explícitamente el calendario nativo del servidor; no se transforma en UTC/Ecuador sin mapping verificado.

## Qué exigían los contratos

`docs/RESEARCH_PROTOCOL.md` nació con la investigación histórica en el commit 3844d04 (2026-10-10). Exige congelar proveedor/configuración/calendario, validar datos, orden de señales, purga, features causales y separación de particiones. No exige una referencia física UTC independiente por tick. El protocolo intra-trade exige features y mark time anteriores al cutoff y ejecución por secuencia de quotes posterior a la llegada, con TP/SL/TIME_EXIT congelados. `RESEARCH_PROTOCOL_V2.md` conserva esas reglas y limita el presupuesto de hipótesis; tampoco exige una certificación física individual de cada generación de tick.

El contrato posterior `configs/timestamp_clock_contract_v1.json`, introducido en 9068af5 (2026-10-23), sí fija autoridad de decisión UTC independiente, rechaza mapping desconocido y preserva todos los estados protegidos. **También declara expresamente** `replay_domain = frozen native event timestamps and sequence; no current wall-clock conversion`. Es coherente mantener cerrado el runtime UTC y permitir un diagnóstico de replay en ese dominio nativo. El documento posterior `PC_A_TIME_PROVENANCE_REQUIREMENTS.md` pide un mismo evento independiente para autorizar un mapping UTC: ese requisito no debe confundirse con un requisito original de todo backtest.

Conclusión de revisión: imponer certificación UTC física de cada tick como prerrequisito universal de un diagnóstico histórico nativo es una sobreextensión. Esto no demuestra que el servidor codifique UTC ni elimina el contrato UTC vigente. La conclusión queda como propuesta de aclaración de alcance, sin activar admisión, cohortes, entrenamiento ni ejecución.

Los protocolos prospectivos congelados sí requieren semanas/días UTC, calendario XM independiente y madurez. Su evaluación precisa candidato congelado y autorización explícita de un uso. Un tester exitoso no sustituye ninguna de esas condiciones. TRAIN agotado, ausencia de candidato y disponibilidad/membresía de datasets congelados son bloqueos distintos. En esta PC falta el split_manifest original en su ruta estándar: no se fabricó uno ni se hizo que el controlador general continuara sin él.

## Automatización y aislamiento

[MetaQuotes soporta `/config` y `[Tester]`](https://www.metatrader5.com/en/terminal/help/start_advanced/start). El controlador nuevo reutiliza presets, fechas exclusivas, hashes y recolección del controlador existente. Solo permite el smoke fijo **2024-01-02 servidor XM**, dentro del TRAIN histórico documentado; esta autorización técnica no permite seleccionar modelos ni readmitir datos a TRAIN. Usa Model=4, M5, Optimization=0, ForwardMode=0, UseRemote=0, UseCloud=0, Visual=0 y desactivación de trading/DLL. No hay opción de fecha arbitraria, optimización o acceso a holdouts.

El cold-start anterior exige cerrar el terminal. Para mantener activo el collector se usa una copia portable aislada de los mismos binarios XM bajo `outputs/pc_a_certification/native_tester/terminal`, con hashes comparados. Los caches locales necesarios, incluido el cache cifrado de la cuenta existente, permanecen privados dentro de outputs ignorados por Git. No se serializan ni publican contraseñas/cookies/tokens ni se accede al otro proyecto. Solo se copió inicialmente historia 2023/2024 y ticks enero 2024 para el símbolo. La descarga y sincronización de historia del tester fueron automáticas. El terminal original no se cerró ni reinició; los dos procesos quedan diferenciados por ruta.

El exportador `StochasticBarDecisionResearchEA.mq5` no se cambia: solo simula posiciones virtuales y rechaza ejecución fuera del tester, optimización y LIVE_TRADING. El envoltorio `NativeTesterDiagnosticEA.mq5` incluye ese archivo y llama sus eventos congelados; añade observación de MAIN_K y exportación de CopyRates M1/M5 dentro del tester. No llama APIs de órdenes, no hace CopyTicks histórico ni modifica reglas o relojes. La compilación dio cero errores y cero warnings. Los ocho outputs originales resultaron idénticos con y sin envoltorio.

Comando completo, únicamente cuando se solicita otro diagnóstico técnico:

```powershell
.venv\Scripts\python.exe -m controller.native_diagnostic
```

`--resume` continúa un checkpoint sin reiniciar un run concluido. El controlador no se programa para repetir el mismo smoke continuamente. Timeout deja el proceso diagnosticado identificado y no termina terminales ajenos. Cada nuevo run usa nonce y archivos exclusivos. Los logs se leen desde offsets previos, solo en carpetas de terminal/tester/agent/MQL5; no se recorren caches de navegador. Los outputs copiados se verifican por hash y no desaparecen cuando el agente limpia su sandbox entre ejecuciones. Los datasets diagnósticos están bajo `pc_a_certification`, que TRAIN ya rechaza antes de I/O.

## Evidencia real y alcance

Se realizaron dos ejecuciones del exportador original y dos del envoltorio para añadir M1 independiente. Todas usaron el mismo día y parámetros, sin búsqueda de rentabilidad. Cada pareja reprodujo byte por byte los ocho archivos de investigación. Las diferencias de tiempo de ejecución y metadatos del HTML no se presentan como determinismo binario de los reportes.

- 79.211 ticks y 276 barras M5 por ejecución; los reportes MT5 indican **100% real ticks** para este intervalo.
- 79.211 quotes del tester coinciden exactamente en secuencia, timestamp nativo, Bid y Ask con el archivo histórico preservado. El tape no contiene flags; estos se conservan en el original y no se inventan.
- CopyRates dentro del tester devuelve 1.376 M1 y 276 M5. Todas coinciden exactamente en OHLC BID con la agregación del tape. El volumen coincide con las actualizaciones BID de flags originales en ambos marcos. No se agregan los minutos sin quotes ni se certifica su causa con un calendario histórico inexistente.
- MAIN_K coincide con el oráculo Python nativo en 268 cierres completos comparables y 27 señales con prehistoria suficiente dentro del día. Se conserva una señal temprana, cuyo K previo necesita prehistoria anterior al día; no se elimina del dataset ni se declara esa comparación probada. Error máximo observado 1,42e-14, bajo la cota numérica 1e-10 ya aprobada por el oráculo existente, sin tolerancia nueva.
- Python reproduce 56 trayectorias FOLLOW/INVERT: 14 TIME_EXIT, 15 SL, 9 TP y 18 END_OF_DATA censuradas. La validación cubre entrada en la vela siguiente, precio Ask/Bid según lado, primer quote posterior a decisión/llegada y precedencias congeladas. No se publican resultados de rentabilidad ni se selecciona una regla.
- Se validan 3.279 snapshots y quotes de llegada con cutoff de features, separación de targets, MFE/MAE pasado, HA/perfil de barras cerradas, parámetros y asignación FOLLOW/INVERT. Esa disponibilidad es de simulación nativa, no una prueba de la hora física ni de que el proveedor histórico no haya revisado datos después.
- El tester registró 72–74 MB de memoria. El agente local único se mantiene sin cloud ni optimización. Un aviso no fatal de puerto MCP ocupado aparece al coexistir los terminales; no impidió los tests ni se detuvo el listener existente.

Una consulta externa M1 por API devolvió una fila fuera del intervalo solicitado. Se retuvo el resultado rechazado sin modificar su timestamp. La causa interna exacta no está demostrada; no se atribuye automáticamente a DST o al límite de barras. El controlador ahora rechaza una respuesta fuera de rango antes de aceptarla. La exportación M1 desde el tester resuelve la verificación técnica sin convertir aquel resultado erróneo en evidencia válida.

En TICK_QUOTES la resolución dentro de una misma barra sigue la secuencia observada: el primer quote que alcanza un nivel decide. La alternativa de barras del core conserva apertura/gap primero y SL antes de TP si ambos extremos son ambiguos. No se sustituye la secuencia real por esa convención ni se altera `ResearchCore.mqh`; sus fixtures ya existentes cubren igualdad, gaps y precedencias. La paridad del smoke no se presenta como cobertura de todos los posibles escenarios de mercado.

NATIVE_BACKTEST_PARITY compara el exportador virtual MQL5 nativo con el replay Python sobre los quotes del tester. No se utilizó el motor de órdenes del tester: los trades son registros virtuales propios del exportador y no operaciones en una cuenta. No se certifican fills del broker, slippage real ni equivalencia con un EA que envíe órdenes MT5.

## Ticks reales y posibles sustituciones

[MetaQuotes documenta](https://www.metatrader5.com/en/terminal/help/algotrading/tick_generation) que puede generar ticks cuando hay barras M1 sin ticks, y que puede ignorar ticks donde no hay barra M1. En modos generados se usa información M1 y el spread no reproduce necesariamente las variaciones reales. [El libro oficial](https://www.mql5.com/en/book/automation/tester/tester_ticks) describe la validación/corrección de historia del tester. Por eso Model=4 y ConfirmRealTickTesterMode=true son configuración, no pruebas suficientes de cobertura real.

En el smoke se combinan reporte 100% real ticks, ausencia de advertencias de sustitución para el intervalo y equivalencia exacta del tape con el archivo original. La exposición detectada a ticks generados es cero en ese día; no se generaliza a otros años. El freeze histórico documenta minutos problemáticos de 2023 y 2024; permanecen pendientes de sus filtros y manifests originales. La línea normal «ticks, bars generated» de MT5 no significa por sí sola que los ticks fueran sintetizados. Se requieren advertencias explícitas, calidad reportada y comparación de datos.

## Puertas independientes, sin modificar las vigentes

| Capacidad | Resultado técnico del smoke | Límite |
|---|---|---|
| A MT5_TESTER_REPRODUCIBILITY | PASS | Día, binario y configuración congelados; no rentabilidad ni admisión. |
| B HISTORICAL_DATA_INTEGRITY | PASS_THIS_INTERVAL | Equivalencia exacta de quotes, OHLC y volumen; no toda la historia ni membresía científica. |
| C CAUSAL_FEATURE_AVAILABILITY | PASS_NATIVE_SIMULATION | Cutoffs y replay nativos; no certifica UTC/NY, vintage histórico o disponibilidad física real. |
| D NATIVE_TIMESTAMP_SEMANTICS | PARTIAL | Unidades, orden y dominio nativo demostrados; mapping histórico UTC sin aprobar. |
| E EXTERNAL_UTC_EVENT_CERTIFICATION | BLOCKED | El tester simula tiempo, no aporta evidencia externa del mismo evento. |
| F BROKER_CALENDAR_CERTIFICATION | PARTIAL | Sesiones semanales nativas retenidas; faltan excepciones históricas fechadas. |

[Durante los tests, TimeLocal/TimeTradeServer/TimeGMT se simulan](https://www.metatrader5.com/en/terminal/help/algotrading/test_preparation); no se usan como reloj externo independiente. Los campos UTC_time, NY_time y sesión del exportador siguen usando sus parámetros congelados de offset/DST: se conservan como outputs de esa configuración, sin declararlos certificados para XM. C PASS no es Causal Audit global PASS: el guard operativo y la admisión científica permanecen FAIL/BLOCKED.

## Propuesta pendiente: no aplicada

1. Aclarar que A/B/C pueden evaluarse en el dominio nativo con identidad/versionado y secuencia, sin exigir E como prerrequisito de todo diagnóstico. Mantener E para afirmaciones UTC/ejecución y F para claims de sesiones/madurez.
2. Para una eventual admisión histórica, revisar membresía, calidad por minuto, versión de feed y whitelist. Excluir o demostrar por separado features UTC/NY/sesión y cualquier dependencia de calendario no certificada. No desplazar timestamps originales ni alterar datasets congelados.
3. Conservar los protocolos prospectivos UTC existentes y la cuarentena; ninguna descarga histórica cuenta como captura nueva. No activar nueva cohorte ni cambiar sus reglas automáticamente.
4. No reabrir el TRAIN agotado. Cualquier nueva búsqueda o entrenamiento fuera del presupuesto vigente requiere una decisión científica explícita y un protocolo nuevo o autorización versionada; el éxito técnico no la otorga.

El smoke usa el servidor actual XMGlobalSC-MT5 5. Que reproduzca el archivo nativo recuperado de ese servidor no demuestra equivalencia con el proveedor/servidor y todos los bloques del master legado. También faltan en PC A los archivos de membresía/splits en sus rutas originales. Una decisión de admisión necesitará esos hashes y fuentes o una cohorte nueva autorizada; este diagnóstico no los reemplaza.

**SCIENTIFIC_CONTRACT_CHANGE_REQUIRED=YES para habilitar una ruta científica nueva; NO para este diagnóstico ya autorizado.** No se ha aplicado la propuesta ni modificado contratos/sidecars congelados. No hace falta acción manual para ejecutar el controlador. DISCOVERY_VALIDATION=BLOCKED, FINAL_TEST=LOCKED, DEMO=DISABLED, LIVE_TRADING=false; TRAINING_READINESS=BLOCKED.
