# Solicitud de evidencia a la PC anterior

Prompt para ejecutar en el Codex local de la PC anterior de stochastic-gpt-lab:

Preparar un paquete pequeño de transferencia de evidencia, sin activar colección, scoring, FINAL_TEST, DEMO, shadow ni trading. Usar únicamente el repositorio l6i2/stochastic-gpt-lab, rama research/full-pipeline. No modificar otro proyecto ni especificaciones selladas, no reset, no credenciales en archivos o chats.

PC A ya verificó XM DEMO y US30Cash y obtuvo CLOCK_ATTESTATION=PASS en una captura simultánea de 50 frames/150 registros. No necesita repetir esa captura. Servidor observado actual: XMGlobalSC-MT5 5. El offset observado +7200 NO constituye mapping certificado.

Buscar y verificar, sin inventar:

- TRANSFER_MANIFEST.json, CLOUD_HANDOFF.json y manifiestos históricos de la cohorte; cursor/checkpoint final, cadena de hashes y rangos temporales nativos. Incluir bytes de los manifiestos y SHA-256, indicando cuáles faltan. No copiar raw cohort grande automáticamente.
- Si existe mapping nativo/UTC externo revisado: mapping.json, evidence_file, sidecars SHA-256, identidad exacta servidor/símbolos y authorized_segments acotados, además de fuente/procedencia y revisión externa. Validarlo con las herramientas del repo. No fabricar status PASS, ampliar fechas/DST ni trasladar una autorización entre servidores distintos.
- Evidencia del contrato congelado de metadata/health y sus versiones. PC A reprodujo FROZEN_METADATA_NATIVE_TRIGGER_PARITY_NOT_ESTABLISHED. No corregir datos/contadores antiguos en silencio, ni reutilizarlos como prueba de madurez del trigger nativo.

Crear un paquete de archivos pequeños con un manifiesto SHA-256 y lista explícita de ausencias y bloqueos. Excluir contraseñas, tokens, claves, identificadores de cuenta, labels, PnL y outcomes. Conservar originales intactos. Si una evidencia no existe, informar NOT_AVAILABLE; no reconstruir históricos ni abrir gates para suplirla.

El paquete permitirá revisar continuidad y mapping en PC A; no garantiza por sí solo aceptación científica. Una nueva cohorte/segmento requiere decisión explícita documentada si no se demuestra continuidad y compatibilidad de contratos.
