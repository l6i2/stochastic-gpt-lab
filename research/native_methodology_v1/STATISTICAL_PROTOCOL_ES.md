# Diseño estadístico nativo v1 — preparado, sin autorización de estudio

Estado: **DESIGN_FROZEN_STUDY_NOT_REGISTERED**. Este diseño se publica antes de
leer outcomes de un nuevo estudio. No es una preregistración completa: faltan el
dataset independiente, membership, ledger de exposición y autorización específica.
Ningún entrenamiento ni scoring se ejecuta por publicar este archivo.

## Pregunta y alcance

Estimar, en un estudio futuro separado, si contexto cerrado nativo permite una
predicción reproducible de la ventaja FOLLOW−INVERT con los mismos eventos
Stochastic y salidas congeladas. Se conservan **ambos caminos por señal**, BUY y
SELL por separado, TP240/SL180/TIME_EXIT100 y la entrada virtual original.
No cambia la estrategia ejecutable ni se produce candidato operativo.
El resultado es evidencia de simulación, no de fills negociables ni UTC físico.

## Especificación que se debe sellar antes de outcomes

Un estudio = un ID, dataset y presupuesto, sin reutilizar TRAIN agotado. Registrar
hashes del protocolo, fuente/servidor/símbolo/build, productor/EX5/controlador,
parámetros, raw artifacts, calidad, membership por señal, ledger de exposición
completo, warmup y horizontes de ambas etiquetas. Aprobar expresamente todos esos
identificadores antes del primer fit. Fecha aparente o datos redescargados no
demuestran independencia. No reutilizar ninguna cohorte protegida.

La familia propuesta es **una regresión logística L2 por lado original**, seed
20261030, C=1, solver lbfgs, max_iter=1000, class_weight=None. No búsqueda de
hiperparámetros ni comparación de algoritmos, features o subconjuntos. Una falta
de convergencia implica NOT_RUN/FAIL técnico; no subir iteraciones tras resultados.
Predictoras exactas propuestas: stoch_k, delta_k_1, ATR, relative_volume_20,
ha_direction y range_to_ATR, todas de entrada y barra cerrada. Se escala cada
columna por media/desviación poblacional de su TRAIN del fold; desviación cero
se sustituye por 1. No usar IDs, timestamps, llegada/entrada Bid/Ask, spread de
entrada, sesiones, targets ni resultados futuros como features.

Target de entrenamiento: `follow_PnL - invert_PnL > 0`, con ambas etiquetas
completas. Predicción p>0.5 asigna FOLLOW; p<=0.5 asigna INVERT, sin ajuste de
threshold. Filas sin alguna predictora finita reciben FOLLOW por regla fija y
no se usan para ajustar coeficientes; se conservan y reportan como missing, sin
ocultar su resultado. Censura no es una pérdida ni un cero: no participa del fit,
se conserva en soporte/cobertura. Ningún PnL se calcula en esta preparación.

Estas especificaciones son **una propuesta de nuevo estudio**, no ejecución de
V2 pendiente ni relanzamiento de las familias rechazadas. Si se requiere cambiarlas,
hacerlo antes de autorizar el dataset/estudio y registrar nuevo hash/justificación.

## Cronología, walk-forward y purga

Orden de señal nativo preservado, nunca shuffle/sort correctivo. Agrupar todos los
snapshots y FOLLOW/INVERT de una señal en la misma unidad. El orden de llegada
desambigua timestamps repetidos; duplicados de IDs se rechazan.

Dentro de TRAIN_NEW autorizado exclusivamente, primeros floor(N/2) IDs son el
TRAIN inicial. El resto se divide en cuatro bloques consecutivos: fronteras
floor(N/2)+floor(j*(N-floor(N/2))/4), j=0..4. En cada fold ajustar solamente con
el prefijo anterior, purgando señales si cualquiera de sus dos exits alcanza o
supera el primer instante de decisión del bloque evaluado. Purgar igualmente el
final del bloque por la frontera siguiente. Un horizonte no resuelto no se
inventa ni se ignora: la señal no es elegible para ajuste/evaluación completa,
permanece en el reporte de censura. Separar prehistoria/warmup admitida de las
filas que aportan outcomes; ninguna dependencia puede entrar en un conjunto
protegido. Folds inválidos no se reemplazan por fechas elegidas manualmente.

