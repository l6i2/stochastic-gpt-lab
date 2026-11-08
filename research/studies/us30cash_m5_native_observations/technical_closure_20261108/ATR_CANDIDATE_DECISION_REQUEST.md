# Decisión pendiente sobre la versión de ATR

Estado PREPARED_INACTIVE. Esta propuesta no solicita ni habilita entrenamiento.

La implementación de referencia queda identificada por controller/cf_atr_candidate.py y SHA-256 9bc2efb0e3a2d1af750d4c47ce38fb8ca2b245639856c63ba210a82d23c70dfc. Su esquema de estado es cf-native-atr14-candidate/1.

La decisión propuesta consiste en autorizar una versión nueva y explícita del cálculo de ATR nativo, después de revisar el ensayo real de 30 M5 propias. Usaría high-low de la primera barra, semilla ordenada de 14 rangos y recurrencia binary64 value + (TR_actual-TR_saliente)/14. El estado diagnóstico tiene valor desde la barra 14. Una eventual integración debe resolver explícitamente la frontera de disponibilidad de la implementación vigente, que mantiene ATR inicializado desde la barra 15.

La versión afecta los valores de ATR y range_to_ATR. Su integración exige revisar el pin del fragmento features, emitir un certificado nativo nuevo ligado a las semillas propias y establecer una identidad de contexto e implementación distinta. Los estados previos no se reinterpretan como estados de este esquema. El código de producción y el certificado retenido siguen vigentes para sus propias evidencias.

Evidencia completada. El candidato reproduce 287 valores nativos sintéticos con restauración antes de cada barra y cinco valores únicos de dos epochs reales. Las pruebas de mutación futura y corrupción de checkpoint pasan. Falta el prefijo propio real de 30 barras y siguen pendientes las semillas y comprobaciones del contexto científico completo.

La solicitud final de integración podrá prepararse sobre esos resultados y hashes. La admisión del dataset y el grant de entrenamiento son decisiones posteriores.

El calendario ya permite un bridge bajo sus requisitos vigentes. Ese permiso requiere evidencia. No se propone reducir 350, modificar la selección de las primeras 800 señales ni sustituir una excepción fechada por una ausencia de cotizaciones. Una modificación de esos requisitos necesitaría otra enmienda científica explícita.
