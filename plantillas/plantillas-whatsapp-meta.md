# Plantillas de WhatsApp para enviar a Meta (aprobación obligatoria)

> WhatsApp solo deja escribirle a un paciente **por iniciativa de la clínica** (recordatorios, avisos) o **pasadas 24 h**
> desde su último mensaje usando una **plantilla aprobada por Meta**. Sin esta plantilla el recordatorio no sale.
> **Acción del fundador** (una sola vez por clínica, cuando exista la cuenta de WhatsApp Business Platform):
> crearla en *WhatsApp Manager → Plantillas de mensajes → Crear plantilla* y esperar la aprobación (suele tardar de minutos a 24 h).
> Claude no la envía: requiere la cuenta de Meta de la clínica.

## 1. `recordatorio_cita` (la que usa el sistema hoy)

| Campo | Valor |
|---|---|
| Nombre | `recordatorio_cita` (exactamente así, minúsculas y guion bajo) |
| Categoría | **Utilidad** (no Marketing: es un aviso de una cita ya agendada) |
| Idioma | Español (`es`) |
| Encabezado / pie | Ninguno |

**Cuerpo:**

```
Hola {{1}} 👋 Te recordamos tu cita en {{2}}: {{3}}, {{4}}. ¿Nos confirmas tu asistencia?
```

**Ejemplos de variables (Meta los pide):**

| Variable | Qué lleva | Ejemplo |
|---|---|---|
| {{1}} | Nombre del paciente | Carolina |
| {{2}} | Nombre de la clínica | Clínica Dental Sonríe |
| {{3}} | Servicio | Limpieza dental (profilaxis) |
| {{4}} | Cuándo | mañana a las 2:00 p. m. |

**Botones (tipo "Respuesta rápida", en este orden):**
1. `Sí, confirmo`
2. `Necesito cambiarla`

> El sistema envía el id de la cita dentro de cada botón. Al tocarlos, el paciente queda confirmado en el panel, o Sofía le ayuda a
> reprogramar. **El orden de los botones importa:** el primero confirma y el segundo cambia.

## 2. Consejos para que la aprueben a la primera
- Categoría **Utilidad** y un texto claro de recordatorio. Evita palabras de promoción (descuento, oferta, gratis).
- Variables con ejemplos reales, sin espacios extra y sin saltos de línea dentro de una variable.
- No empezar ni terminar el cuerpo con una variable.
- Si la rechazan, Meta indica el motivo: se corrige el texto y se vuelve a enviar (el nombre de una plantilla rechazada no se
  puede reutilizar tal cual: crear `recordatorio_cita_2` y poner ese nombre en `plantilla_recordatorio` del YAML de la clínica).

## 3. Cómo se comporta el sistema (para explicarlo a la clínica)
- Dos avisos por cita: **el día anterior** (entre 8 a. m. y 8 p. m., si se agendó con más de un día de anticipación) y **2 horas antes**
  (entre 7 a. m. y 8 p. m., si la cita se agendó con 6 h o más de antelación).
- Nunca se envía de noche, nunca dos veces el mismo aviso, y se omiten las citas de recepción sin número de WhatsApp.
- Si Meta rechaza el envío (p. ej. plantilla no aprobada), el sistema lo reintenta cada 5 minutos mientras siga en la ventana y lo deja
  en el registro del servidor. (El aviso al equipo de fallos repetidos llega con el monitoreo, P0-8.)
- Costo: cada recordatorio es un mensaje de plantilla de la categoría Utilidad; consultar la tarifa vigente de Meta para Colombia antes de
  prometer un costo a la clínica.

## 4. Plantillas siguientes (cuando haga falta; no son imprescindibles ahora)
- **Aviso de cita reprogramada** (cuando la clínica mueve una cita y el paciente no ha escrito en 24 h).
- **Reactivación de pacientes antiguos** (categoría Marketing; requiere consentimiento del paciente y cobra más).
- **Seguimiento postratamiento / reseña de Google** (Utilidad o Marketing según el texto).
