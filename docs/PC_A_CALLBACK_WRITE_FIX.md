# Corrección de escritura del observador prospectivo

La revisión encontró un archivo nativo real de 579 bytes con un SESSION_START y ningún heartbeat ni tick. La sesión permanece conservada, junto con su cadena y copia local. No se certifica como captura continua ni se fabrica continuidad.

La causa es un defecto del escritor v1: [FileWriteString](https://www.mql5.com/en/docs/files/filewritestring) añade CR ante un LF aislado en archivos TXT. El archivo observado termina en CRLF, pero el código comparaba bytes escritos con la longitud de una cadena que contenía solo LF. Por tanto cerró su handle después del primer registro correctamente escrito, sin avanzar su estado.

El observador v1.01 escribe CRLF explícito. El hash sigue cubriendo exactamente previous + LF + payload; el terminador exterior no forma parte del payload y los originales no se cambian. Se informa un error de escritura real con bytes esperados/observados y OnInit falla si no queda handle válido. La compilación del EA y del lanzador con el MetaEditor XM fijado tiene cero errores y cero advertencias. No se modifica FullClockAndTimeSemanticsProbe.

El lanzador v1.01 puede recargar mediante plantilla únicamente un gráfico que ya ejecute ProspectiveUtcObserver y tenga símbolo US30Cash; no sustituye EAs ajenos. Si no existe observador, conserva la ruta del gráfico dedicado. Exige Algo Trading desactivado, servidor/data folder/cuenta de datos fijados. Una plantilla encolada no prueba arranque: el monitor debe observar una nueva sesión, ticks y heartbeats.

El monitor ahora distingue ACTIVE_CALLBACKS_QUARANTINED de INACTIVE_CALLBACKS_RETAINED, STALLED_START_ONLY y PREPARED_NOT_OBSERVED. Una captura con ticks antiguos pero sin heartbeat reciente no se reporta activa. Las condiciones de certificación UTC y entrenamiento permanecen cerradas.

22 pruebas afectadas PASS, incluida conservación de hash/secuencia al leer CRLF y contabilidad correcta de bytes para el espejo append-only. La comprobación estática sin órdenes PASS. Los tests de software no sustituyen callbacks reales.

En el snapshot final aún hay una sola sesión estancada. La recompilación no recargó el EA que MT5 tenía en memoria. Se requiere ejecutar una sola vez Scripts → ResearchDiagnostics → PC_A → StartProspectiveUtcObserver, con Algo Trading y DLL desactivados; el lanzador recargará únicamente este observador. No existe una interfaz disponible para ejecutar automáticamente el script. Esta intervención se solicita después de verificar instalación y compilación. No se reinicia MT5 ni el otro proyecto.

Ecuador permanece como vista principal. CAUSAL_AUDIT=FAIL, UTC no certificado, segmentos QUARANTINED, TRAINING bloqueado, DISCOVERY_VALIDATION=BLOCKED, FINAL_TEST=LOCKED, DEMO=DISABLED, LIVE_TRADING=false.
