<!--
SPDX-FileCopyrightText: 2023 Marlon W (Mawoka)
SPDX-FileCopyrightText: 2026 Roberto Pizarro Díaz

SPDX-License-Identifier: MPL-2.0
-->

# ICCI – Espacio de debate

**Plataforma experimental de aprendizaje activo para estructurar procesos de respuesta individual, argumentación, deliberación entre pares y reconsideración de posturas en educación superior.**

> Estado: **piloto en desarrollo (`v0.1`)**. Este repositorio es un fork de [ClassQuiz](https://github.com/mawoka-myblock/ClassQuiz) y conserva su base tecnológica y obligaciones de licencia MPL-2.0.

## Propósito

ICCI – Espacio de debate explora cómo transformar una pregunta de aula en un proceso deliberativo observable y reproducible:

**Piensa → responde → explicita tu razonamiento → conversa → reconsidera → reflexiona.**

El objetivo inicial no es construir otro sistema de trivia ni premiar el cambio de respuesta. El foco está en hacer visible el proceso de razonamiento, discusión y metacognición, especialmente en actividades donde puede no existir una única respuesta correcta.

El primer piloto está orientado a docencia universitaria en informática y contempla dos escenarios:

- cursos de aproximadamente **20–35 estudiantes**, con deliberación entre pares o pequeños grupos;
- seminarios pequeños, incluido un escenario de **3 estudiantes**, con conversación guiada y visualizaciones adecuadas a muestras reducidas.

Este proyecto es una iniciativa experimental de desarrollo y docencia. **No representa un producto institucional oficial de una universidad.**

## Primer flujo de aprendizaje

La versión inicial implementará un flujo configurable de Peer Instruction / deliberación:

1. pregunta de entrenamiento para aprender la dinámica y la interfaz;
2. respuesta individual inicial (R1);
3. nivel de convicción;
4. justificación breve;
5. deliberación entre pares;
6. segunda respuesta individual (R2);
7. reflexión/metacognición;
8. analítica neutral de transiciones y argumentos.

La plataforma no interpretará automáticamente un cambio de alternativa como éxito. La analítica observará, entre otros elementos:

- mantenimiento o cambio de postura;
- matriz completa de transiciones R1 → R2;
- variación del nivel de convicción;
- convergencia o divergencia de respuestas;
- argumentos destacados;
- reflexión posterior a la discusión.

## Arquitectura

ICCI se construye sobre la arquitectura real de ClassQuiz en lugar de reimplementar su infraestructura de sesiones y comunicación en tiempo real.

### Backend

- FastAPI
- ormar
- python-socketio
- PostgreSQL
- Redis

### Frontend

- SvelteKit
- Tailwind CSS

El prototipo visual previo en React/Vite se considera una **referencia UX y funcional**, no la base de producción del fork.

## Principio de extensibilidad

El objetivo es que Peer Instruction sea la primera metodología, no la arquitectura completa. El modelo futuro se organizará alrededor de entidades configurables como:

```text
Activity
├── Question
├── Phase
├── Response
├── Group
├── Reflection
└── Analytics
```

Esto permitirá explorar posteriormente metodologías como:

- Think–Pair–Share;
- debate estructurado;
- Team-Based Learning;
- Jigsaw;
- ranking o priorización colectiva;
- evaluación entre pares;
- dilemas éticos;
- construcción de consenso;
- retrospectivas y reflexión grupal.

## Alcance de `v0.1 – Classroom Pilot`

El primer vertical slice debe demostrar, de extremo a extremo:

```text
Profesor abre sesión
        ↓
Estudiantes ingresan con PIN
        ↓
Pregunta de entrenamiento
        ↓
Pregunta sustantiva
        ↓
R1 + convicción + justificación
        ↓
Deliberación
        ↓
R2 + reflexión
        ↓
Analítica docente
```

No forman parte de `v0.1`: integración LMS, calificaciones, IA generativa, análisis automático de argumentos, microservicios adicionales ni cuentas institucionales.

## Documentación

- [`docs/BASELINE.md`](docs/BASELINE.md): procedencia del fork y baseline técnico.
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md): principios de arquitectura y extensibilidad.
- [`docs/PEDAGOGY.md`](docs/PEDAGOGY.md): modelo pedagógico y reglas de analítica responsable.
- [`docs/PILOT.md`](docs/PILOT.md): alcance y criterios de aceptación del primer piloto.

## Desarrollo

La rama `master` se mantiene inicialmente como referencia limpia del upstream. El desarrollo del piloto parte desde:

```text
feat/peer-instruction
```

Baseline inicial del fork:

```text
711bdde7a7dcd2d217cfc75dbbbb2592a78582d3
```

Antes de integrar código funcional se validará el build del upstream, sus dependencias y el flujo actual de sesiones.

## Upstream y atribución

ICCI – Espacio de debate deriva de **ClassQuiz**, creado y mantenido por Marlon W. / `mawoka-myblock` y sus colaboradores:

- Upstream: https://github.com/mawoka-myblock/ClassQuiz
- Proyecto original: https://classquiz.de

Las modificaciones propias se documentarán de manera explícita y se mantendrá la trazabilidad con el proyecto original.

## Licencia

ClassQuiz y los archivos derivados cubiertos por esta licencia se distribuyen bajo **Mozilla Public License 2.0 (MPL-2.0)**. Consulta [`LICENSE`](LICENSE) para los términos aplicables.

Las contribuciones nuevas deberán respetar las obligaciones de atribución y publicación de código fuente correspondientes a los archivos cubiertos por MPL-2.0.
