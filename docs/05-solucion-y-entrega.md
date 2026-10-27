# 05 · Solución técnica y entrega

## 1. Arquitectura del producto

```
Paciente ──WhatsApp──▶ API oficial de WhatsApp (vía BSP)
                              │
                              ▼
                   Plataforma de agente / orquestador
                   (n8n o Make + LLM: Claude API)
                     │            │            │
                     ▼            ▼            ▼
             Base de conocimiento  Calendario   CRM / hoja
             (precios, servicios,  (Google Cal  (leads, citas,
              FAQ de la clínica)    o software   reactivación)
                                    de la clínica)
                              │
                              ▼
                 Traspaso a humano cuando el caso lo requiere
```

## 2. Stack recomendado (validar costos en el país)

> ⚠️ **Actualizado 2026-10-27:** se decidió construir un **agente propio con la Claude API + Cloud API de Meta**
> (sin plataforma paga por cliente). n8n queda solo como puente opcional. Ver análisis completo en
> `docs/11-stack-tecnico-agentes-2026.md`. La tabla de abajo queda como referencia.

| Capa | Opción A (rápida, no-code) | Opción B (más control/margen) |
|---|---|---|
| API WhatsApp (BSP) | 360dialog, Twilio, o alternativas LATAM (ezcontact, Chattigo) | Cloud API directa de Meta |
| Orquestación | Make / Zapier | n8n autohospedado |
| Cerebro del agente | Claude API (modelo rápido/barato para chat; modelo superior para casos complejos) | Igual |
| Agenda | Google Calendar / Calendly | API del software de la clínica |
| CRM | Google Sheets → HubSpot | HubSpot / Notion |
| Reportes | Google Sheets + artifact/dashboard | Igual |

**Principio:** empezar con la opción A para los pilotos; migrar a B cuando haya 10+ clientes (más margen).

## 3. Onboarding del cliente (72 horas)

| Hora | Paso | Responsable |
|---|---|---|
| 0 | Firma + pago del setup → formulario de onboarding (servicios, precios, horarios, FAQ, tono) | Cliente |
| 0–24 | Construir base de conocimiento y flujos; conectar calendario | Claude |
| 24–48 | Pruebas internas con 30 conversaciones simuladas (incluye casos difíciles) | Claude |
| 48 | Llamada de 30 min: revisión con el cliente, ajustes | Fundador |
| 72 | Puesta en marcha + mensaje de bienvenida + entrega de guía de uso | Ambos |

Checklist de onboarding → `plantillas/onboarding-checklist.md`.

## 4. Operación mensual (por cliente)
- **Semanal:** revisar 20 conversaciones al azar; corregir respuestas; añadir FAQ nuevas.
- **Mensual:** campaña de reactivación; reporte de resultados (mensajes, leads, citas, ingresos estimados, ROI);
  llamada de 15 min de revisión y propuesta de mejora/upsell.
- **Alertas:** caída del número, errores de agenda, quejas → respuesta < 4 h hábiles.

## 5. Retención (la clave del MRR)
1. **Mostrar el ROI cada mes** — el reporte dice "este mes generamos 23 citas ≈ USD 1.840".
2. **Victoria rápida en la semana 1** — enviar captura de la primera cita agendada fuera de horario.
3. **Mejoras continuas** — cada mes algo nuevo (nuevo flujo, campaña, mejora).
4. **Detectar riesgo de churn** — uso bajo, cliente no abre reportes, pagos tarde → llamada proactiva.
5. **Contratos de 3 meses mínimo + pago anual con descuento.**
6. **Comunidad/beneficios** — grupo de clientes, plantillas extras, prioridad en nuevas funciones.

Meta: churn < 5 % mensual (vida media > 20 meses).

## 6. Calidad y seguridad
- El agente **nunca** da diagnósticos médicos ni promete resultados clínicos; deriva a humano.
- Consentimiento y política de privacidad para datos de pacientes (ver `docs/06-administracion.md` §5).
- Plantillas de mensajes salientes aprobadas por Meta; respetar opt-out.
- Registro de todas las conversaciones para auditoría y mejora.

## 7. Demo de ventas (prioridad #1 técnica)
Construir una "Clínica Demo" con base de conocimiento ficticia y un número de prueba; en cada llamada
de ventas se carga la info real del prospecto (sacada de su Instagram/web) para que vea SU agente funcionando.
