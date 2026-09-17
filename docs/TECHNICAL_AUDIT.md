<!-- SPDX-License-Identifier: MPL-2.0 -->

# Auditoría técnica y mapeo del prototipo

## ICCI – Espacio de debate

**Estado:** diseño técnico previo al primer cambio funcional  
**Rama:** `feat/peer-instruction`  
**Baseline upstream:** `711bdde7a7dcd2d217cfc75dbbbb2592a78582d3`

## 1. Propósito

Este documento mapea el prototipo React/Vite de Peer Instruction contra la arquitectura real de ClassQuiz y fija qué se reutiliza, qué se adapta, qué se reescribe y qué no debe portarse.

La meta del primer incremento no es crear otra aplicación paralela. Es incorporar un flujo deliberativo dentro de los mecanismos existentes de ClassQuiz, preservando compatibilidad con el upstream y dejando una base extensible para futuras metodologías.

## 2. Hallazgo principal

El prototipo adjunto es una **especificación UX/funcional**, no un fork ejecutable de ClassQuiz.

Conserva valor en:

- flujo `respuesta individual → discusión → revoto → resultados`;
- nivel de convicción;
- justificación breve;
- captura de un argumento de un par;
- experiencia móvil del estudiante;
- tablero docente;
- matriz de transiciones;
- comparación antes/después;
- pregunta de entrenamiento seguida de una pregunta sustantiva.

No deben portarse literalmente:

- React/Vite como runtime de producción;
- los pseudoarchivos `backend/models.py`, `backend/schemas.py` y `backend/sockets.py`;
- el WebSocket FastAPI independiente del prototipo;
- la migración SQL manual `001_peer_instruction.sql`;
- dependencias de Gemini/AI Studio que no participan del flujo;
- la interpretación `A → B = éxito`;
- la idea de dos cohortes A/B como supuesto estructural del dominio.

## 3. Arquitectura real encontrada en ClassQuiz

### Backend y estado vivo

ClassQuiz ya posee un servidor `python-socketio` en:

```text
classquiz/socket_server/__init__.py
```

El ciclo real incluye, entre otros, eventos para:

```text
join_game
rejoin_game
register_as_admin
start_game
set_question_number
submit_answer
get_question_results
get_final_results
show_solutions
```

Los jugadores entran a la sala identificada por `game_pin`, mientras el docente también entra en `admin:{game_pin}`. La sesión, los jugadores, las respuestas de la pregunta y el estado del juego se apoyan en Redis.

**Decisión:** ICCI no creará un segundo WebSocket, un segundo sistema de rooms ni una sesión paralela.

### Modelo de preguntas

El dominio está definido principalmente en:

```text
classquiz/db/models.py
```

`QuizQuestionType` ya incluye:

```text
ABCD
RANGE
VOTING
SLIDE
TEXT
ORDER
CHECK
```

`VOTING` ya representa una elección sin el campo `right` de una respuesta ABCD. Esto lo hace una base natural para dilemas y preguntas sin alternativa correcta.

La pregunta vive como `QuizQuestion` y los cuestionarios almacenan `questions` como JSON. El estado de ejecución se representa mediante `PlayGame`, que mantiene datos como `game_pin`, `current_question`, `started`, `question_show` y `game_mode` en Redis.

**Decisión:** no crear `PEER_INSTRUCTION` como nuevo tipo de pregunta. `VOTING` describe el **tipo de respuesta**; Peer Instruction describe el **flujo metodológico**.

### Frontend del estudiante

El flujo de juego real está en:

```text
frontend/src/routes/play/+page.svelte
frontend/src/lib/play/question.svelte
frontend/src/lib/play/join.svelte
```

`+page.svelte` ya gestiona conexión/reconexión, inicio de juego, cambio de pregunta, resultados y finalización. `question.svelte` ya renderiza `VOTING`, envía `submit_answer` y gestiona el temporizador visual.

**Decisión:** el StudentMobileSimulator del prototipo se reimplementará como componentes Svelte integrados a este flujo, no como una ruta React independiente.

### Frontend docente

Los controles y vistas docentes están concentrados en:

```text
frontend/src/lib/play/admin/
```

Incluyen:

```text
controls.svelte
game_state.ts
question.svelte
results.svelte
voting_results.svelte
socket_game_controls.ts
```

Existe además `SocketGameControls`, que ya encapsula progresivamente eventos del docente.

