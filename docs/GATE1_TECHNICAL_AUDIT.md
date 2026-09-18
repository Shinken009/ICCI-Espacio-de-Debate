<!-- SPDX-License-Identifier: MPL-2.0 -->

# Gate 1 — Auditoría técnica y mapeo del prototipo

Estado: **auditoría de integración previa a implementación**  
Rama: `feat/peer-instruction`  
Baseline upstream: `711bdde7a7dcd2d217cfc75dbbbb2592a78582d3`

## 1. Conclusión ejecutiva

El prototipo React/Vite no debe convertirse en la base productiva. Su valor principal es de especificación UX y pedagógica. La implementación debe extender el flujo de juego real de ClassQuiz, reutilizando:

- las salas Socket.IO por `game_pin`;
- la sesión de administrador y jugador;
- Redis para estado vivo de una sesión;
- el frontend SvelteKit existente;
- los tipos de pregunta y componentes de juego existentes;
- el mecanismo de reconexión del alumno.

La restricción técnica principal encontrada es que ClassQuiz modela actualmente **una única respuesta por estudiante y pregunta**. `submit_answer` valida `has_already_answered(...)`, por lo que el flujo R1 → deliberación → R2 requiere introducir explícitamente el concepto de **fase/ronda**. Reabrir una pregunta sin cambiar el modelo de respuesta produciría `already_replied`.

La primera implementación no debe crear un segundo servidor WebSocket ni una máquina de estados paralela.

---

## 2. Arquitectura real relevante de ClassQuiz

### Backend

Puntos de integración principales:

- `classquiz/socket_server/__init__.py`
  - `join_game`
  - `rejoin_game`
  - `register_as_admin`
  - `start_game`
  - `set_question_number`
  - `submit_answer`
  - `get_question_results`
  - `show_solutions`
  - `get_final_results`
- `classquiz/socket_server/models.py`
  - contratos Pydantic para join, rejoin y submit;
  - `SubmitAnswerData` hoy contiene `question_index`, `answer` y `complex_answer`.
- `classquiz/db/models.py`
  - `QuizQuestionType`;
  - `QuizQuestion`;
  - `PlayGame`;
  - `GameSession`;
  - `AnswerData` / `AnswerDataList`.

### Estado vivo

ClassQuiz conserva estado temporal en Redis, incluyendo:

```text
game:{game_pin}
game_session:{game_pin}
game_session:{game_pin}:{question_index}
game_session:{game_pin}:players
game_session:{game_pin}:players:{username}
game_session:{game_pin}:player_scores
game:{game_pin}:current_time
```

Esto permite implementar la deliberación inicialmente sin introducir otra infraestructura de estado.

### Frontend

Puntos principales:

- `frontend/src/routes/play/+page.svelte`
  - superficie del estudiante;
  - escucha `joined_game`, `rejoined_game`, `set_question_number`, `question_results`, `solutions`, `final_results`;
  - conserva reconexión mediante cookie `joined_game`.
- `frontend/src/lib/play/question.svelte`
  - render de pregunta y envío de `submit_answer`;
  - ya soporta `ABCD`, `VOTING`, `RANGE`, `TEXT`, `ORDER` y otros tipos.
- `frontend/src/lib/play/admin/`
  - superficie docente;
  - `question.svelte` muestra pregunta y conteo de respuestas;
  - `results.svelte` / `voting_results.svelte` muestran resultados;
  - `socket_game_controls.ts` encapsula acciones como `start_game`, `set_question_number`, `get_question_results`, `show_solutions` y `get_final_results`;
  - `game_state.ts` concentra estado de la interfaz docente.

Esta separación encaja con ICCI: **docente controla fases; estudiantes responden y deliberan**.

---

## 3. Lo que ya existe y debe reutilizarse

| Necesidad ICCI | ClassQuiz actual | Decisión |
|---|---|---|
| PIN de sesión | `game_pin` + Redis | Reutilizar |
| ingreso BYOD | `/play` + `join_game` | Reutilizar |
| reconexión | `rejoin_game` + cookie | Reutilizar |
| sala realtime | Socket.IO room por PIN | Reutilizar |
| rol docente | `register_as_admin` + room `admin:{pin}` | Reutilizar |
| selección de pregunta | `set_question_number` | Extender |
| respuesta individual | `submit_answer` | Extender |
| conteo de respuestas | `player_answer` / `answer_count` | Extender |
| resultados agregados | `get_question_results` | Extender |
| votación sin respuesta correcta | `QuizQuestionType.VOTING` | Base preferida para el piloto |
| visualización docente | `lib/play/admin/*` | Extender |
| tipos de pregunta | `QuizQuestionType` | Conservar; evitar crear tipos innecesarios |
| persistencia del quiz | PostgreSQL JSON en `Quiz.questions` | Reutilizar inicialmente |
| estado de la sesión | Redis | Reutilizar inicialmente |

