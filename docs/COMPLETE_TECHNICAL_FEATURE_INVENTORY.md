# Inventario técnico multivariable

Whitelists de entrada e intratrade candidatas. Revisión científica requerida antes de cualquier fit. La whitelist congelada sigue vigente.

| Familia | Variables | Dependencias | Estado del día fijo |
|---|---|---|---|
| Stochastic | K, D, pendientes, cruces, aceleración, divergencia | M5 cerradas y pivotes ya confirmados | MAIN_K reproducido. K/D medidos; divergencias y aceleración pendientes |
| EMA | EMA 9/20/50/100/200, distancia, pendiente y alineación | M5 cerradas y semilla específica por periodo | EMA20/50/100/200 exportadas; EMA9 y semillas propias pendientes |
| Soporte y resistencia | niveles, rechazo, ruptura, retesteo y ruptura fallida | pivote confirmado, ventana previa y estado secuencial | propuesto; no se retrofecha la confirmación |
| Estructura | HH, HL, LH, LL y cambios de estructura | pivotes confirmados y rango anterior que excluye la barra actual | exportación intratrade presente; auditoría de definición pendiente |
| Velas | cuerpo, mechas, rango, patrones y secuencias | OHLC cerrados, catálogo fijo y ventanas previas | OHLC verificado; patrones propuestos |
| Heikin Ashi | dirección, continuidad, intensidad y transición | OHLC cerrados, recurrencia y semilla trazable | campos exportados; semilla no certificada para fit |
| Volumen | relativo, anomalías, picos, divergencia y desplazamiento | tick volume BID, baseline previo y pivotes confirmados | volumen BID verificado; relativo exportado |
| Perfil de volumen | POC, VAH, VAL, HVN y LVN | ticks de ventana cerrada, bins fijos, empates y política de gaps | insumos diagnósticos disponibles; perfiles y fronteras pendientes |
| Volatilidad | ATR, compresión, expansión y régimen | TR de barras cerradas, semilla ATR y umbrales congelados | ATR exportado; semilla y régimen pendientes |
| Tendencia y momentum | intensidad, aceleración, agotamiento y cambios | retornos y pendientes causales; horizonte futuro solo como etiqueta | propuesto para verificación |
| Nueva York | fases, volatilidad y contexto | mapping de evento a UTC demostrado más IANA America/New_York | no disponible con mapping certificado |
| Multitemporal | M5/M15/M30/H1, rango y desplazamiento | M5 cerradas, bucket completo y cutoff de decisión | agregación nativa diagnóstica verificada |
| Intratrade | PnL flotante, MFE/MAE, retroceso, recuperación y pérdida de impulso | entrada, BID/ASK de marca y prefijo de quotes hasta snapshot | orden y marca exacta verificados; etiquetas y políticas pendientes |

[Recibos y hashes](../research/studies/us30cash_xm_historical_ai_development_v1/technical_context/sha256.json).