**Decisión:** los controles de fase de ICCI deben ampliar esta capa, evitando introducir llamadas Socket.IO dispersas por nuevas vistas.

### Migraciones

El repositorio utiliza Alembic:

```text
migrations/
migrations/versions/
```

**Decisión:** no usar SQL manual independiente. Si una iteración posterior requiere persistencia relacional nueva, deberá añadirse mediante los modelos del proyecto y una migración Alembic compatible.

## 4. Mapeo prototipo → ClassQuiz

| Prototipo | Responsabilidad | Destino real propuesto | Acción |
| --- | --- | --- | --- |
| `App.tsx` | máquina de estados R1/discusión/R2/resultados | nuevo estado de actividad en backend + UI existente | Reescribir |
| `StudentMobileSimulator.tsx` | experiencia del alumno | `frontend/src/lib/play/` + `play/+page.svelte` | Portar UX a Svelte |
| `TeacherPresenterBoard.tsx` | control docente | `frontend/src/lib/play/admin/` | Portar y simplificar |
| `TransitionMatrix.tsx` | transiciones | nuevo componente de analítica docente | Conservar concepto |
| `CohortComparison.tsx` | comparación A/B | analítica genérica por grupo/configuración | Generalizar |
| `SqlAnalyticsExplorer.tsx` | consultas demostrativas | servicio de agregación real | No portar UI técnica |
| `dilemmaData.ts` | contenido piloto | pregunta `VOTING` + configuración de actividad | Adaptar |
| `backend/sockets.py` | realtime paralelo | `classquiz/socket_server/` | Eliminar y reescribir sobre Socket.IO |
| `backend/models.py` | tablas independientes | modelos/estado ClassQuiz | No copiar |
| `backend/schemas.py` | payloads de respuesta | `classquiz/socket_server/models.py` o módulo ICCI dedicado | Reescribir |
| `001_peer_instruction.sql` | persistencia | Alembic, solo cuando sea necesaria | Eliminar |

## 5. Modelo de extensibilidad

La arquitectura debe separar tres dimensiones:

```text
Contenido       → tipo de pregunta (VOTING, TEXT, ABCD, ...)
Metodología     → flujo/fases de interacción
Presentación    → vista alumno/docente
```

Por tanto, una pregunta `VOTING` puede ejecutarse como:

```text
STANDARD
PEER_DELIBERATION
THINK_PAIR_SHARE        (futuro)
TEAM_BASED              (futuro)
STRUCTURED_DEBATE       (futuro)
```

### Configuración propuesta

Para el primer piloto, la configuración debe ser explícita y pequeña. Conceptualmente:

```text
ActivityConfig
  mode: STANDARD | PEER_DELIBERATION
  phases:
    - INITIAL_RESPONSE
    - DISCUSSION
    - SECOND_RESPONSE
    - REFLECTION
    - RESULTS
  confidence: enabled/disabled
  justification: required/optional/disabled
  peer_argument: required/optional/disabled
  group_mode: automatic | manual | whole_class
  group_size: optional integer
  discussion_seconds: integer
```

No se propone implementar todas estas variantes en v0.1.0. El modelo se define ahora para evitar decisiones irreversibles.

## 6. Estado vivo: diseño recomendado

### No sobrecargar `game_mode`

`game_mode` ya participa en la presentación del juego (`normal`, `kahoot`, etc.). No debe convertirse también en indicador metodológico.

Se debe introducir una dimensión separada, por ejemplo:

```text
interaction_mode
```

o una configuración opcional asociada a la pregunta.

### Estado de fase

El servidor debe ser autoritativo para la fase actual. Propuesta conceptual:

```text
DeliberationState
  game_pin
  question_index
  phase
  phase_started_at
  phase_deadline
  groups
```

Redis es apropiado para el estado efímero del piloto porque ClassQuiz ya lo usa para el juego activo.

Una clave posible:

```text
activity:{game_pin}:{question_index}:state
```

Las respuestas pueden mantenerse durante el piloto en una estructura separada:

```text
activity:{game_pin}:{question_index}:responses
```

Esto evita alterar prematuramente `GameResults` y permite validar la metodología antes de diseñar persistencia histórica definitiva.

## 7. Eventos Socket.IO propuestos para v0.1.0

No se reemplazan los eventos existentes. Se agregan eventos específicos y con nombres inequívocos:

