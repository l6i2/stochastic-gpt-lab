# stochastic-gpt-lab

Laboratorio **independiente** para MetaTrader 5: estrategia Stochastic M5 fija, simulación interna FOLLOW/INVERT y dataset causal. No pertenece a `asistente-trader-ia`. No contiene funciones para enviar órdenes. No necesita cuenta real ni credenciales.

## Qué implementa

- Stochastic `(5,3,3)`, SMA, Low/High. BUY: línea anterior `<=20` y actual `>20`; SELL: anterior `>=80` y actual `<80`. `MAIN_K` por defecto; `SIGNAL_D` configurable. **No es cruce K/D**.
- Señal al cierre de M5 y entrada en el primer tick de la siguiente vela disponible. BUY Ask/salida Bid; SELL Bid/salida Ask. TP 240 y SL 180 en **unidades absolutas de precio**, vencimiento a 100 barras M5.
- Una fila por señal; múltiples operaciones virtuales independientes; ambos contrafactuales, pérdidas, empates y censura al terminar los datos.
- Seis Volume Profiles causales, features de volumen, velas, volatilidad, tendencia, estructura y tiempo. CSV UTF-8; conversión a Parquet desde Python.
- TRAIN/VALIDATION/TEST cronológicos 60/20/20, purga de etiquetas que cruzan fronteras y walk-forward. Análisis descriptivo, sin búsqueda de reglas.

## Estructura

```text
mt5/StochasticResearchEA.mq5     EA para Strategy Tester
mt5/ResearchCore.mqh            reglas escalares compartidas con las pruebas
mt5/HeikinAshiCore.mqh           serie HA persistente y 54 features causales
python/heikin_ashi.py           contrato y validación HA
python/research.py             contrato, validación, particiones y oráculo de perfil
python/validate_dataset.py     validador y conversión Parquet
python/analyze_dataset.py      informes descriptivos
requirements.txt
tests/                        pruebas sintéticas y núcleo C++
docs/STRATEGY_SPEC.md
docs/DATA_DICTIONARY.md
docs/RESEARCH_PROTOCOL.md
docs/MT5_ACCEPTANCE.md
docs/VERIFICATION.md
outputs/.gitkeep
```

## Ejecutar en MT5

1. Copiar **los tres** archivos de `mt5/` a `MQL5/Experts/StochasticResearch/`. Abrir el `.mq5` en MetaEditor y compilar con F7.
2. Abrir Strategy Tester, elegir el EA, US30/US30Cash o el equivalente del broker y M5. El cálculo utiliza M5 de forma explícita incluso si el gráfico tiene otro periodo.
3. Elegir **Every tick based on real ticks** y `ConfirmRealTickTesterMode=true`. El EA no puede verificar automáticamente ese ajuste del terminal: la confirmación es una declaración del investigador. Mantener `LIVE_TRADING=false`. La optimización del tester está bloqueada.
4. `ResearchSymbol=""` usa el símbolo del tester. Si se configura otro nombre, debe coincidir exactamente con ese símbolo. No hay ejecución multi-símbolo.
5. Verificar `ServerUTCOffsetWinterHours` y `ServerDSTRule` contra el histórico del broker. Defaults: UTC+2 en invierno, DST europeo. **No son una inferencia automática del broker.** Para broker sin DST usar `DST_NONE`.
6. `ProfileBinSize=10.0` por defecto; `profile_weight=TICK_ACTIVITY` es la opción inicial para CFDs. Registrar parámetros y versión del código antes de investigar. Cambiar la anchura de bins cambia las features, no la señal.
7. Descargar suficiente prehistoria (al menos 350 barras M5; más para estabilización de EMA200) y ticks de la sesión anterior. Elegir fechas con datos reales. El EA comienza a generar señales en el primer cierre completo observado después de su inicialización.
8. Elegir `OutputFile` nuevo para cada corrida. El EA rechaza sobrescrituras. No añadir comas al nombre del símbolo.
9. Al finalizar, recuperar `stochastic_events.csv` y `stochastic_events.csv.audit.json` del `MQL5/Files` del **agente local del tester**. Consultar Journal para abortos. Copiar ambos a `outputs/`.

No se genera un dataset histórico hasta ejecutar MT5 con datos del broker. Las pruebas usan datos sintéticos claramente identificados.

### Si no hay resolución intrabar

Seleccionar explícitamente `simulation_mode=BAR_CONSERVATIVE`. En una vela ambigua gana SL, salvo un gap de apertura que ya resuelva la salida. El Ask histórico se aproxima con OHLC Bid más el spread almacenado de la barra; no reproduce el spread intrabar. MFE/MAE son **cotas de la vela completa de salida**, no excursiones exactas. `TICK_QUOTES` es la modalidad de referencia. Nunca mezclar modalidades en un dataset.

## Python

Python 3.10+; numpy y pandas para análisis, pyarrow o fastparquet para Parquet. `python/parquet_io.py` selecciona fastparquet si el CPU no soporta SSE4.2. Crear un entorno aislado:

```bash
python3 -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate
python -m pip install -r requirements.txt
python python/validate_dataset.py outputs/stochastic_events.csv \
  --parquet outputs/stochastic_events.parquet
python python/analyze_dataset.py outputs/stochastic_events.parquet \
  --output outputs/discovery_001
python python/analyze_dataset.py outputs/stochastic_events.csv \
  --output outputs/walk_forward_001 --walk-forward --wf-initial 1000 --wf-step 300
python -m unittest discover -s tests -v
```

