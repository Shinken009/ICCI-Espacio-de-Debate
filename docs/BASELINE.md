<!-- SPDX-License-Identifier: MPL-2.0 -->

# Baseline técnico

## Procedencia

Este repositorio es un fork de:

- **Upstream:** `mawoka-myblock/ClassQuiz`
- **Repositorio:** https://github.com/mawoka-myblock/ClassQuiz
- **Licencia:** Mozilla Public License 2.0 (MPL-2.0)
- **Rama upstream de referencia:** `master`

## Baseline inicial

El desarrollo de ICCI – Espacio de debate parte desde el commit:

```text
711bdde7a7dcd2d217cfc75dbbbb2592a78582d3
```

Mensaje upstream asociado:

```text
Fix and add basic RTL support
```

Fecha del commit: 2026-08-30.

La rama `master` del fork se conserva inicialmente sin modificaciones funcionales. El trabajo propio comienza en:

```text
feat/peer-instruction
```

## Regla de trazabilidad

Antes de modificar comportamiento se debe poder responder:

1. ¿el comportamiento proviene de ClassQuiz o de ICCI?;
2. ¿qué archivo upstream fue modificado?;
3. ¿qué requisito pedagógico justifica el cambio?;
4. ¿qué prueba valida que el cambio no rompe el flujo original?;
5. ¿la modificación mantiene las obligaciones MPL-2.0 aplicables?

## Gate previo a implementación

Antes del primer cambio funcional deben comprobarse localmente:

- instalación reproducible de dependencias;
- build del frontend;
- arranque del backend;
- conexión a PostgreSQL y Redis cuando corresponda;
- creación y unión a una sesión ClassQuiz;
- comunicación realtime existente;
- suite de tests disponible en upstream;
- ausencia de secretos locales en commits.

## Upstream sync

Durante el piloto se evitarán refactors no necesarios sobre archivos heredados. Las actualizaciones desde ClassQuiz deberán revisarse explícitamente para minimizar drift y conflictos futuros.