```text
set_activity_phase          docente → servidor
activity_phase_changed      servidor → sala
submit_activity_response    estudiante → servidor
activity_response_saved     servidor → estudiante
activity_progress           servidor → docente
get_activity_results        docente → servidor
activity_results            servidor → docente
```

### Reglas

- solo una sesión admin puede cambiar de fase;
- el servidor valida la fase antes de aceptar una respuesta;
- una persona puede tener una respuesta por fase de respuesta;
- R1 y R2 son registros distintos, no columnas que presuponen exactamente dos rondas para siempre;
- al reconectarse, el alumno recibe la fase vigente y su progreso;
- el temporizador de discusión se deriva de un deadline del servidor, no solo de un decremento local;
- los resultados agregados del grupo no deben mostrarse al alumno antes de R2 salvo que la metodología lo configure explícitamente.

## 8. Modelo de respuesta recomendado

El prototipo utiliza campos `initial_*` y `final_*`. Para extensibilidad es mejor representar cada respuesta por fase:

```text
ActivityResponse
  participant
  question_index
  phase
  choice
  confidence
  justification
  reflection
  submitted_at
```

Ventajas:

- soporta dos o más rondas;
- permite Think–Pair–Share y metodologías futuras;
- elimina columnas `initial/final` específicas de Peer Instruction;
- simplifica una matriz de transición entre fases arbitrarias.

Para el piloto, esta estructura puede serializarse en Redis sin crear aún una tabla SQL permanente.

## 9. Cambios mínimos por área para el vertical slice

### Backend

**Modificar o extender:**

```text
classquiz/socket_server/models.py
classquiz/socket_server/__init__.py
```

**Preferencia:** si la lógica supera un tamaño pequeño, extraerla desde el inicio a un módulo nuevo, por ejemplo:

```text
classquiz/socket_server/activity.py
classquiz/socket_server/activity_models.py
```

para reducir el riesgo de convertir `socket_server/__init__.py` en un archivo aún más monolítico.

### Modelos de pregunta

Cambios potenciales y backward-compatible:

```text
classquiz/db/models.py
frontend/src/lib/quiz_types.ts
```

Agregar una configuración opcional de interacción a `QuizQuestion`, con valor por defecto equivalente al comportamiento actual.

### Estudiante

Extender:

```text
frontend/src/routes/play/+page.svelte
frontend/src/lib/play/question.svelte
```

Añadir componentes nuevos en vez de inflar `question.svelte`, por ejemplo:

```text
frontend/src/lib/play/activity/
  deliberation.svelte
  confidence.svelte
  justification.svelte
  discussion.svelte
  reflection.svelte
```

### Docente

Extender:

```text
frontend/src/lib/play/admin/game_state.ts
frontend/src/lib/play/admin/socket_game_controls.ts
frontend/src/lib/play/admin/
```

Agregar:

```text
frontend/src/lib/play/admin/activity_controls.svelte
frontend/src/lib/play/admin/activity_results.svelte
frontend/src/lib/play/admin/transition_matrix.svelte
```

## 10. Qué reutilizar del tipo `VOTING`

`VOTING` es especialmente valioso porque:

- ya está representado en backend y frontend;
- no codifica una alternativa correcta;
- ya tiene resultados docentes específicos;
- usa el mismo sistema de preguntas, respuestas, sockets y rooms del producto.

Sin embargo, **no basta** por sí mismo. El `submit_answer` actual:

- acepta una respuesta por pregunta;
- impide responder nuevamente mediante `has_already_answered`;
- calcula campos de resultado compatibles con el modelo de quiz;
- cierra la pregunta cuando todos responden.

Por eso R1/R2 no debe implementarse haciendo hacks al mismo `submit_answer`. El flujo deliberativo necesita eventos y almacenamiento de actividad propios, reutilizando identidad, room y sesión.

## 11. Analítica responsable

No existe una alternativa objetivo implícita para el dilema ético.

La analítica v0.1 debe mostrar:

```text
conteos R1
conteos R2
matriz completa R1 → R2
número que mantuvo postura
número que cambió postura
variación de convicción
argumentos/reflexiones seleccionables por el docente
```

No mostrar:

```text
“conversión exitosa”
“respuesta correcta”
“A → B = mejora”
ranking moral de estudiantes
```

Para N=3:

