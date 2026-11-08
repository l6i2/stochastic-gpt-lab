# Recuperación histórica diagnóstica XM

El registro retrospectivo B usa outputs/xm_historical_recovery_v1. Lee índices verificados del productor C+F y consulta exclusivamente gaps posteriores al corte nativo 1793895900000, con cuenta demo, XMGlobalSC-MT5 5 y US30Cash no personalizado. El registro A conserva su productor, SQLite, checkpoints, epochs, contratos y admisión. Las consultas históricas no escriben en A.

La autorización técnica está vinculada al hash del texto del usuario y a la asignación exclusiva ya aprobada. Cada intervalo solicitado debe pertenecer íntegramente al inventario de interrupciones, quedar después del corte y terminar antes de la última cotización nativa observada. Los intervalos anteriores al corte y las intersecciones protegidas se rechazan antes de consultar datos. Los límites legacy desconocidos siguen desconocidos. La copia diagnóstica posterior al corte no cambia el propietario científico C+F.

## Detección y límites

El inventario deriva el último poll anterior y el primero posterior con timestamp nativo superior, desde el ledger verificado. Conserva la referencia a las interrupciones, distingue suspensión y desconexión XM cuando el clasificador existente tiene evidencia y mantiene UNKNOWN_GAP para causas no demostradas. Un reinicio de proceso no acredita por sí mismo apagado físico. La falta de ticks tampoco acredita cierre de mercado.

Los gaps se unen solo para evitar consultas retrospectivas duplicadas. Esa unión del inventario B no une epochs ni rachas de A. El recuperador incluye bordes de milisegundos y solo conserva M1/M5 completas dentro de cada request. Un gap sin límite nativo posterior queda pendiente hasta recibir una cotización nueva. Los registros pendientes no son necesariamente incidentes físicos distintos.

Las consultas se limitan a cinco minutos por tramo. El proceso programado atiende hasta seis por ejecución. Se verifica identidad antes de la descarga y durante las consultas, sin registrar login ni credenciales. Se exige espacio libre de 2 GiB y un límite de 16 MiB por array. La alternativa nativa se limita a un lanzamiento por ejecución y comparte el lock del terminal aislado con los oráculos existentes.

## APIs y timestamps

La ruta principal usa copy_rates_range y copy_ticks_range. Sus fechas de consulta se construyen en UTC como exige la interfaz Python, usando las coordenadas enteras nativas observadas. Esto no acredita que el timestamp de generación XM sea UTC. Se conserva el valor recibido y se valida que cada fila archivada pertenezca al intervalo nativo solicitado. [CopyRates en Python](https://www.mql5.com/en/docs/python_metatrader5/mt5copyratesrange_py) · [CopyTicks en Python](https://www.mql5.com/en/docs/python_metatrader5/mt5copyticksrange_py)

El wrapper probado perdió el último segundo cuando date_to llevaba milisegundos inmediatamente anteriores al extremo. La solución solicita el límite superior inclusivo y conserva únicamente start <= time_msc < end. Para bordes fraccionarios, la consulta utiliza segundos exteriores y registra las filas de borde descartadas. La comprobación de protección incluye ese sobre de consulta. No se desplazan timestamps ni se rellenan ticks.

La alternativa MQL5 usa CopyRates y CopyTicksRange en la instalación aislada existente, con órdenes, expertos y DLL deshabilitados. Una respuesta del tester o un símbolo personalizado se rechazan como fuente de ticks de mercado. El ensayo compiló con cero errores y advertencias, pero el terminal aislado estaba desconectado y devolvió 4403 en historial. No se presenta esa ruta como descarga válida. [Errores oficiales MQL5](https://www.mql5.com/en/docs/constants/errorswarnings/errorcodes)

El controlador histórico antiguo depende del split_manifest original que no está disponible. No se ejecutó Strategy Tester ni se abrieron sus conjuntos. El oráculo de indicadores utiliza una copia aislada de barras B en un símbolo diagnóstico, sin generar ticks de mercado ni enviar órdenes.

## Persistencia e integridad

Cada request tiene clave determinista. Cada intento escribe intención, payloads JSONL con fsync, hashes y un manifiesto inmutable. Los manifiestos forman una cadena separada. Si falla el checkpoint después de confirmar un manifiesto, el siguiente proceso reconstruye el sufijo huérfano. Un intento parcial se conserva y la recuperación usa otro directorio. Un error API puede reintentarse hasta tres veces con la misma evidencia de fuente, con separación operativa de quince minutos. Un boot distinto o una cotización nativa posterior permiten volver a intentarlo con evidencia nueva. Las descargas ya confirmadas conservan su clave y no se repiten por ese cambio. Los vacíos y las diferencias quedan registrados.

La repetición de un request confirmado verifica el payload y reutiliza el manifiesto. La auditoría explícita recorre todos los hashes. Se preservan ticks idénticos y timestamps repetidos que puedan proceder del broker. No se deduplican precios para forzar igualdad. Las versiones iniciales corregidas se conservan y no se cuentan dos veces en los totales vigentes.

## Uso diario

La tarea StochasticGPTLab_PC_A_XMHistoricalDiagnostics_v1 se ejecuta al iniciar sesión y cada cinco minutos, con IgnoreNew y lock propio. Guardian, NTS y C+F conservan sus tareas. La recuperación se pospone si XM no está conectado o su identidad es insegura. No requiere el chat y no cambia energía global ni reinicia Windows.

Desde la raíz se puede ejecutar .venv/Scripts/python.exe tools/xm_historical_recovery.py --budget 6. Para verificar el archivo local sin consultar MT5, usar --audit. La tarea puede retirarse con Unregister-ScheduledTask -TaskName 'StochasticGPTLab_PC_A_XMHistoricalDiagnostics_v1' -Confirm:$false.

La presentación de recepción usa el módulo horario existente, con Ecuador prioritario y Nueva York con DST. El tiempo XM y el mapping UTC de eventos mantienen sus estados de evidencia. El registro B queda diagnóstico, expuesto y sin admisión científica. Los raw permanecen locales; GitHub publica código, hashes y recibos de tamaño acotado.
