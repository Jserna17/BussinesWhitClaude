# Privacidad y tratamiento de datos (Ley 1581 de 2012) — BORRADOR

> ⚠️ **Borrador de trabajo, no es asesoría legal.** Los datos de salud son **datos sensibles** en Colombia y el tratamiento exige
> reglas estrictas. Este texto deja listo el mecanismo técnico y una base para que **el abogado lo revise y lo ajuste antes del
> primer cliente pagado** (ya está en el presupuesto, `docs/09-presupuesto.md`). Nada de esto debe usarse con una clínica real sin esa revisión.

## 1. Qué hace el sistema hoy (técnico)
| Obligación / riesgo | Cómo se cubre en el código |
|---|---|
| Informar al paciente **al primer contacto** quién trata sus datos, para qué y sus derechos | El primer mensaje a cada paciente nuevo es el **aviso de datos** (texto en `negocio.aviso_privacidad_texto`; enlace a la política de la clínica en `politica_url`). Se desactiva con `aviso_privacidad: false` en el YAML (no recomendado). |
| Poder **demostrar** que se informó | Tabla `autorizaciones` (clínica, paciente, versión, fecha). Se ve en el panel (ficha de la conversación). |
| Datos de salud **opcionales** | El aviso dice que compartirlos es opcional; Sofía no da diagnósticos ni pide datos clínicos innecesarios. |
| **Acceso**: el titular pide ver sus datos | El dueño descarga todo lo guardado de un paciente (panel → conversación → "Descargar sus datos"). Queda en el historial de cambios. |
| **Supresión**: el titular pide borrar sus datos | El dueño usa "Eliminar sus datos": borra conversaciones, mensajes, interesados, casos y la autorización; cancela citas futuras; deja las citas pasadas **sin nombre ni teléfono** y quita el teléfono del historial de cambios. |
| Solicitudes que llegan por el chat | Sofía las pasa al equipo como caso ("Solicitud sobre datos personales") y no promete que ya se hicieron. |
| Acceso solo de quien debe | Usuarios con rol (dueño / recepción / odontólogo), claves con hash, sesiones que vencen, límite de intentos, historial de quién hizo qué. |
| Seguridad en tránsito y en reposo | HTTPS obligatorio (Caddy), base de datos y respaldos con permisos solo del servicio, **respaldos cifrados** (AES-256) y copiados a otro lugar privado. |
| No guardar historia clínica | El sistema solo maneja **agenda y conversación**; no hay odontograma ni historia clínica (esas tienen reglas propias: Ley 2015 de 2020 y Res. 866 de 2021). |

**Limitaciones conocidas (decirlas al abogado):**
- Un nombre escrito dentro de un texto libre del historial de cambios (p. ej. "Creó una cita: Ana Gómez…") **no se elimina automáticamente**; se elimina
  el teléfono. Si el abogado lo exige, se agrega un barrido por nombre.
- Los respaldos antiguos conservan lo que se borró después: la política debe fijar cuánto tiempo se guardan (hoy: 14 días + domingos de 8 semanas) y aclarar que
  la supresión en respaldos ocurre al vencer esa retención.
- Las conversaciones se procesan con proveedores de IA en el exterior (**transferencia internacional**) y la transcripción de notas de voz con OpenAI: debe quedar
  en el aviso y en el contrato (sección 3).
- No hay todavía purga automática por antigüedad (ej. borrar conversaciones de más de 12 meses). Definir plazo con el abogado y automatizarlo (P1).

## 2. Texto del primer mensaje (el que envía Sofía)
> Hola 👋 Soy *{asistente}*, asistente virtual de *{clínica}*. Para atenderte usamos tus datos (nombre, teléfono y lo que nos cuentes) solo para responderte y
> gestionar tu cita, y los procesamos con herramientas de inteligencia artificial. Compartir datos de salud es opcional. Puedes pedir verlos, corregirlos o
> borrarlos cuando quieras, escribiéndonos aquí. Nuestra política de datos: {enlace}

*Preguntas para el abogado:* ¿basta continuar la conversación como "conducta inequívoca" de autorización, o para datos sensibles se necesita una respuesta
afirmativa explícita (p. ej. un botón "Acepto")? Si se requiere, se cambia el flujo: Sofía pide el "Acepto" antes de recoger datos de salud.

## 3. Cláusulas para el contrato con la clínica (encargado del tratamiento)
1. **Roles.** La clínica es **responsable** del tratamiento de los datos de sus pacientes; Vértice actúa como **encargado** y solo trata los datos por instrucción de la clínica
   y para prestar el servicio (atención por WhatsApp, agenda, recordatorios, reportes).
2. **Datos tratados.** Nombre, teléfono, contenido de las conversaciones, citas y, de forma incidental, datos de salud que el paciente decida compartir.
3. **Subencargados autorizados.** Meta (WhatsApp Business Platform), proveedor del modelo de IA (OpenAI y/o Anthropic), proveedor del servidor (indicar), proveedor de copias
   de seguridad (indicar). Vértice informa a la clínica antes de cambiarlos.
4. **Transferencia internacional.** La clínica autoriza el envío de los datos necesarios a los subencargados ubicados fuera de Colombia, que deben ofrecer niveles adecuados de protección.
5. **Seguridad.** Acceso por usuario y clave, roles, registro de cambios, cifrado en tránsito, respaldos cifrados, acceso restringido al servidor, monitoreo.
6. **Confidencialidad.** Las personas de Vértice con acceso están obligadas a la reserva. El acceso de soporte a la cuenta de la clínica queda registrado en el historial.
7. **Derechos de los titulares.** Vértice entrega a la clínica las herramientas para atender solicitudes de acceso, corrección y supresión (panel) y la ayuda en un plazo razonable.
8. **Incidentes.** Vértice avisa a la clínica sin demora indebida ante cualquier incidente de seguridad que afecte sus datos, con la información disponible, para que decida si lo reporta
   a la Superintendencia de Industria y Comercio.
9. **Terminación.** Al terminar el servicio, Vértice entrega a la clínica una copia de sus datos y los elimina del sistema y de los respaldos al vencer su retención (indicar plazo).
10. **Auditoría.** La clínica puede pedir información razonable sobre las medidas de seguridad.

## 4. Política de tratamiento de datos de la clínica (la que enlaza el aviso)
La política es **de la clínica** (responsable) y debe estar publicada (sitio web, Instagram o un PDF). Vértice puede ayudar a redactar el borrador: finalidades (agendar, recordar, atender,
mejorar el servicio), datos sensibles y su carácter opcional, derechos de los titulares y cómo ejercerlos (canal y responsable de atenderlos), tiempo de conservación, transferencia
internacional y vigencia. Recordar a la clínica el **Registro Nacional de Bases de Datos (RNBD)** si le aplica por tamaño (verificar con el abogado).

## 5. Lista de verificación antes de encender a una clínica
- [ ] Contrato de servicio con las cláusulas de la sección 3, firmado.
- [ ] Política de datos de la clínica publicada y su enlace en `politica_url` del YAML.
- [ ] El abogado revisó el texto del primer mensaje.
- [ ] Se acordó la persona de la clínica que atiende solicitudes de datos (la que tiene el rol dueño).
- [ ] Respaldos cifrados, copiados a otro lugar y **prueba de restauración hecha** (`python -m vertice.respaldo verificar`).
- [ ] Servidor con HTTPS, `VERTICE_ENTORNO=produccion` y todos los secretos configurados.