Los bloques son validación interna de este nuevo TRAIN, **no Discovery Validation,
Historical Holdout o Final Test**. Ningún resultado posterior del fold puede
redefinir modelos, scaling, features, reglas de missing ni fronteras.

## Baselines, incertidumbre y criterios conjuntivos propuestos

Comparar siempre con FOLLOW_ALWAYS e INVERT_ALWAYS sobre las mismas señales;
reportar BUY, SELL y agregado, además de conteos FOLLOW/INVERT, missing/censura,
soporte por fold y calidad por bloque de fuente. La unidad de bootstrap es la
señal, preservando juntos sus dos caminos y snapshots; 10.000 resamples,
seed 20261030, intervalos percentiles 95%. No tratar caminos solapados como muestras
independientes: informar la dependencia residual temporal; el bootstrap por señal
no la elimina. Añadir bootstrap pareado de bloques consecutivos de 451 barras M5
observadas, anclados al primer índice admitido (350 barras de contexto exportado
+100 de horizonte de etiqueta +1 de llegada). Remuestrear bloques completos con
las señales asignadas por su llegada original; seed y resamples iguales al
bootstrap por señal. Reportar el bloque final incompleto sin rellenarlo. Exigir
también IC95% inferior >0 por lado contra ambos baselines bajo este diagnóstico;
si no se puede construir un IC no degenerado, INCONCLUSIVE. La longitud proviene
de esas dependencias del productor, no de maximizar rendimiento. HA/EMA conservan
recurrencia más larga: este control no prueba independencia temporal completa.
No buscar otra longitud de bloque que produzca PASS ni afirmar robustez universal.

Requisitos mínimos propuestos heredados de la escala conservadora de V2, ahora
explícitamente sujetos a la nueva autorización: >=200 señales evaluables en total,
>=80 por lado y >=3 folds evaluables por lado. Deben cumplirse antes de interpretar
efectos; no bajar mínimos para adaptar el dataset. Además, cada lado debe tener
efecto medio positivo frente a **ambos** baselines y límite inferior de sus IC95%
por encima de cero; >=70% folds positivos por lado frente a ambos baselines;
ningún fold aporta >50% del efecto positivo. Reportar drawdown de tamaño fijo;
no más de 20% peor que cada baseline. Son criterios de investigación propuesta,
no cambio de gates de los protocolos congelados.

El baseline histórico mantiene su entrada idealizada en el primer tick observado.
Para una afirmación sobre política ejecutable aún haría falta replay de llegada y
fill posterior, coste de cómputo/comisiones/slippage y evidencia adicional; este
estudio no puede adjudicársela. En pruebas de políticas, conservar 250 ms primario
y 0/500 sensibilidad, índice estrictamente posterior y barreras antes del fill;
no elegir la latencia favorable. No se cambia el esquema de entrada del baseline.

Resultados posibles: REJECTED ante fallo de integridad/causalidad; INCONCLUSIVE
ante insuficiencia de soporte, censura que impida el conjunto común completo,
incertidumbre o dependencia no resuelta; FAIL ante fallo de los criterios fijados;
PASS_INTERNAL_RESEARCH_ONLY si se cumplen todos. Ninguno abre un conjunto ni
autoriza promoción. Un resultado terminal no permite retuning/retry en los mismos
datos; documentar intentos, errores y exposiciones, sin borrar ejecuciones fallidas.

## Condiciones de inicio, parada y reproducción

Antes del fit se requiere autorización explícita de estudio, membership y ledger
independientemente revisados, productor verificado por prefijos, whitelist exacta,
calidad/cobertura y ventanas de dependencia válidas. El preflight de independencia
solo comprueba estructura; no puede autenticar su propio ledger. No se cargan
outcomes si falta alguna condición. Registrar versiones y entorno de librerías,
seed, configuración, logs y hashes; repetir solo reproducción idéntica autorizada,
nunca seleccionar el mejor run. No escoger fechas por rendimiento.

Guardas invariantes: TRAIN agotado no reabierto; Discovery Validation/Historical
Holdout bloqueados; Final Test locked; cohortes científicas inactivas; scoring y
entrenamientos nuevos no autorizados; DEMO disabled; LIVE_TRADING=false.

La siguiente autorización sería aprobar **un estudio nuevo concreto**, con sus
datos independientes, reglas de dependencia temporal, soporte, protocolo/hash,
presupuesto de una familia y destinos de salida. No puede concederse de manera
informada hasta disponer de ese paquete; este documento no lo sustituye.