---

## 4. Mapeo del prototipo React/Vite

| Prototipo | Función conceptual | Destino ClassQuiz | Acción |
|---|---|---|---|
| `TeacherPresenterBoard.tsx` | tablero del docente | `frontend/src/lib/play/admin/*` | **Portar UX**, no código React |
| `StudentMobileSimulator.tsx` | experiencia del alumno | `frontend/src/routes/play/+page.svelte` + `lib/play/question.svelte` | **Portar UX** |
| `DashboardAnalytics.tsx` | comparación R1/R2 | nuevo módulo de analítica docente sobre `admin/results` | **Reescribir** |
| `MethodologyGuide.tsx` | instrucciones de dinámica | nuevo panel/instrucción por fase | **Portar contenido** |
| `ArchitectureBoard.tsx` | explicación técnica | `docs/` | **Convertir en documentación**, no runtime |
| `DiffViewer.tsx` | demostración de cambios | ninguno | **Eliminar del producto** |
| `grouping.ts` | asignación de grupos | helper ICCI opcional | **Rediseñar**; no necesario para N=3 |
| `dilemmaData.ts` | contenido piloto | fixture/ejemplo de actividad | **Conservar conceptualmente** |
| snippets FastAPI/WebSocket | backend simulado | `classquiz/socket_server/*` | **Descartar** |
| React/Vite shell | runtime del prototipo | SvelteKit existente | **Descartar** |
| AI Studio / Gemini metadata | scaffolding no utilizado | ninguno | **Eliminar** |

---

## 5. Problema de diseño central: una respuesta no es una deliberación

El modelo actual de ClassQuiz se organiza por:

```text
question_index -> AnswerDataList
```

Y `AnswerData` contiene:

```text
username
answer
right
time_taken
score
```

Para ICCI necesitamos distinguir como mínimo:

```text
question_index
round / phase
username
answer
confidence
justification
submitted_at
```

`right`, `time_taken` y `score` no deben ser las variables centrales de un dilema deliberativo.

### Decisión propuesta para v0.1

No modificar todavía toda la semántica de ClassQuiz. Crear una extensión acotada de sesión para actividades deliberativas.

Modelo conceptual:

```text
DeliberationSessionState
  activity_mode: "deliberation"
  current_phase: WARMUP | R1 | DISCUSSION | R2 | REFLECTION | RESULTS
  current_question: int
  round: 1 | 2
  group_mode: auto | manual | plenary
```

Respuesta deliberativa:

```text
DeliberationResponse
  username: str
  question_index: int
  round: 1 | 2
  answer: str
  confidence: int | null
  justification: str | null
  submitted_at: datetime
```

Para el piloto estas respuestas pueden almacenarse en Redis con claves separadas por ronda:

```text
icci:{game_pin}:question:{question_index}:round:1
icci:{game_pin}:question:{question_index}:round:2
```

Esto evita romper el formato legacy `game_session:{pin}:{question}` durante el primer vertical slice.

### Por qué no reutilizar simplemente la misma clave

Porque:

1. ClassQuiz rechaza respuestas duplicadas del mismo usuario;
2. perderíamos R1 al almacenar R2;
3. no podríamos construir una matriz individual R1→R2;
4. mezclar scoring competitivo con deliberación introduciría semántica incorrecta.

---

## 6. Máquina de estados objetivo del piloto

No crear una máquina de estados general de metodologías todavía. El vertical slice debe validar primero un flujo mínimo:

```text
LOBBY
  ↓
WARMUP_R1
  ↓
WARMUP_DISCUSSION
  ↓
WARMUP_R2
  ↓
MAIN_R1
  ↓
MAIN_DISCUSSION
  ↓
MAIN_R2
  ↓
REFLECTION
  ↓
RESULTS
```

Internamente puede abstraerse como fases configurables después del piloto.

### Acciones del docente

El docente debe poder:

- abrir R1;
- cerrar respuestas;
- revelar solo la distribución si la metodología lo requiere;
- iniciar deliberación;
- abrir R2;
- cerrar R2;
- mostrar comparación neutral;
- abrir reflexión final.

### Eventos Socket.IO sugeridos

Mantener el namespace/servidor actual y añadir eventos específicos y explícitos:

