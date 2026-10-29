# Certificación XM/UTC: partición de intervalos

Reporte principal en America/Guayaquil. Se conserva íntegro el módulo horario aprobado. El registro de esta revisión es un snapshot, no una reclasificación automática de futuras capturas.

## Resultado científico

CERTIFIED_INTERVALS está vacío. Ambos intervalos archivados quedan QUARANTINED con límites enteros originales nativos, chain head, SHA canónico del manifest y SHA del archivo snapshot por separado. Ningún límite se etiqueta UTC. El histórico cubre [1704153600000,1704240000000) en dominio nativo. La captura prospectiva tiene su propio intervalo creciente detallado en audit.json. Las filas, su multiplicidad, timestamps y originales no se modifican. Las cero barras almacenadas en el archivo histórico original no eliminan la reconstrucción versionada de 276 barras nativas previamente contrastadas; son artefactos diferentes.

La herramienta offline `tools/audit_xm_utc_intervals.py` verifica fuentes v11, ambas cadenas de archivo, hashes del bundle de correlación y de las mediciones adicionales y suplementarias; también verifica el CSV nativo aprobado. Reutiliza esos registros sin consultas de ticks, sin repetir probes y sin TimeTradeServer como referencia independiente. La partición es un catálogo derivado: no mueve, copia a TRAIN, admite ni modifica datos. Un cambio futuro del mapping provoca revisión explícita en lugar de certificar intervalos automáticamente.

## Correlación existente

50 lecturas y 21 payloads distintos conservan hashes verificables. El timestamp nativo menos la referencia externa proyectada abarca aproximadamente 7199,053–7199,900 segundos. Es una diferencia observada de coordenadas temporales, no un offset autorizado ni una estimación de latencia. Las 50 lecturas son futuras bajo interpretación directa UTC; esa interpretación queda rechazada para este snapshot. No se deduce por ello una resta fija de dos horas ni se extrapola al histórico.

Las tres referencias NTP y TLS corroboran la recepción de forma diagnóstica, no la identidad UTC del evento XM. Las 50 diferencias de contador para la llamada API son cero: se clasifican como lecturas indistinguibles, no latencia cero. Las muestras corresponden al último quote obtenido por polling, no al instante garantizado de llegada al terminal. No hay una cota calibrada de deriva del contador para convertir esa proyección en certificación de precisión. No se fabrica retrospectivamente información faltante.

## Semántica documental

[MqlTick](https://www.mql5.com/en/docs/constants/structures/mqltick) describe time/time_msc como actualización de precio en segundos/milisegundos. [CopyTicks](https://www.mql5.com/en/docs/series/copyticks) permite sincronizar ticks ausentes desde el servidor; conservar reconsultas no prueba recepción original. [CopyRates](https://www.mql5.com/en/docs/series/copyrates) entrega barras, puede descargar/construir historia y admite barra actual. Apertura de barra, actualización de quote y recepción local se mantienen como dominios distintos.

Los contratos Python de [ticks](https://www.mql5.com/en/docs/python_metatrader5/mt5copyticksrange_py) y [barras](https://www.mql5.com/en/docs/python_metatrader5/mt5copyratesrange_py) sí afirman UTC. Esa afirmación genérica se conserva tal cual; no se oculta la contradicción con las capturas del servidor exacto ni se declara que MetaQuotes haya certificado un offset alternativo. TimeTradeServer es cálculo dependiente del equipo y no resuelve esa contradicción.

## Sesiones US30Cash

Se reutiliza el probe sellado XMGlobalSC-MT5 5: cotización lunes-viernes 00:00–23:00; operación lunes-jueves 00:05–22:55 y viernes 00:05–22:50, todas etiquetas nativas observadas. La [API de sesiones](https://www.mql5.com/en/docs/marketinformation/symbolinfosessiontrade) consulta día de semana y hora; no aporta un calendario fechado de excepciones. No se presume que ausencia de ticks sea cierre, ni que presencia de quote pruebe aceptación de órdenes. No se envían órdenes para probarlo.

La búsqueda acotada encontró un [calendario oficial XM de 2022](https://www.xm.com/assets/pdf/new/holiday_schedule/2022/XM_Stocks/EN_XM-holiday-trading-hours-2022.pdf). Tiene alcance temporal distinto y no identifica este servidor en los intervalos 2024/2026. Su descarga local devolvió HTTPError; se preserva el recibo de fallo y la referencia documental, sin inventar hash del PDF. Tablas de otras entidades/servidores se excluyen. Calendario PARTIAL y dated_exception_coverage UNKNOWN; una lista vacía no significa que no existan excepciones.

## Auditoría causal y continuación

El guard existente devuelve NATIVE_UTC_MAPPING_UNVERIFIED. Cero filas normalizadas admitidas; feature_max_time <= decision_time y quote_time <= decision_time no son evaluables sobre estos datos. CAUSAL_AUDIT=FAIL, independientemente del PASS de 34 tests afectados. TRAINING_READINESS=BLOCKED_BY_RESEARCH_GOVERNANCE. Collector activo en cuarentena, sin backfill retrospectivo. Discovery y Final Test cerrados; DEMO deshabilitado, LIVE_TRADING=false.

Falta una fuente independiente que vincule inequívocamente el evento exacto del servidor con UTC y su incertidumbre; además, intervalos históricos y transiciones respaldados por evidencia y un calendario fechado del servidor. Los patrones de precios, horarios de otra entidad, IANA y un reloj de recepción por sí solos no aportan esa prueba. Las plantillas existentes pueden recibir documentación/exportaciones verificables de XM sin activación automática. No se requiere intervención para que la captura segura continúe. Para cerrar la certificación sigue siendo necesaria evidencia externa no disponible por los canales públicos revisados; no se enviaron solicitudes a terceros.
