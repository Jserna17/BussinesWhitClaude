# Auditoría gratis: "¿Cuántos pacientes está perdiendo su clínica?"

> Es la **llave para abrir la puerta** con clínicas que no nos conocen. Se prepara antes de la visita
> (15–20 min por clínica) y se entrega impresa o por WhatsApp en una sola página. El dueño ve su problema con
> datos de SU clínica, no una charla de ventas.

## 1. Cómo se arma (antes de contactar)

| # | Revisión | Cómo | Quién |
|---|---|---|---|
| 1 | **Tiempo de respuesta en WhatsApp** | Escribir como paciente un día hábil a las 7–8 p. m.: *"Hola, ¿cuánto vale una limpieza y tienen cita esta semana?"* Anotar hora de respuesta | Fundador (2 min) |
| 2 | **Ficha de Google** | Buscar la clínica en Google Maps: calificación, nº de reseñas, ¿responde reseñas?, fotos, horario | Fundador (3 min) |
| 3 | **Instagram** | Seguidores, fecha de la última publicación, publicaciones del último mes, ¿tiene link a WhatsApp? | Fundador o Claude |
| 4 | **¿Hace anuncios?** | Biblioteca de anuncios de Meta (facebook.com/ads/library) → buscar el nombre de la clínica | Fundador (1 min) |
| 5 | **Sitio web** | ¿Existe? ¿Botón de WhatsApp? ¿Precios o servicios claros? | Claude |
| 6 | **Competencia** | ¿Qué clínicas cercanas sí hacen anuncios? (Biblioteca de anuncios: "odontología Pereira") | Claude |

## 2. Puntaje (0–100)

| Área | Puntos | Criterio |
|---|---|---|
| Respuesta WhatsApp | 30 | < 5 min: 30 · < 1 h: 20 · mismo día: 10 · día siguiente o nunca: 0 |
| Google | 25 | ≥ 4,7 y ≥ 100 reseñas: 25 · ≥ 4,5 y ≥ 50: 15 · menos: 5 · sin ficha: 0 |
| Instagram | 20 | ≥ 8 publicaciones/mes: 20 · 3–7: 10 · < 3 o abandonado: 0 |
| Anuncios | 15 | Activos: 15 · no: 0 |
| Web / enlace a WhatsApp | 10 | Completo: 10 · parcial: 5 · nada: 0 |

**Lectura:** < 40 = "está perdiendo muchos pacientes" · 40–70 = "tiene base pero deja dinero en la mesa" · > 70 = "bien; el siguiente paso es escalar".

## 3. Formato de entrega (una página)

```
AUDITORÍA DE PACIENTES — [Nombre de la clínica]            Vértice · Automatización con IA
Fecha: [__]                                                 Puntaje: [__]/100

1. WhatsApp: le escribimos el [día] a las [hora]. Respuesta: [X horas / sin respuesta].
   → El 1er consultorio que responde suele quedarse con el paciente.
2. Google: [4,3] estrellas con [27] reseñas. Clínica X (a 3 cuadras): [4,8] con [210].
3. Instagram: última publicación hace [5] semanas. [2] publicaciones en el último mes.
4. Anuncios: no tiene anuncios activos. [3] clínicas de la zona sí (ej.: [nombres]).
5. Web: [no tiene botón de WhatsApp / no muestra servicios].

ESTIMADO DE PACIENTES PERDIDOS POR MES: [N] (cálculo abajo)
3 ACCIONES QUE RECOMENDAMOS:
 a) Responder en menos de 1 minuto, 24/7 (asistente IA en su WhatsApp).
 b) Anuncios "clic a WhatsApp" en Pereira y Dosquebradas.
 c) Pedir reseña a cada paciente atendido.
```

**Estimado de pacientes perdidos (conservador, explicarlo como estimado):**
mensajes por semana que reportan (preguntar en la visita) × 4 × % que escribe fuera de horario (~30 %) ×
% que se va con otra clínica por demora (~30 %). Ej.: 40 × 4 × 0,3 × 0,3 ≈ **14 pacientes/mes**.

## 4. Guion de entrega (visita en frío, 3–5 minutos)
> "Buenos días, soy Juan José, de Vértice, una empresa de aquí de Pereira. Estamos haciendo un estudio de cómo
> atienden las clínicas dentales a los pacientes nuevos y preparé uno gratis para [clínica]. ¿Está el doctor o
> el administrador? Son tres minutos."
>
> (Con el dueño) "Le escribí a su WhatsApp el martes a las 7:40 p. m. preguntando por una limpieza; la respuesta
> llegó al otro día a las 10 a. m. A esa hora, ese paciente probablemente ya había escrito a otras dos clínicas.
> Aquí está el resumen: [entregar la hoja]. Lo que hacemos es un sistema que trae pacientes nuevos con anuncios
> en Instagram y los atiende en segundos por WhatsApp, a cualquier hora, y les deja la cita agendada.
> ¿Le muestro en un minuto cómo respondería su WhatsApp?" → **demo en el celular** (Sofía con los datos de su clínica).
>
> **Cierre:** "Estoy escogiendo 2 clínicas para un piloto sin costo de instalación. ¿Le parece si el [día]
> nos sentamos 20 minutos y le muestro el plan con números para su clínica?"

**Si no está el dueño:** dejar la hoja con una tarjeta y escribir ese mismo día:
> "Hola [Nombre], soy Juan José de Vértice. Hoy dejé en su clínica un estudio de cómo están atendiendo a los
> pacientes nuevos (puntaje [__]/100). ¿Le puedo mostrar en 15 minutos cómo subirlo? 😊"

## 5. Reglas
- El mystery shopping es una consulta normal: no dejar datos falsos ni agendar citas que no se van a cumplir
  (si responden con agenda, agradecer y decir que se confirma luego).
- No publicar ni compartir la auditoría de una clínica con otra.
- Registrar cada auditoría en `prospectos/clinicas-dentales.csv` (columnas de auditoría).
