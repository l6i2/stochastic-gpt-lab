# Decisión pendiente sobre reservas futuras

Estado: **NO APROBADA NI APLICADA**. La adquisición C+F continúa en cuarentena.

Estudio `US30CASH_M5_NATIVE_OBSERVATIONS_20261105_01`, contrato
`CF_NATIVE_OBSERVATIONS_CONTRACT_V1_20261105`, productor
`cfprod_5c64f0781dc148e5896391b1492ba144`, dataset
`us30cash_m5_native_observations_20261105_01_dataset_01`.
La autoridad metodológica está en `authorization.json`; la propuesta aprobada
tiene SHA256 `12bc6001b1e3a77523a1224cb55e9bba52b53b35759e9c2b0433de9485af0d55`.

La fecha nueva y la identidad separada prueban procedencia propia, pero no
exclusividad frente a reservas anteriores con extremo desconocido. No se
abrieron conjuntos protegidos ni se reconstruyeron manifests inexistentes.

Se solicita **una sola decisión**: autorizar un corte exclusivamente prospectivo,
registrado mediante un recibo temporal nuevo después de esa autorización, que
cierre las incorporaciones futuras de US30Cash de PC A a las reservas anteriores
y asigne exclusivamente al estudio C+F los nuevos intervalos a partir de ese corte.
El corte debe delimitar los roles de TODAS las reservas previas, incluso las de
extremo desconocido, para los intervalos nuevos de este símbolo; cambiar únicamente
el ID del productor no elimina un solapamiento temporal entre estudios.

Esta decisión preservaría íntegros datos, hashes, checkpoints, reservas y derechos
de acceso anteriores al corte. No liberaría ni expondría ningún conjunto protegido.
Los registros C+F anteriores al nuevo corte seguirían en cuarentena y no contarían
como warmup ni como datos independientes del nuevo rol exclusivo. Se iniciaría un
epoch propio y un ledger de asignación sin backfill, con las semillas dentro del
nuevo intervalo. La reserva histórica desconocida seguiría siendo desconocida.

No se solicita entrenar, hacer scoring, reducir umbrales ni aprobar admisión.
Si no se aprueba este alcance, se necesitan los límites verificables originales
de todas las reservas y la reconciliación de sus dominios temporales para probar
no solapamiento. Ninguna de estas alternativas está aplicada por este documento.
