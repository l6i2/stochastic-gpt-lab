# Recuperación automática de PC A

PC A puede apagarse normalmente. Al iniciar sesión, la tarea `StochasticGPTLab_PC_A_RecoveryGuardian_v1` ejecuta el guardian con el usuario interactivo y privilegios limitados. La instalación verificada permite arrancar en batería, ignora instancias duplicadas y también conserva su disparador periódico. El usuario inicia sesión como de costumbre. La adquisición solo cubre intervalos observados y verificados.

El instalador del repositorio reutiliza la tarea si su acción pertenece a este workspace. Si falta, registra la tarea con disparador de inicio de sesión. El mutex del guardian y el bloqueo del escritor impiden propietarios simultáneos. La configuración de energía de Windows queda bajo control del usuario.

## Arranque y recuperación

El guardian identifica la instalación XM por la ruta exacta. Cuando falta el terminal y está cerrado el ingreso legado, comprueba primero el manifest, el pin de implementación, la asignación exclusiva, el contrato y el checkpoint de C+F. La apertura exige además el perfil autorizado y el hash del observador instalado. El archivo de inicio usa `Enabled=0`, `AllowLiveTrading=0` y `AllowDllImport=0`. El productor verifica por IPC cuenta demo, servidor, símbolo, conexión y `terminal_trade_allowed=false` antes de adquirir. La semántica de los parámetros de inicio está documentada por MetaQuotes. [Inicio de la plataforma](https://www.metatrader5.com/en/terminal/help/start_advanced/start)

La instalación anterior usaba `Enabled=1`. Durante la inspección se observó `trade_allowed=true` y el productor rechazó la adquisición. Se deshabilitó Algo Trading en la instancia XM y se comprobó por IPC el estado resultante. El siguiente arranque automático de XM con el archivo corregido queda por observar en un inicio normal. La prueba real de esta intervención reinició el productor y el monitor, con XM abierto.

El guardian recupera el productor, el monitor de calidad y madurez y el ciclo NTS existentes. El productor reintenta las interrupciones con espera creciente hasta 30 segundos. Un fallo de persistencia o de publicación termina el proceso para que el siguiente propietario lea el checkpoint comprometido. Así se evita volver a insertar el lote si SQLite ya lo había confirmado. Una excepción durante una iteración del guardian se registra y deja que la supervisión vuelva a intentar en su intervalo normal.

## Checkpoints y evidencia

La cadena y el estado se confirman juntos en SQLite WAL con `synchronous=FULL`. Al apagar, la unidad recuperable es el último commit completo. El siguiente arranque verifica la cadena y deja que SQLite descarte una transacción incompleta. La publicación del estado usa reemplazo atómico. Una interrupción entre la observación y el commit se trata como cobertura incierta.

El recibo local `outputs/us30cash_m5_native_observations/recovery/latest.json` incluye el hash del checkpoint, el epoch, la última observación, los últimos intervalos verificados, cursores, semillas, madurez y admisión. Vincula el manifest, los roles y el pin de código. El arranque comprueba el prefijo guardado y verifica el nuevo sufijo en una sola lectura de SQLite. Los recibos de transición se guardan por índice y hash sin reemplazar los anteriores. El directorio de recibos del colector legado se conserva aparte.

`TOTAL_VERIFIED_M5` cuenta barras con paridad M1/M5 en la cadena. `CURRENT_CONSECUTIVE_M5` mide el contexto propio vigente. `SCIENTIFICALLY_ELIGIBLE_M5` permanece en cero mientras la admisión esté pendiente. El estado autoritativo expone los tres valores por separado.

## Clasificación y continuidad

La evidencia de suspensión positiva se clasifica como `SLEEP`. Una desconexión explícita del terminal se clasifica como `XM_DISCONNECT`. `WINDOWS_RESTART` y `NORMAL_SHUTDOWN` requieren cambio de boot, intención del registro de Windows y cierre de sistema correlacionado. Un Kernel-Power 41 registra un arranque tras un cierre irregular y se conserva como `UNKNOWN_INTERRUPTION` en ausencia de prueba de pérdida de energía. Lo mismo se aplica a un posible `NETWORK_DISCONNECT` sin evidencia de la red aplicable. La duración dentro del mismo boot usa reloj monotónico. Entre boots se conserva la diferencia de las etiquetas de reloj del host con su alcance explícito.

`MARKET_CLOSED` requiere una transición aceptada por el verificador C+F. El calendario semanal sigue siendo parcial y ninguna transición real está certificada. El puente actual exige observación conectada y continua. Un apagado durante un cierre demostrado tampoco satisface por sí mismo esa condición. La recuperación conserva el prefijo, excluye el intervalo sin cobertura y abre un epoch cuando corresponde. Las semillas del epoch anterior quedan en la evidencia y solo el contexto propio vigente alimenta el warmup.

## Pruebas y uso diario

El ensayo controlado conservó los 6.230 registros comprometidos y las 18 M5 verificadas. El guardian levantó otro proceso de productor, se observó un nuevo epoch y la cadena siguió creciendo con el mismo boot de Windows. También recuperó el monitor de calidad tras finalizar su proceso. Las pruebas simularon desconexión, cierre probado, hueco desconocido, bloqueo duplicado, checkpoint incompleto y salida abrupta durante una transacción. Pasaron 53 pruebas Python y el ensayo seco del guardian. Los recibos públicos están en `research/studies/us30cash_m5_native_observations/automatic_recovery_20261105/`.

La recuperación tras un apagado físico de Windows queda pendiente del próximo inicio natural. El usuario puede apagar y encender la PC normalmente. El guard deja en cuarentena cualquier intervalo sin observación y el reinicio diario no requiere ejecutar scripts. Discovery Validation, Historical Holdout y Final Test están cerrados. DEMO está deshabilitado, `LIVE_TRADING=false`, `TRAINING_EXECUTED=false` y `PROTECTED_SCORING=false`.
