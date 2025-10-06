# Documentación de la API para ORAs (Open Response Assessments)

## Endpoint para crear ORAs

**URL:** `POST /api/v1/owly-courses/content/ora/`

**Permisos requeridos:** Usuario autenticado que sea administrador, creador de cursos, o staff del curso.

**Nota importante:** Los tipos de evaluación usan nombres completos: `self-assessment`, `peer-assessment`, `staff-assessment`

### Parámetros del Body

```json
{
  "vertical_id": "block-v1:ORG+COURSE+RUN+type@vertical+block@VERTICAL_ID",
  "ora_config": {
    "display_name": "Ensayo de Análisis Crítico",
    "prompt": "Escribe un ensayo de 500 palabras analizando el tema propuesto. Considera múltiples perspectivas y proporciona evidencia para respaldar tus argumentos.",
    "rubric": {
      "criteria": [
        {
          "name": "Contenido y Análisis",
          "prompt": "¿Qué tan bien aborda el ensayo el tema con análisis crítico?",
          "options": [
            {
              "name": "Excelente",
              "points": 4,
              "explanation": "Análisis profundo y comprensivo con múltiples perspectivas"
            },
            {
              "name": "Bueno",
              "points": 3,
              "explanation": "Buen análisis con algunas perspectivas consideradas"
            },
            {
              "name": "Regular",
              "points": 2,
              "explanation": "Análisis básico con perspectiva limitada"
            },
            {
              "name": "Deficiente",
              "points": 1,
              "explanation": "Análisis superficial o inexistente"
            }
          ]
        },
        {
          "name": "Claridad y Organización",
          "prompt": "¿Qué tan claro y bien organizado está el ensayo?",
          "options": [
            {
              "name": "Excelente",
              "points": 4,
              "explanation": "Muy claro y bien estructurado"
            },
            {
              "name": "Bueno",
              "points": 3,
              "explanation": "Claro con buena estructura"
            },
            {
              "name": "Regular",
              "points": 2,
              "explanation": "Parcialmente claro, estructura básica"
            },
            {
              "name": "Deficiente",
              "points": 1,
              "explanation": "Confuso o mal estructurado"
            }
          ]
        }
      ]
    },
    "assessments": [
      {
        "name": "self",
        "start": null,
        "due": null,
        "must_grade": 1,
        "must_be_graded_by": 1
      },
      {
        "name": "peer",
        "start": null,
        "due": null,
        "must_grade": 3,
        "must_be_graded_by": 2
      },
      {
        "name": "staff",
        "start": null,
        "due": null,
        "required": false
      }
    ],
    "submission_start": "2024-01-01T00:00:00Z",
    "submission_due": "2024-12-31T23:59:59Z",
    "allow_text_response": true,
    "allow_file_upload": false,
    "file_upload_type": null,
    "leaderboard_show": 0
  }
}
```

### Respuesta exitosa

```json
{
  "success": true,
  "component_id": "block-v1:ORG+COURSE+RUN+type@openassessment+block@GENERATED_ID",
  "parent_vertical": "block-v1:ORG+COURSE+RUN+type@vertical+block@VERTICAL_ID",
  "display_name": "Ensayo de Análisis Crítico",
  "prompt": "Escribe un ensayo de 500 palabras...",
  "assessment_types": ["self", "peer", "staff"],
  "message": "ORA component created successfully"
}
```

## Configuraciones del ORA

### Campos principales del `ora_config`:

- **display_name** (str): Nombre que aparecerá para el ORA
- **prompt** (str): Pregunta o instrucciones para los estudiantes
- **rubric** (dict): Configuración de la rúbrica de evaluación
- **assessments** (list): Tipos de evaluación que se realizarán
- **submission_start** (str, opcional): Fecha de inicio para entregas (formato ISO)
- **submission_due** (str, opcional): Fecha límite para entregas (formato ISO)
- **allow_text_response** (bool, opcional): Permitir respuestas de texto (default: true)
- **allow_file_upload** (bool, opcional): Permitir subir archivos (default: false)
- **file_upload_type** (str, opcional): Tipo de archivos permitidos ('image', 'pdf-and-image')
- **leaderboard_show** (int, opcional): Número de mejores entregas a mostrar (default: 0)

### Tipos de evaluación disponibles:

1. **self**: Autoevaluación del estudiante
2. **peer**: Evaluación por pares
3. **staff**: Evaluación por instructor/staff

### Estructura de la rúbrica:

La rúbrica define los criterios de evaluación. Cada criterio debe tener:
- **name**: Nombre del criterio
- **prompt**: Pregunta o descripción del criterio
- **options**: Lista de opciones de puntuación con nombre, puntos y explicación

## Ejemplos de uso

### ORA básico con solo autoevaluación:

```json
{
  "vertical_id": "block-v1:TestX+CS101+2024+type@vertical+block@unit1",
  "ora_config": {
    "display_name": "Reflexión Personal",
    "prompt": "Reflexiona sobre lo aprendido en esta unidad.",
    "rubric": {
      "criteria": [
        {
          "name": "Reflexión",
          "prompt": "¿Qué tan profunda es la reflexión?",
          "options": [
            {"name": "Profunda", "points": 3, "explanation": "Reflexión muy detallada"},
            {"name": "Moderada", "points": 2, "explanation": "Reflexión básica"},
            {"name": "Superficial", "points": 1, "explanation": "Reflexión mínima"}
          ]
        }
      ]
    },
    "assessments": [
      {"name": "self", "must_grade": 1, "must_be_graded_by": 1}
    ],
    "allow_text_response": true
  }
}
```

### ORA con evaluación por pares y subida de archivos:

```json
{
  "vertical_id": "block-v1:TestX+CS101+2024+type@vertical+block@unit2",
  "ora_config": {
    "display_name": "Proyecto Final",
    "prompt": "Sube tu proyecto final y describe tu proceso de desarrollo.",
    "allow_text_response": true,
    "allow_file_upload": true,
    "file_upload_type": "pdf-and-image",
    "assessments": [
      {"name": "peer", "must_grade": 2, "must_be_graded_by": 2},
      {"name": "self", "must_grade": 1, "must_be_graded_by": 1}
    ],
    "submission_due": "2024-06-30T23:59:59Z"
  }
}
```

## Errores comunes

### Error 400 - Configuración inválida:
```json
{
  "success": false,
  "error": "Invalid ora_config",
  "message": "La configuración del ORA es inválida"
}
```

### Error 404 - Vertical no encontrado:
```json
{
  "success": false,
  "error": "vertical_not_found",
  "message": "No item found for vertical_id: ..."
}
```

### Error 403 - Sin permisos:
```json
{
  "detail": "User must be admin, Course Creator or Course Staff"
}
```

## Notas importantes

1. El vertical_id debe ser de un vertical válido y existente en el curso
2. El usuario debe tener permisos de staff en el curso o ser administrador/creador de cursos
3. Los ORAs son componentes complejos de OpenedX y requieren que el sistema tenga habilitados los XBlocks de openassessment
4. Las fechas deben estar en formato ISO 8601 con timezone (ej: "2024-01-01T00:00:00Z")
5. La evaluación por pares requiere que haya suficientes estudiantes en el curso para funcionar correctamente