```text
admin_set_deliberation_phase
submit_deliberation_response
deliberation_phase_changed
deliberation_response_count
deliberation_results
```

No reutilizar `submit_answer` de forma ambigua para la primera versión: su semántica actual incluye validación de respuesta correcta y scoring.

---

## 7. Superficie estudiante

`frontend/src/routes/play/+page.svelte` ya actúa como orquestador de estados del jugador. Para v0.1 conviene añadir una rama de render según `activity_mode` en vez de reemplazar el flujo normal.

Componentes propuestos:

```text
frontend/src/lib/play/deliberation/
  DeliberationQuestion.svelte
  ConfidenceSelector.svelte
  JustificationField.svelte
  DiscussionPrompt.svelte
  ReflectionPrompt.svelte
```

Flujo móvil:

```text
pregunta
→ alternativa
→ convicción 1–5
→ justificación breve
→ enviado
→ espera/instrucción de conversación
→ R2
→ reflexión
```

### Restricciones UX

- un CTA principal por pantalla;
- controles táctiles grandes;
- feedback inmediato de envío;
- preservar respuesta local ante reconexión accidental cuando sea posible;
- no mostrar “correcto/incorrecto” en actividades deliberativas;
- no presentar cambio de postura como logro.

---

## 8. Superficie docente

ClassQuiz ya dispone de una carpeta administrativa especializada y de `SocketGameControls`. ICCI debe extenderla, no construir un dashboard independiente.

Componentes sugeridos:

```text
frontend/src/lib/play/admin/deliberation/
  DeliberationControls.svelte
  ResponseProgress.svelte
  RoundDistribution.svelte
  TransitionMatrix.svelte
  ConfidenceChange.svelte
  ArgumentReview.svelte
  SmallCohortResults.svelte
```

`game_state.ts` puede evolucionar para incorporar un subestado deliberativo, evitando añadir decenas de variables sueltas a componentes Svelte.

---

## 9. Analítica responsable

### No implementar

```text
A → B = éxito
"conversión"
"convencidos por sus pares"
ranking por cambio de postura
score por respuesta ética
```

### Implementar

Para grupos normales:

- distribución R1;
- distribución R2;
- matriz completa de transición;
- mantuvo/cambió postura;
- variación de convicción;
- convergencia/divergencia descriptiva;
- argumentos seleccionados para discusión;
- reflexión final.

Para `N=3`:

- usar conteos: `2 de 3`, no porcentajes como representación principal;
- no inferir tendencias estadísticas;
- no prometer anonimato si la posición puede ser reidentificada;
- conversación plenaria guiada, sin agrupamiento automático;
- mostrar las tres trayectorias solo al docente y únicamente si es pedagógicamente necesario.

---

## 10. Contenido del vertical slice

### Pregunta 0 — entrenamiento

Objetivo: aprender el ciclo, no medir conocimientos.

> Para una aplicación web pequeña que tuvieras que prototipar hoy, ¿qué opción preferirías usar como lenguaje principal?

- Python
- JavaScript/TypeScript
- Java
- Otro

Ciclo:

```text
R1 → convicción → razón breve → conversación → R2
```

No existe respuesta correcta.

### Pregunta 1 — dilema sustantivo

> Un sistema de IA desarrollado por tu equipo puede proponer y ejecutar modificaciones sobre infraestructura crítica. Los resultados de prueba son altos, pero las decisiones internas todavía no pueden auditarse adecuadamente. La organización solicita desplegarlo.

Opciones iniciales:

- A. Desplegar ahora con monitoreo reforzado.
- B. Postergar hasta alcanzar mayor auditabilidad.
- C. Realizar un despliegue progresivo con supervisión humana.
- D. No autorizar el despliegue actual y escalar formalmente la objeción.

Las alternativas se presentan como posiciones para argumentar, no como clave de respuesta.

---

## 11. Qué NO debe entrar en v0.1

- IA generativa para juzgar argumentos;
- Gemini/OpenAI;
- LMS;
- calificaciones;
- cuentas institucionales adicionales;
- rúbricas complejas;
- microservicios;
- motor genérico de workflows;
- algoritmo sofisticado de formación de grupos;
- persistencia longitudinal de analítica identificable;
- refactor amplio del core de ClassQuiz.

---

## 12. Orden de implementación recomendado

### Gate 2A — contrato de datos

1. introducir modelos Pydantic deliberativos;
2. definir claves Redis;
3. añadir fase/ronda al estado de sesión ICCI;
4. tests unitarios del modelo y transición de fases.

### Gate 2B — realtime