Las pruebas del núcleo requieren `g++`; no requieren MT5. Los tamaños de walk-forward se expresan en señales, manteniendo el orden temporal. Si no quedan datos después de la purga, ampliar el histórico; no quitar la protección.

Los informes incluyen `summary.csv`, `groups.csv`, `correlations.csv`, `feature_deciles.csv`, `missingness.csv`, `exit_reasons.csv` y `manifest.json`. Se separan ALL/BUY/SELL. Los directorios de salida existentes no se sobrescriben.

Para evaluar hipótesis **ya congeladas en TRAIN**:

```bash
python python/analyze_dataset.py outputs/stochastic_events.csv \
  --output outputs/validation_001 --evaluate DISCOVERY_VALIDATION \
  --hypotheses-file docs/my_frozen_hypotheses.md
# Sólo evaluación final deliberada, una vez fijado el protocolo:
python python/analyze_dataset.py outputs/stochastic_events.csv \
  --output outputs/final_001 --evaluate FINAL_TEST --unlock-final-test \
  --hypotheses-file docs/my_frozen_hypotheses.md
```

Crear el archivo de hipótesis como resultado de la investigación; no existe un patrón rentable predefinido. El control de acceso al test es una protección operativa, no una garantía de que un humano no vuelva a consultarlo.

## Límites importantes

El flujo reproducible está disponible en `python/pipeline.py`: `historical` informa cobertura/bloques existentes sin iniciar MT5; `validate`, `build-master`, `train-analysis`, `validate-hypotheses`, `ml-train` y `candidate` realizan las etapas de investigación. `candidate` se bloquea si ninguna hipótesis congelada sobrevive. No hay comando FINAL_TEST en el orquestador. El Tester MT5 aún se inicia fuera del orquestador y requiere verificar su log/dataset por bloque.

La verificación local vigente de MT5 y la cobertura medida de XM están en [estado del proyecto](docs/PROJECT_STATUS.md). Esa verificación incluye un `.ex5` compilado por MetaEditor con 0 errores y 0 warnings y un smoke test DEMO; los datos crudos permanecen locales. Consultar también [aceptación en MT5](docs/MT5_ACCEPTANCE.md). PnL/MFE/MAE son unidades de precio: no incluyen comisiones, swap, lotes o conversión monetaria. El perfil usa la historia que entrega el broker; una consulta exitosa no garantiza cobertura completa. La reproducción de una implementación histórica externa requiere comparar su línea trigger, SMA/LowHigh, calendario, fills y datos. No se afirma equivalencia con código original que no se ha proporcionado.

## Heikin Ashi causal (schema 1.1)

Añade **54 features HA**, sólo contexto de investigación: OHLC sintéticos, cuerpo/mechas, dinámica, ratios, streaks, promedios, morfología y transiciones. HA nunca genera/cancela señales ni cambia BUY/SELL, TP=240, SL=180, TIME_EXIT=100 o FOLLOW/INVERT.

`HA_Close=(O+H+L+C)/4`; seed `HA_Open=(O+C)/2`; después `HA_Open=(HA_Open_previo+HA_Close_previo)/2`. High/Low son max/min entre precio original, HA_Open y HA_Close. Se procesa prehistoria y cada barra M5 cerrada, con estado persistente (no se reinicia por señal). Warmup fijo 256 barras y 20 barras adicionales para ventanas completas: listo desde la barra 276. Las señales con warmup insuficiente se conservan con HA vacío. Las fórmulas, tolerancias y metadata están en DATA_DICTIONARY.

El informe `ha_interactions.csv` cruza dirección/streak/transición/fuerza/expansión HA con señal original, volumen, niveles y estado de Value Area de los seis perfiles, y régimen ATR. Incluye ALL/BUY/SELL y resultados FOLLOW/INVERT. Son 30 pares predefinidos; no se buscan combinaciones ni se seleccionan reglas. Cortes numéricos ajustados sólo en TRAIN o TRAIN de cada fold. FINAL_TEST sigue bloqueado.

Schema 1.0 continúa compatible con validación, análisis y conversión Parquet; sin informes HA ni reconstrucción artificial de su historia. Nuevos CSV/audit usan 1.1. Las pruebas compilan y ejecutan también el núcleo HA real como C++ y lo comparan con un oráculo independiente. La compilación del EA en MetaEditor se verificó con 0 errores y 0 warnings para el código vigente en la auditoría; revisar [estado del proyecto](docs/PROJECT_STATUS.md) para el HEAD auditado y límites actuales.

## Round two (TRAIN → DISCOVERY_VALIDATION)

La ronda dos mantiene los eventos Stochastic obligatorios y compara FOLLOW/INVERT sin `SKIP` ni `NO_TRADE`. El set de diez hipótesis y el pequeño conjunto de interacciones están fijados en código antes de la única validación. Los clasificadores usan un whitelist causal reducido, interacciones predefinidas y calibración logística con folds temporales dentro de TRAIN. Los comandos `round2-entry-freeze`, `round2-entry-interactions`, `round2-entry-validate`, `ml-train --round2` e `intratrade-status` están en `python/pipeline.py`. No existe un comando FINAL_TEST.

La exportación actual del EA no guarda estados de operaciones abiertas a través de las barras. El constructor de snapshots debe esperar un export nuevo de la secuencia tick/bar y estados virtuales; los resultados terminales MFE/MAE no se usan para reconstruirlo. Consulta [estado de round two](docs/ROUND2_STATUS.md) y el [protocolo intra-trade](docs/INTRATRADE_RESEARCH_PROTOCOL.md).

\n
