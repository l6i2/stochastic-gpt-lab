# Prerregistro de diseño — US30CASH_M5_NATIVE_20261030_01

Estado **PRE_TRAIN / DESIGN_PREREGISTERED / DATASET_UNALLOCATED**. Publicado antes
de outcomes de este estudio inexistente; no equivale a registro completo de un
estudio con datos, ni a autorización. Ningún fit, scoring, cohorte o presupuesto
se activa. El anexo nativo aprobado solo autoriza diagnóstico y preparación.

## Pregunta, hipótesis y estrategia inmutable

¿Permiten seis features de entrada cerradas predecir la ventaja FOLLOW−INVERT en
un dataset nuevo no expuesto? Cuatro contrastes primarios predefinidos: BUY frente
a FOLLOW_ALWAYS, BUY frente a INVERT_ALWAYS, SELL frente a FOLLOW_ALWAYS y SELL
frente a INVERT_ALWAYS. Para cada contraste H0: media de delta pareado <=0;
H1: >0. La afirmación conjunta requiere superar **los cuatro** contrastes.
Agregado, medianas y subgrupos de fuente son descriptivos, nunca selección.

US30Cash M5, MAIN_K 5/3/3 SMA Low/High, BUY anterior <=20/actual >20, SELL anterior
>=80/actual <80, siguiente barra observada, ambos caminos FOLLOW/INVERT,
TP240/SL180/TIME_EXIT100 y censura originales. No se modifica entrada/salida,
estrategia, timestamp, calendario ni productor. La asignación investigada es una
predicción virtual, no una política operativa. No hay órdenes, DEMO o promoción.

## Datos y parada de adquisición (todavía inactiva)

DATASET_ID `us30cash_m5_native_new_01_reserved` identifica una **reserva de nombre**,
no datos existentes. Requiere inicio real posterior a una asignación de rol exclusiva
autorizada, session/sequence/contador monotónico observados y primer M5 completo
posterior. No heredar históricos, warmup ni cohortes previas. Si un rol protegido
queda abierto o su intervalo es desconocido/no comparable, la asignación falla.
No inferir independencia de hashes distintos de una redescarga.

La adquisición propuesta conserva todo el stream post-inicio: al menos 350 barras
cerradas de warmup propio, semillas nativas/HA completamente vinculadas a ese origen,
y las primeras **800 señales base consecutivas** posteriores, sin selección por
features, lado, labels o rendimiento. Después conservar exactamente hasta completar
100 barras M5 observadas tras la última entrada, para ambos horizontes de salida,
y sellar. Si las 800 no se alcanzan o falta cobertura/continuidad verificable,
NOT_READY; no reemplazar fechas, prolongar tras ver efectos ni rellenar gaps.
El inicio, la cobertura disponible y el límite de almacenamiento/operación deberán
quedar vinculados al plan de captura antes de su activación. El conteo de señales
es metadata de elegibilidad, nunca scoring. Conexión perdida/reinicio segmenta;
no hace backfill ni prueba ausencia de pérdidas con el simple retorno del servicio.

No introducir barras de cache anterior para inicializar iATR/iStochastic/HA.
350 barras solicitadas por el exportador **no prueban** aislamiento del seed nativo.
Exigir historia de tester aislada, hashes/identidad y registro de inicialización
completos. HA es recurrente desde seed, ready a 276 barras, sin truncación fingida;
ATR nativo también exige procedencia de inicialización, sin sustituir su definición
por el adaptador sintético. No interpretar 100 barras observadas como 500 minutos.

## Whitelist, modelo y presupuesto

Features exactas: **stoch_k, delta_k_1, ATR, relative_volume_20, ha_direction,
range_to_ATR**. Definiciones y dependencias en `temporal_dependencies.json`;
whitelist/modelo en `feature_model_whitelist.json`. Todas de barra cerrada shift 1,
disponibles después de calcular contexto en el callback de decisión. No utilizar
barra actual, IDs, timestamps, entradas Bid/Ask, spread de llegada, campos UTC/NY,
sesiones, targets o labels como predictores. No selección de features ni nuevas
interacciones. La igualdad de prefijos sintéticos no certifica vintage real.

Una sola familia: regresión logística L2 **separada para BUY y SELL**, C=1,
solver=lbfgs, max_iter=1000, class_weight=None, seed=20261030. Target:
`follow_PnL - invert_PnL > 0`. Umbral fijo: p>0.5 FOLLOW, p<=0.5 INVERT.
Escalar por media/desviación poblacional de cada TRAIN del fold; desviación cero
se cambia por 1. Sin imputación: filas con alguna feature no finita no ajustan
coeficientes y reciben FOLLOW fijo; conservar filas, resultados y reporte missing.
Si falta una clase o no converge, FAIL técnico/NOT_RUN, sin cambiar parámetros.

