# Desarrollo histórico amplio de IA para US30Cash M5

Estudio US30CASH_XM_HISTORICAL_AI_DEVELOPMENT_V1 registrado por separado. La autorización permite reutilizar TRAIN o DEVELOPMENT expuesto con membership verificable y fija ocho fits exploratorios como máximo. La matriz vigente habilita el día diagnóstico del 2 de enero de 2024. Los límites exactos de TRAIN legado y Historical Holdout siguen pendientes. C+F, B+C, Discovery Validation y Final Test conservan sus roles.

El diseño conserva MAIN_K 5/3/3, cruce BUY 20 y SELL 80, entrada siguiente M5 con Bid/Ask, TP 240, SL 180, TIME_EXIT 100 y FOLLOW/INVERT. El modelo inicial sería logística L2 por lado con escalado dentro de cada fold cronológico purgado. La evaluación independiente queda inactiva. El presupuesto consumido es cero.

Para avanzar hace falta un intervalo concreto de TRAIN o DEVELOPMENT con membership verificable que cubra calentamiento, decisiones y salidas. Después deben comprobarse cobertura y semillas causales, congelarse dataset y protocolo y medirse soporte por lado. El día diagnóstico permanece disponible para reproducibilidad.

[Recibos, índice de lotes y hashes](../research/studies/us30cash_xm_historical_ai_development_v1/sha256.json).