- mostrar `2 de 3`, no `66,7 %` como indicador principal;
- evitar inferencias estadísticas;
- no prometer anonimato cuando las respuestas pueden ser inferibles;
- usar conversación guiada de tríada/turnos en vez de agrupamiento algorítmico.

## 12. Pregunta de entrenamiento

La primera actividad debe enseñar la mecánica antes del dilema.

Ejemplo inicial:

> Para aprender cómo funciona esta actividad, ¿qué lenguaje preferirías para crear una pequeña aplicación web?

Opciones:

```text
A. Python
B. JavaScript / TypeScript
C. Java
D. Otro
```

Objetivo: aprender `elegir → convicción → justificar → conversar → reconsiderar`, no evaluar conocimiento.

## 13. Pregunta sustantiva inicial

El dilema del prototipo se conserva conceptualmente y se ajustará para neutralidad:

> Un hospital solicita desplegar un sistema de IA para priorizar intervenciones. Las pruebas muestran un desempeño alto, pero el equipo aún no puede explicar adecuadamente determinados sesgos y decisiones del modelo. La organización argumenta que retrasar el despliegue prolongará una lista de espera crítica. ¿Qué curso de acción debería recomendar el equipo profesional?

Alternativas de trabajo:

```text
A. Desplegar ahora con monitoreo reforzado.
B. Postergar el despliegue hasta completar una auditoría adicional.
C. Ejecutar un piloto acotado con supervisión humana y criterios de detención.
D. Elevar la decisión a una instancia institucional independiente antes de desplegar.
```

Ninguna alternativa se marca como correcta en el sistema.

## 14. Seguridad y privacidad para el piloto

Mínimo requerido:

- no almacenar correos ni identificadores institucionales si no son necesarios;
- usar alias/nombre de sesión como ya permite ClassQuiz;
- no publicar respuestas reales de estudiantes en el repositorio;
- no incluir secretos ni credenciales en configuración;
- validar tamaño de justificación/reflexión en servidor;
- sanitizar/renderizar texto de usuario sin HTML ejecutable;
- verificar autorización admin en cada transición de fase;
- mantener TTL para estado efímero en Redis;
- definir explícitamente qué datos sobreviven al cierre de la sesión.

## 15. Riesgos técnicos detectados

### R1 — `socket_server/__init__.py` ya concentra demasiada lógica

**Mitigación:** implementar la extensión en módulo dedicado y registrar handlers con una interfaz pequeña.

### R2 — temporizadores principalmente visuales en cliente

**Mitigación:** usar `phase_deadline` autoritativo del servidor para discusión y reconstrucción tras reconexión.

### R3 — respuestas actuales son una sola por pregunta

**Mitigación:** modelar respuestas por fase y no relajar globalmente `has_already_answered`.

### R4 — `game_mode` mezcla actualmente decisiones de presentación

**Mitigación:** crear `interaction_mode` separado.

### R5 — persistencia prematura

**Mitigación:** piloto en Redis + exportación controlada; diseñar tablas históricas después de observar qué datos realmente aportan valor docente.

### R6 — drift respecto de ClassQuiz

**Mitigación:** minimizar modificaciones sobre archivos upstream y preferir componentes/módulos nuevos con puntos de integración pequeños.

## 16. Gate 1 recomendado

El primer cambio funcional debe demostrar solamente:

```text
1 docente
3 clientes de prueba
1 pregunta VOTING configurada como PEER_DELIBERATION
R1
convicción
justificación
discusión
R2
reflexión
matriz R1→R2
reconexión básica
```

No incluye aún:

- IA generativa;
- LMS;
- notas/calificaciones;
- agrupamiento sofisticado;
- persistencia histórica avanzada;
- editor genérico de metodologías;
- estadísticas inferenciales;
- dashboards longitudinales.

## 17. Criterio de salida de esta fase

La fase de mapeo queda cerrada cuando:

- cada pieza del prototipo tiene un destino o una decisión de descarte;
- no existe un stack paralelo React/FastAPI-WebSocket;
- `VOTING` se reutiliza sin convertirlo en metodología;
- la metodología se representa como flujo configurable separado;
- Redis y Socket.IO existentes son la base del piloto;
- se conoce la superficie mínima de archivos upstream a tocar;
- se puede iniciar un vertical slice sin una migración SQL prematura.

Con estos criterios, el siguiente paso es **Gate 1: implementar el estado de actividad y el flujo mínimo R1 → discusión → R2 sobre Socket.IO y Redis existentes**.
