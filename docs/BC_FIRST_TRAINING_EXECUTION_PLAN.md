# Primera ejecución B+C — preparada, no autorizada

1. Adquirir solo el periodo posterior al corte nativo nuevo; mantener TRAIN_CONTEXT y TRAIN_DEV exclusivos. Primeros 350 M5 de contexto, primeras 800 señales base y 100 barras posteriores.
2. Validar vintages, precios, volumen, intervalos, calendario y sus excepciones, semillas y disponibilidad causal nativa. Conservar fuera cualquier segmento no demostrado. No mezclar C+F ni B legacy.
3. Calcular exclusivamente los labels de baselines congelados para el nuevo TRAIN. Exigir entradas/quotes reales, horizontes completos y no usar resultados para cambiar hipótesis. Censurar la cola incompleta. Contar al menos 200 evaluables purgados, 80 BUY, 80 SELL y tres folds por lado.
4. Generar bajo outputs/bc_train_future_eval_v1/pretraining_quarantine el paquete futuro con DATASET_HASH, bounds, membership/exposure, protocolo, whitelist, CODE_HEAD/CODE_HASH, entorno, plan y criterios de aceptación. Los hashes ausentes quedan null; no es un manifest admitido.
5. Revisar y admitir científicamente un snapshot sellado. Solo entonces preparar una única solicitud de entrenamiento con sus hashes. Las listas de autoridad vacías impiden adelantarse.
6. Tras un grant específico futuro, usar tools/admitted_training.py --grant <grant revisado>. El dispatch verifica autoridad antes del lector; revisa Git limpio, protocolo B+C, hashes, entorno, filas, purga, clases y presupuesto antes de crear estimadores.
7. Ejecutar BUY/SELL × cuatro folds, logística L2 C1/lbfgs/max_iter1000/seed20261030, escalado solo en TRAIN, ocho fits máximos, sin búsquedas ni noveno fit. Un intento fallido es terminal sin reintento científico automático.
8. Conservar modelos fold4 por lado, hashes, orden de features, código/entorno y bracket NTS de congelación. EVAL no se activa por el éxito de TRAIN; requiere autorización posterior y observaciones nuevas después de modelos y cierre de labels/purga.

Se conservan cuatro hipótesis BUY/SELL frente FOLLOW/INVERT y los criterios del contrato aprobado: 10.000 bootstraps, cuatro contrastes, límite unilateral 98,75% >0, sensibilidad bloques 451, fracción positiva ≥0,70, concentración ≤0,50 y drawdown proxy ≤1,20 baseline. Un caso degenerado es INCONCLUSIVE. No ampliar la muestra tras ver rendimiento.

Estado actual: 0 M5 nuevas, ningún dataset admitido, ningún grant, ningún fit. El plan está preparado; no debe ejecutarse ahora. Referencia vigente: [cierre integral](BC_FINAL_PRETRAINING_CLOSURE.md).
