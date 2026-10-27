# 04 · Marketing

## 1. Marca (propuesta, pendiente de aprobación)

- **Nombres candidatos:** *Agenda Viva*, *CitaBot*, *RecepcionIA*, *Respondo*, *Clinia* (verificar dominios con el conector de Shopify).
- **Promesa:** "Ningún paciente sin respuesta."
- **Tono:** cercano, claro, sin tecnicismos; hablamos de citas y dinero, no de "LLMs".
- **Pilares de mensaje:**
  1. Velocidad = ventas (quien responde primero, agenda).
  2. Menos inasistencias, más ingresos.
  3. Tu equipo se enfoca en atender, no en contestar el chat.
  4. Hecho por ti, en 72 horas, con garantía.

## 2. Activos mínimos (semanas 1–2)

| Activo | Herramienta | Responsable |
|---|---|---|
| Logo y kit de marca | Canva (conector) | Claude |
| Landing page de 1 sección + calculadora de pérdidas | Higgsfield website builder / Artifact | Claude |
| Perfil de Instagram + LinkedIn del fundador optimizados | Manual | Fundador con textos de Claude |
| Video demo de 60–90 s | Grabación de pantalla + Higgsfield | Claude + fundador |
| Caso de estudio (tras primer piloto) | skill `marketing:content-creation` | Claude |

## 3. Estrategia de contenido orgánico (canal 2 de Core Four)

**Plataformas:** Instagram/TikTok (Reels) + LinkedIn del fundador.
**Frecuencia:** 1 pieza/día hábil (Claude genera el lote semanal).

| Tipo | % | Ejemplos |
|---|---|---|
| Educativo | 40 % | "3 mensajes que hacen que un paciente no vuelva a escribir" |
| Demostración | 30 % | Pantalla grabada: el agente agenda una cita a las 11 pm |
| Prueba social | 20 % | Resultados de clientes, testimonios |
| Detrás de cámaras | 10 % | Construyendo el negocio con IA (marca personal del fundador) |

**Regla de dar/pedir:** ~3–4 piezas de valor por cada llamado a la acción.
**Lead magnet:** "Auditoría gratis: te escribimos como paciente y te mostramos cuántas citas pierdes."

## 4. Email / WhatsApp nurture

Secuencia de 5 mensajes para leads que no cerraron (skill `marketing:email-sequence`):
1. Día 0: grabación de la demo + resumen del diagnóstico.
2. Día 2: caso de estudio.
3. Día 5: objeción más común resuelta (precio/IA "fría").
4. Día 9: dato de pérdidas del sector.
5. Día 14: última plaza del mes.

## 5. Anuncios pagados (canal 4 — desde mes 3, solo si cierre en frío ≥ 25 %)

- **Meta Ads** (Instagram/Facebook) segmentado a dueños de clínicas / intereses odontología y estética.
- Presupuesto inicial: USD 10–20/día; objetivo: agendar llamadas de diagnóstico.
- Creativos: skills `ads-image-architect`, `estratega-avatarhype` (guiones UGC), `vox-animated-ad`.
- KPI: costo por llamada agendada < USD 40.

## 6. Calendario de marketing del trimestre
| Mes | Foco |
|---|---|
| 1 | Marca + landing + demo + outreach; contenido 3×/semana |
| 2 | Casos de estudio de pilotos; contenido diario; programa de referidos |
| 3 | Prueba de anuncios; webinar/live "IA para clínicas"; alianzas |

## 7. Skills de esta sesión útiles para marketing
`marketing:campaign-plan`, `marketing:content-creation`, `marketing:draft-content`, `marketing:email-sequence`,
`marketing:competitive-brief`, `marketing:seo-audit`, `marketing:brand-review`, `marketing:performance-report`,
`anthropic-skills:ads-image-architect`, `anthropic-skills:estratega-avatarhype`, `anthropic-skills:ugc-prompt-engineer`,
`anthropic-skills:vox-animated-ad`. Detalle en `docs/07-herramientas-skills-conectores.md`.
