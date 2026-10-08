# Políticas de Onboarding Digital (documento de ejemplo)

## 1. Verificación de identidad
- Todo prospecto debe validar su identidad contra el registro civil.
- Si la confianza de la verificación es menor a 0.80, el caso se escala a validación
  biométrica asistida o revisión manual por un oficial de onboarding.
- Si la identidad no coincide con el registro civil, la solicitud se rechaza.

## 2. Listas de riesgo (KYC / AML)
- Se consultan listas OFAC, PEP y listas internas del banco.
- Riesgo bajo: continúa el flujo normal.
- Riesgo medio (p. ej. PEP): se permite el onboarding con debida diligencia reforzada,
  incluyendo declaración de origen lícito de fondos.
- Riesgo alto (p. ej. coincidencia OFAC): el caso se escala al Oficial de Cumplimiento.
  No se informa al cliente el motivo específico.

## 3. Productos
- cuenta_ahorros: mayor de edad, cédula vigente, planilla de servicio básico.
- cuenta_corriente: además, certificado de ingresos y referencia bancaria.
- tarjeta_credito: además, certificado de ingresos, declaración de impuestos y
  autorización de consulta al buró de crédito. Requiere riesgo bajo.
- Productos no listados no están disponibles por canal digital.

## 4. Respuesta al cliente
- La respuesta debe ser clara, cordial e indicar los siguientes pasos.
- En casos escalados se informa que la solicitud está en revisión y el plazo estimado
  (48 horas hábiles).
