# Separación entre entrada y seguimiento intratrade

## Entrada

La decisión conserva las 28 señales y elige FOLLOW o INVERT. Sin SKIP ni NO_TRADE. El contexto utiliza barras cerradas hasta el primer tick de entrada. Hay contexto para 28 entradas en M5, M15 y M30, y para 27 en H1. El H1 faltante queda explícito. El script agrupa por etiquetas nativas y exige todos los componentes M5 del bucket. La paridad con series superiores nativas y la recepción original de las barras agregadas requieren evidencia adicional.

## Intratrade

Se revisaron 3.279 snapshots con marcas BID/ASK exactas en el tape, todos después de la entrada y antes de la salida del camino. MFE/MAE acumulados y PnL flotante pertenecen al estado intratrade. Los resultados finales y las excursiones posteriores pertenecen a etiquetas separadas.

| Señal original y modo | Snapshots | PnL flotante medio | MFE medio | MAE medio |
|---|---:|---:|---:|---:|
| BUY FOLLOW | 606 | 17,24 | 56,37 | 44,40 |
| BUY INVERT | 726 | 15,92 | 83,37 | 47,17 |
| SELL FOLLOW | 1.000 | 7,92 | 60,16 | 51,11 |
| SELL INVERT | 947 | 9,58 | 59,87 | 40,21 |

Valores en unidades de precio. Son medias por snapshot y las trayectorias largas aportan más observaciones. El número de unidades independientes sigue siendo el de señales, con caminos emparejados y censura. No se verificaron predictores de reversión o continuación ni se probaron políticas virtuales de gestión.

[Recibos y hashes](../research/studies/us30cash_xm_historical_ai_development_v1/technical_context/sha256.json).
