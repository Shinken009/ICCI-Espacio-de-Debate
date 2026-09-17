<!-- SPDX-License-Identifier: MPL-2.0 -->

# Piloto v0.1 – Classroom Pilot

## Objetivo

Validar un vertical slice funcional de deliberación en aula sobre la infraestructura real de ClassQuiz, con foco en uso BYOD y dos tamaños de cohorte: curso estándar y seminario pequeño.

## Alcance funcional mínimo

El piloto debe permitir:

1. profesor abre una sesión;
2. estudiantes ingresan mediante PIN desde sus teléfonos;
3. se ejecuta una pregunta de entrenamiento;
4. se ejecuta una pregunta sustantiva;
5. cada estudiante registra R1;
6. cada estudiante registra convicción y justificación breve;
7. el docente inicia la fase de deliberación;
8. se ejecuta R2;
9. se registra una reflexión breve;
10. el docente observa resultados descriptivos pre/post.

## Pregunta de entrenamiento

Objetivo: enseñar la metodología y reducir errores de interfaz antes de la actividad principal.

Ejemplo:

> Para una pequeña aplicación web, ¿qué lenguaje o stack preferirías usar inicialmente?

Opciones:

- Python;
- JavaScript/TypeScript;
- Java;
- Otro.

No existe una respuesta correcta. El propósito es aprender el flujo.

## Pregunta sustantiva

Ejemplo inicial:

> Un sistema de IA desarrollado por tu equipo puede proponer y ejecutar modificaciones sobre infraestructura crítica. Los resultados de prueba son altos, pero las decisiones internas todavía no pueden auditarse adecuadamente. La organización solicita desplegarlo.

Opciones:

- A. Desplegar ahora con monitoreo reforzado.
- B. Postergar hasta alcanzar mayor auditabilidad.
- C. Realizar un despliegue progresivo con supervisión humana.
- D. No autorizar el despliegue actual y escalar formalmente la objeción.

En modo deliberativo ninguna opción se marca como correcta.

## Analítica mínima

El panel docente debe poder representar:

- distribución R1;
- distribución R2;
- matriz completa de transiciones R1 → R2;
- número de participantes que mantuvieron/cambiaron postura;
- cambio de convicción;
- argumentos o justificaciones seleccionables;
- reflexión posterior.

No debe etiquetar una transición concreta como éxito.

## Configuración estándar

Para aproximadamente 20–35 estudiantes:

- grupos de 2–4;
- discusión breve entre pares;
- datos agregados en el panel docente;
- posibilidad de destacar argumentos sin convertirlos en ranking de estudiantes.

## Configuración seminario

Para N=3:

- una tríada;
- sin agrupamiento automático;
- turnos o conversación guiada;
- conteos explícitos en vez de porcentajes como representación principal;
- advertencia de que el anonimato puede ser limitado por el tamaño del grupo;
- sin métricas inferenciales ni indicadores estadísticos complejos.

## Criterios de aceptación

### Técnico

- [ ] el upstream compila sin modificaciones funcionales;
- [ ] backend inicia correctamente;
- [ ] frontend inicia correctamente;
- [ ] estudiante puede unirse por PIN;
- [ ] mínimo 3 clientes simultáneos completan el flujo;
- [ ] R1 y R2 se distinguen correctamente;
- [ ] convicción y justificación persisten durante la sesión;
- [ ] transición de fases funciona en realtime;
- [ ] reconexión no corrompe la sesión;
- [ ] no hay secretos ni credenciales en el repositorio;
- [ ] cambios respetan MPL-2.0.

### Pedagógico

- [ ] la pregunta de entrenamiento enseña el flujo sin evaluación;
- [ ] el estudiante entiende cuándo está en R1, discusión y R2;
- [ ] el sistema no presenta una opción ética como correcta por defecto;
- [ ] la analítica distingue cambio de postura de aprendizaje;
- [ ] la experiencia N=3 no utiliza anonimato engañoso ni porcentajes como única representación.

### UX

- [ ] usable desde navegador móvil;
- [ ] controles principales accesibles sin zoom;
- [ ] estado de fase claramente visible;
- [ ] confirmación de respuesta inequívoca;
- [ ] errores de conexión comprensibles;
- [ ] no se requieren cuentas institucionales para el piloto.

## Fuera de alcance

Quedan fuera de v0.1:

- LMS;
- calificaciones;
- IA generativa;
- análisis automático de argumentos;
- perfiles longitudinales;
- integración institucional;
- gamificación competitiva adicional;
- dashboards de investigación;
- publicación de datos reales de estudiantes.

## Evidencia del piloto

Tras la prueba de aula se registrarán, de forma no identificable cuando corresponda:

- número de dispositivos conectados;
- errores operativos;
- tiempos aproximados por fase;
- confusiones de interfaz;
- utilidad percibida de R1/R2;
- comportamiento de la escala de convicción;
- calidad operativa de la deliberación;
- mejoras necesarias para v0.2.

La primera release pública propuesta será:

```text
v0.1.0 – Classroom Pilot
```

solo después de superar los criterios técnicos mínimos y una prueba controlada.
