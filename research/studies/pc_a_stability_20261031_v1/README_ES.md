# Estabilización PC A — 31 octubre 2026

Se conservaron los valores originales del plan Equilibrado. En corriente: suspensión por inactividad 300 → 0 segundos (nunca); cierre de tapa suspender → no hacer nada; hibernación automática permanece en 0. En batería: suspensión 180 segundos, tapa suspender e hibernación 2147483647 sin cambios. No se alteraron pantalla, batería crítica, botón de encendido ni otros planes. Es una política de Windows compartida: afecta la suspensión de la PC, aunque ningún archivo/proceso del otro proyecto se modifica. Permanece hasta restauración explícita; no se afirma aislamiento de una política de energía por proceso. No requirió UAC.

Restaurar energía original y retirar únicamente el supervisor nuevo con un comando PowerShell desde el repositorio:

    powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\restore_research_stability.ps1

El snapshot original permanece en outputs/pc_a_stability/power_original.json. La restauración no detiene MT5 ni el capturador original y no modifica valores DC. No cierra programas productores ni elimina evidencia.

El supervisor nuevo tiene mutex y arranque HKCU propio. Cada 15 segundos inspecciona solo la instalación XM identificada y el watchdog de esta captura. Solo inicia XM si falta; exige perfil Default sin otros EA y binario observador aprobado. Usa configuración de arranque AllowLiveTrading=0 y AllowDllImport=0, sin credenciales, cambios de cuenta ni Strategy Tester. Ante perfil inseguro bloquea el arranque. No reinicia MT5 por una desconexión: deja la reconexión al terminal, conserva cuarentena y registra gaps en el monitor existente. No elimina sesiones ni recupera ticks históricos. Una app bloqueada pero aún viva no se mata automáticamente.

Documentación de configuración de arranque: https://www.metatrader5.com/en/terminal/help/start_advanced/start . Enabled habilita el EA observacional; AllowLiveTrading=0 prohíbe su trading automático. El observador original no se modifica.

Cada 60 segundos consulta la estación NTS existente, que aplica su cadencia de cinco minutos y su lock. Convive con la tarea previa sin duplicar mediciones; guarda stderr y stdout locales. El muestreo de verificación real obtuvo Cloudflare autenticado; el segundo origen agotó timeout. Autenticación NTS no certifica generación de ticks XM ni continuidad UTC entre muestras. No se cambió el reloj.

Después de reinicio se requiere inicio de sesión Windows; no se configura autologin ni contraseñas. La reanudación completa también requiere red, cuenta XM persistida válida y perfil seguro. No se ha probado un reinicio físico, cierre de tapa ni crash real: las decisiones de ausencia/proceso sano se probaron con inventarios sintéticos y ningún lanzamiento real. 27 regresiones PASS. El servicio vivo siguió registrando heartbeats, sin modificar captura, ID, segmentos anteriores ni protocolos científicos. El estado de observador se verifica por sus nuevos registros; la existencia del proceso no prueba ticks de mercado.

Las tres interrupciones previas y su evidencia de suspensión permanecen íntegras. El ledger existente detecta gaps, desconexión y reconexión; no deduce pérdida cero de ticks. Los eventos nuevos del supervisor son archivos exclusivos por transición, hasheables junto al ledger nativo; causas no observadas quedan indeterminadas. Sus horas de host no certifican generación UTC.

Continúan CAUSAL_AUDIT=FAIL, dataset y entrenamiento bloqueados, Discovery Validation bloqueado, Historical Holdout bloqueado, Final Test locked, DEMO disabled, LIVE_TRADING=false. No scoring, órdenes ni backfill. Próximo estado: supervisión prospectiva en cuarentena. Ninguna intervención manual pendiente ahora.
