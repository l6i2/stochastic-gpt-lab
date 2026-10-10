# Protocolo de investigación

1. Congelar símbolo, fechas, proveedor, ajustes MT5, bin de perfil, fuente de perfil, calendario broker y versión del código. Registrar si hay ticks reales. No comparar mezclando feeds o configuraciones.
2. Validar CSV y audit; preservar dataset original, pérdidas, empates, valores faltantes y operaciones censuradas. Parquet es una conversión del mismo dataset, no un filtrado.
3. Particionar por **orden de señal** (sin sort correctivo ni shuffle). Defaults: primeros `floor(N*.6)` TRAIN; hasta `floor(N*.8)` DISCOVERY_VALIDATION; resto FINAL_TEST. Fracciones configurables, tres particiones no vacías y timestamps únicos crecientes.
4. Purgar del análisis TRAIN señales cuyo máximo exit_time de ambos lados alcance o supere la primera señal de validación. Aplicar lo mismo en validación frente a FINAL_TEST. Se mantienen en el archivo original y se cuentan en el manifest. Esta purga impide que etiquetas de descubrimiento utilicen precios de la partición siguiente; es conservadora también para censura.
5. Descubrir hipótesis exclusivamente en TRAIN. Revisar tamaños muestrales, faltantes, BUY/SELL, perfiles y regímenes. Los cortes de grupos son deciles de features ajustados sólo sobre TRAIN purgado. Duplicados de cuantiles reducen el número de grupos. Extremos fuera del rango de TRAIN se asignan a las colas abiertas. No se busca el threshold más rentable.
6. Congelar por escrito hipótesis, dirección esperada, variables y grupos observados, muestras mínimas, criterio de evaluación, manejo de faltantes/censura y decisiones posibles. El programa guarda copia y hash SHA-256 del archivo. Tener un archivo no prueba por sí mismo que se registró antes de mirar los datos: conservar su historial externamente.
7. Evaluar en DISCOVERY_VALIDATION con hipótesis congeladas. No hacer nuevas búsquedas ahí. FINAL_TEST no produce estadísticas durante el modo TRAIN; se verifican únicamente invariantes estructurales del dataset completo y tamaños/fronteras de las particiones.
8. Sólo cuando el protocolo esté cerrado, usar `--evaluate FINAL_TEST --unlock-final-test --hypotheses-file ...`. No repetir consultas para seleccionar patrones. Si se revisa el diseño tras verlo, se necesita otro periodo futuro completamente nuevo.

## Informes

- `summary.csv`: FOLLOW/INVERT general, BUY y SELL. Medias sobre pares completos y también medias disponibles por lado claramente separadas; victorias, pérdidas, empates, censura, MFE/MAE.
- `groups.csv`: los tres universos por percentiles de volumen 20/50/100, volumen relativo 5/10/20/50/100, expansión, distancias POC/VAH/VAL de los seis perfiles, régimen ATR por percentiles 20/50/100, hora NY y alineación EMA. Se conservan grupos missing/unavailable.
- `correlations.csv`: Pearson y Spearman de features causales explícitas frente a las tres etiquetas; n de pares no faltantes por correlación. Spearman usa rangos con empates promedio. No se reportan p-values ni se simula independencia de trades solapados.
- `feature_deciles.csv`: cuantiles descriptivos de todas las features numéricas de la partición solicitada. No alimentan thresholds operativos. En evaluación los grupos siguen usando cortes TRAIN aunque se describa la distribución de la partición evaluada.
- `missingness.csv`, `exit_reasons.csv` y manifest de parámetros, hashes, tamaños, purga y cortes.

Las señales correlacionadas y las dos direcciones de una señal **no** son muestras independientes. Comisiones ausentes, spreads, calidad de ticks y censura pueden cambiar conclusiones. No interpretar correlación como causalidad ni publicar una estrategia derivada automáticamente. No seleccionar sólo las señales en que FOLLOW gana, ni eliminar ventajas cero.

## Walk-forward

`--walk-forward --wf-initial N --wf-step M`: ventana TRAIN expansiva y ventanas posteriores de validación de M señales (la última puede ser parcial). Cada fold ajusta sus cortes usando exclusivamente su TRAIN; purga etiquetas que crucen la frontera del fold y de validación al siguiente fold. Se usa sólo el conjunto anterior a FINAL_TEST y se purga también la frontera final. Los informes se escriben separados por fold. Los tamaños están en señales, pero las ventanas son cronológicas. El walk-forward muestra estabilidad temporal; no busca tamaños ni selecciona reglas.

Para investigación con GPT, suministrar únicamente informes TRAIN durante descubrimiento; adjuntar especificación y diccionario. Pedir hipótesis descriptivas con incertidumbre y soporte muestral. No adjuntar FINAL_TEST a la conversación exploratoria.