1. `admin_set_deliberation_phase`;
2. `submit_deliberation_response`;
3. validación de una respuesta por `username + question + round`;
4. reconexión y restauración de fase;
5. conteo de respuestas por ronda.

### Gate 2C — estudiante

1. flujo de pregunta;
2. convicción;
3. justificación;
4. pantalla de discusión;
5. R2;
6. reflexión.

### Gate 2D — docente

1. controles de fase;
2. progreso de respuestas;
3. distribución R1/R2;
4. transición neutral;
5. modo `small_cohort`.

### Gate 2E — piloto

1. fixture de entrenamiento;
2. fixture de dilema;
3. prueba con 3 clientes;
4. prueba con 20–35 clientes simulados;
5. ensayo de reconexión;
6. verificación móvil;
7. checklist de privacidad y datos ficticios.

---

## 13. Criterios de aceptación para iniciar implementación

**PASS** si:

- el flujo ICCI reutiliza Socket.IO actual;
- `master` upstream continúa limpio;
- la funcionalidad queda aislada detrás de `activity_mode` o equivalente;
- un alumno puede responder R1 y R2 sin perder ninguna ronda;
- R1 y R2 pueden correlacionarse por participante durante la sesión;
- no se asigna scoring competitivo a una actividad deliberativa;
- la reconexión conserva la fase actual;
- el docente puede controlar explícitamente cada cambio de fase;
- N=3 tiene presentación específica;
- el código normal de ClassQuiz continúa operando.

**NO-GO** si la implementación requiere duplicar el servidor realtime, romper el modelo normal de quiz o mezclar respuestas deliberativas con scoring competitivo sin separación semántica.

---

## 14. Archivos que probablemente serán tocados en Gate 2

### Backend

```text
classquiz/socket_server/__init__.py
classquiz/socket_server/models.py
classquiz/db/models.py              # solo si la configuración persistente lo exige
classquiz/socket_server/helpers.py  # solo helpers acotados
```

Preferencia: añadir módulos ICCI específicos para limitar drift, por ejemplo:

```text
classquiz/socket_server/deliberation.py
classquiz/socket_server/deliberation_models.py
```

### Frontend

```text
frontend/src/routes/play/+page.svelte
frontend/src/lib/play/question.svelte                # cambios mínimos
frontend/src/lib/play/admin/game_state.ts
frontend/src/lib/play/admin/socket_game_controls.ts  # o controlador ICCI separado
```

Nuevos módulos preferidos:

```text
frontend/src/lib/play/deliberation/
frontend/src/lib/play/admin/deliberation/
```

---

## 15. Riesgos técnicos

### Drift con upstream

**Riesgo:** modificar demasiado `socket_server/__init__.py` o componentes centrales genera conflictos futuros.  
**Mitigación:** delegar lógica ICCI a módulos nuevos y dejar handlers finos.

### Semántica de identidad

**Riesgo:** usar `username` como correlación R1/R2 permite reidentificación.  
**Mitigación:** mantenerlo solo durante sesión para el MVP; no exponer trayectorias individuales a estudiantes; planificar identificador efímero posteriormente.

### Reconexión

**Riesgo:** el cliente reingresa a la sala, pero necesita conocer fase, ronda y si ya respondió.  
**Mitigación:** incluir `current_phase` y estado de respuesta del usuario en la respuesta de rejoin ICCI.

### Finalización automática

ClassQuiz actualmente puede emitir `everyone_answered` cuando todos contestan. En deliberación no debe avanzar automáticamente de fase: el docente controla el cierre porque pueden existir ausencias, conversación incompleta o un propósito didáctico para extender el tiempo.

### Scoring

El cálculo actual usa corrección y tiempo. No debe ejecutarse para respuestas deliberativas.

---

## 16. Decisión Gate 1

**PASS para comenzar Gate 2**, con una condición arquitectónica: implementar ICCI como una extensión aislada del runtime actual de ClassQuiz, manteniendo intacta la semántica de quiz competitivo y modelando explícitamente `phase` + `round` para la deliberación.

El primer objetivo de código no es construir el dashboard completo. Es demostrar este vertical slice end-to-end:

```text
Docente abre R1
→ alumno responde alternativa + convicción + justificación
→ docente cambia a DISCUSSION
→ alumno recibe instrucción de conversar
→ docente abre R2
→ alumno responde nuevamente
→ docente ve R1, R2 y transición neutral
```

Cuando este ciclo funcione de forma confiable con 3 clientes y con clientes concurrentes simulados, se habilita el resto del piloto.