Presupuesto: **una familia, una configuración, dos modelos por fold, cuatro
folds, máximo ocho fits planificados**. Cero fit final sobre todo el dataset,
cero búsqueda de hiperparámetros, cero selección de periodo/latencia/feed. Una
sola ejecución científica futura autorizada, no retry adaptativo. Presupuesto
actual autorizado: **cero fits y cero scoring**. No relanzar V2, R2–R4 ni TRAIN
agotado. Reproducción idéntica requeriría permiso que no permita selección.

## Particiones cronológicas y purged walk-forward

Preservar orden nativo de señales, sin shuffle ni sort correctivo. Un ID por señal
y ambos caminos unidos. El índice de llegada desambigua timestamps iguales.
Primeros floor(N/2) IDs del **nuevo TRAIN** son el prefijo inicial. El resto forma
cuatro bloques consecutivos con fronteras
`floor(N/2)+floor(j*(N-floor(N/2))/4)`, j=0..4. Ajustar cada fold exclusivamente
con el prefijo anterior y sus transforms. Purgar si **cualquiera** de sus dos exits
alcanza o supera el primer instante de decisión del bloque evaluado. Purgar el
final de cada bloque frente al siguiente. No tomar labels fuera del dataset
sellado, ni leer conjuntos protegidos como warmup o continuación de targets.

Censura queda registrada y no se convierte en cero ni se elimina silenciosamente.
El conjunto pareado completo se identifica sin filtrar pérdidas; informar todos
los IDs, conteos de exclusión y sensibilidad al alcance de censura. Si la censura
impide una comparación común suficiente, INCONCLUSIVE. Estos bloques son
validación interna del nuevo TRAIN, no Discovery Validation ni holdouts.

## Métricas y aceptación conjuntiva antes de cualquier promoción

Reportar deltas pareados medios/medianos frente a ambos baselines, BUY y SELL,
conteos por fold/lado/FOLLOW/INVERT, missingness, censura, concentración de efecto
y drawdown proxy de tamaño fijo. Sin rankings ni selección de subgrupos.

Bootstrap pareado por señal (ambos caminos juntos), 10.000 resamples, seed 20261030;
reportar IC95% percentiles. Para los cuatro contrastes primarios exigir además
límite inferior unilateral **98,75%** >0 (alpha 0,05/4, Bonferroni predefinido).
Esto es un criterio preregistrado, no garantía de cobertura bootstrap con dependencia.
Repetir como sensibilidad obligatoria por bloques consecutivos de **451 barras M5
observadas**, anclados al primer índice admitido; 350 de contexto +100 de horizonte
+1 de llegada. Remuestrear bloques completos con sus señales; bloque final
incompleto conservado. Exigir también límites inferiores >0 por lado/baseline.
No elegir longitud o semilla favorables. HA/ATR pueden conservar memoria más larga;
este control no demuestra independencia temporal absoluta. IC degenerado o
dependencia que invalide la interpretación → INCONCLUSIVE, sin umbrales nuevos.

Soporte mínimo: >=200 señales evaluables total, >=80 BUY y >=80 SELL, >=3 folds
evaluables por lado. Para cada uno de los cuatro contrastes, efecto positivo en
>=70% folds y ningún fold aporta >50% del efecto positivo. Drawdown proxy no más
de 20% peor que cada baseline. Los umbrales se fijan antes de datos del estudio;
no se reducen para alcanzar PASS. No heredan autorización de protocolos anteriores.

Integridad, dominio/identidad y dependencias: todos los artifacts admitidos con
hashes exactos, 100% quotes requeridos finitos `0<bid<=ask`, OHLC coherente, secuencia
conservada, cero dependencias futuras/protegidas/no declaradas. Duplicados de
timestamps se cuentan/conservan; IDs duplicados se rechazan. No asumir calendario
NYSE para US30Cash ni inventar sesiones/excepciones. Cobertura desconocida impide
afirmar cobertura completa; discrepancias y gaps no resueltos → QUARANTINED.

PASS_INTERNAL_RESEARCH_ONLY requiere todos los criterios. Integridad/causalidad
fallida → REJECTED; soporte/cobertura/semillas/uncertidumbre insuficientes →
NOT_READY/INCONCLUSIVE; criterios de efecto incumplidos → FAIL. Todos terminales
para el intento, sin retuning, extensión o nueva familia sobre los mismos datos.
Registrar errores/abortos/exposición sin borrar intentos. Un PASS interno no
abre validación protegida, no promueve candidato y no autoriza trading.

## Gates y autorización

Primero se necesita dataset independiente verificable, ledger y membership
completos, warmup/seed aislados, cobertura, código/entorno versionados y paquete
de hashes. Solo después presentar autorización científica de ese estudio/dataset
específico antes de cualquier fit. Este expediente no solicita aprobación ahora:
DATASET_HASH es null porque no existe dataset admitido. El hash de un manifiesto
vacío no lo sustituye. La publicación Git deja constancia externa del diseño.

Se mantienen Discovery Validation e Historical Holdout BLOCKED, Final Test LOCKED,
cohortes científicas inactivas, TRAIN agotado cerrado, DEMO DISABLED,
LIVE_TRADING=false y CAUSAL_AUDIT global FAIL sin override.
