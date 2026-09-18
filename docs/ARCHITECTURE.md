<!-- SPDX-License-Identifier: MPL-2.0 -->

# Arquitectura objetivo

## Principio general

ICCI – Espacio de debate extiende ClassQuiz sin reemplazar su infraestructura base de sesiones, persistencia y comunicación realtime.

El objetivo técnico es introducir una capa metodológica configurable sobre el motor existente.

## Base heredada

Se preservan como fundamentos:

- FastAPI;
- ormar;
- python-socketio;
- PostgreSQL;
- Redis;
- SvelteKit;
- Tailwind CSS;
- modelo de sesión/room de ClassQuiz;
- mecanismos existentes de unión mediante PIN y comunicación realtime.

No se incorporará un segundo canal WebSocket paralelo si la capacidad puede resolverse con el sistema Socket.IO existente.

## Modelo conceptual

La extensión debe evolucionar hacia un modelo compuesto por:

```text
Activity
├── Question
├── Phase
├── Response
├── Group
├── Reflection
└── Analytics
```

### Activity

Representa una experiencia pedagógica completa y define:

- metodología;
- secuencia de fases;
- preguntas;
- configuración de grupos;
- reglas de visibilidad;
- reglas de transición;
- opciones de analítica.

### Question

Debe permitir distintos tipos de interacción sin acoplar la lógica a una sola alternativa múltiple.

Tipos candidatos:

- single choice;
- multiple choice;
- ranking;
- escala;
- respuesta breve;
- posición en un continuo;
- selección + justificación.

### Phase

Una actividad se ejecuta como una secuencia de fases configurables.

Ejemplo inicial:

```text
INTRO
→ VOTE_1
→ JUSTIFY
→ DELIBERATE
→ VOTE_2
→ REFLECT
→ RESULTS
```

Las fases deben ser explícitas y serializables para permitir nuevas metodologías sin reescribir el flujo completo.

### Response

Debe distinguir al menos:

- participante;
- pregunta;
- ronda/fase;
- alternativa o valor seleccionado;
- convicción;
- justificación;
- timestamp;
- metadatos mínimos necesarios para analítica.

### Group

El agrupamiento debe ser configurable y no obligatorio.

Modos iniciales:

- sin grupos;
- pares;
- grupos pequeños;
- grupo único/seminario.

### Reflection

La metacognición debe ser una entidad separada de la respuesta objetiva para permitir preguntas como:

- ¿qué argumento influyó más en tu razonamiento?;
- ¿qué cambió o reforzó tu posición?;
- ¿qué incertidumbre permanece?;

### Analytics

La analítica se construirá sobre eventos y respuestas, evitando codificar supuestos pedagógicos del tipo “cambiar de respuesta = éxito”.

## Realtime

Los eventos nuevos deben extender `python-socketio` y el modelo realtime ya existente.

Eventos conceptuales candidatos:

```text
activity:phase_changed
response:submitted
response:updated
group:assigned
deliberation:started
deliberation:ended
reflection:submitted
```

Los nombres finales deben mapearse contra las convenciones reales del código upstream antes de implementarse.

## Persistencia

La primera iteración debe introducir el mínimo esquema adicional necesario. No se crearán microservicios ni una base paralela.

Debe mantenerse separación clara entre:

- entidades heredadas de ClassQuiz;
- entidades nuevas de ICCI;
- archivos upstream modificados;
- archivos nuevos de extensión.

## Modos de clase

### Standard

Pensado para aproximadamente 20–35 participantes.

Características:

- grupos de 2–4;
- analítica agregada;
- transición R1 → R2;
- argumentos visibles de manera controlada.

### Seminar

Pensado para grupos muy pequeños, incluido N=3.

Características:

- sin agrupamiento automático;
- conversación única o turnos guiados;
- resultados mostrados como conteos antes que porcentajes;
- evitar inferencias estadísticas no justificadas;
- configuración explícita del nivel de anonimato posible.

## Restricciones de v0.1

No forman parte del primer vertical slice:

- integración LMS;
- cuentas institucionales;
- calificaciones;
- análisis generativo de argumentos;
- embeddings/RAG;
- microservicios nuevos;
- motor de reglas complejo;
- dashboards longitudinales avanzados.

## Criterio de diseño

Cada nueva función debe responder a una pregunta:

> ¿Esta capacidad pertenece al motor general de actividades o solo a una metodología concreta?

Si es general, debe diseñarse como componente reutilizable. Si es específica, debe permanecer encapsulada en la configuración/metodología correspondiente.
