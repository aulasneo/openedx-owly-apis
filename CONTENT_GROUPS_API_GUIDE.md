# Content Groups API v2 - Usage Guide

Esta API permite gestionar content groups en OpenEdX y asignarlos a cohorts para crear experiencias de aprendizaje personalizadas.

## Endpoints Disponibles

### Content Groups: `/api/v2/content-groups/`
### Content Group Assignments: `/api/v2/content-group-assignments/`

## 1. Listar Content Groups

**GET** `/api/v2/content-groups/?course_id={course_id}`

Lista todos los content groups de un curso.

**Parámetros:**
- `course_id` (query): ID del curso (ej: `course-v1:TestX+CS101+2024`)

**Ejemplo de respuesta:**
```json
{
    "success": true,
    "course_id": "course-v1:TestX+CS101+2024",
    "content_groups": [
        {
            "id": 1,
            "name": "Advanced Students",
            "description": "Content for advanced students",
            "course_id": "course-v1:TestX+CS101+2024",
            "created_at": "2024-01-15T10:30:00Z",
            "updated_at": "2024-01-15T10:30:00Z"
        }
    ],
    "total_groups": 1
}
```

## 2. Crear Content Group

**POST** `/api/v2/content-groups/`

Crea un nuevo content group.

**Body:**
```json
{
    "course_id": "course-v1:TestX+CS101+2024",
    "name": "Advanced Students",
    "description": "Content for advanced students"
}
```

**Ejemplo de respuesta:**
```json
{
    "success": true,
    "content_group": {
        "id": 1,
        "name": "Advanced Students",
        "description": "Content for advanced students",
        "course_id": "course-v1:TestX+CS101+2024",
        "created_by": "instructor"
    },
    "message": "Content group 'Advanced Students' created successfully"
}
```

## 3. Actualizar Content Group

**PUT** `/api/v2/content-groups/{group_id}/`

Actualiza un content group existente.

**Body:**
```json
{
    "course_id": "course-v1:TestX+CS101+2024",
    "name": "Expert Students",
    "description": "Updated description"
}
```

## 4. Eliminar Content Group

**DELETE** `/api/v2/content-groups/{group_id}/?course_id={course_id}`

Elimina un content group.

## 5. Crear Asignación (Asignar Content Group a Cohort)

**POST** `/api/v2/content-group-assignments/`

Crea una nueva asignación entre un content group y un cohort.

**Body:**
```json
{
    "course_id": "course-v1:TestX+CS101+2024",
    "content_group_id": 1,
    "cohort_id": 2
}
```

**Ejemplo de respuesta:**
```json
{
    "success": true,
    "message": "Content group 'Advanced Students' assigned to cohort 'Group A' successfully",
    "assignment": {
        "content_group": {
            "id": 1,
            "name": "Advanced Students"
        },
        "cohort": {
            "id": 2,
            "name": "Group A"
        },
        "course_id": "course-v1:TestX+CS101+2024",
        "assigned_by": "instructor"
    }
}
```

## 6. Eliminar Asignación (Desasignar Content Group de Cohort)

**DELETE** `/api/v2/content-group-assignments/?course_id={course_id}&content_group_id={group_id}&cohort_id={cohort_id}`

O con body:

**DELETE** `/api/v2/content-group-assignments/`

**Body:**
```json
{
    "course_id": "course-v1:TestX+CS101+2024",
    "content_group_id": 1,
    "cohort_id": 2
}
```

## 7. Listar Asignaciones

**GET** `/api/v2/content-group-assignments/?course_id={course_id}`

Lista todas las asignaciones de content groups a cohorts.

**Ejemplo de respuesta:**
```json
{
    "success": true,
    "course_id": "course-v1:TestX+CS101+2024",
    "assignments": [
        {
            "content_group": {
                "id": 1,
                "name": "Advanced Students",
                "description": "Content for advanced students"
            },
            "cohort": {
                "id": 2,
                "name": "Group A"
            },
            "assignment_type": "manual",
            "course_id": "course-v1:TestX+CS101+2024"
        }
    ],
    "unassigned_content_groups": [
        {
            "id": 3,
            "name": "Beginner Students",
            "description": "Content for beginners"
        }
    ],
    "total_assignments": 1,
    "total_unassigned": 1
}
```

## Casos de Uso

### 1. Configurar Content Groups para diferentes niveles
```bash
# Crear content groups
curl -X POST /api/v2/content-groups/ \
  -H "Content-Type: application/json" \
  -d '{
    "course_id": "course-v1:TestX+CS101+2024",
    "name": "Beginner Level",
    "description": "Content for beginner students"
  }'

curl -X POST /api/v2/content-groups/ \
  -H "Content-Type: application/json" \
  -d '{
    "course_id": "course-v1:TestX+CS101+2024",
    "name": "Advanced Level",
    "description": "Content for advanced students"
  }'
```

### 2. Asignar content groups a cohorts existentes
```bash
# Asignar "Beginner Level" al cohort 1
curl -X POST /api/v2/content-group-assignments/ \
  -H "Content-Type: application/json" \
  -d '{
    "course_id": "course-v1:TestX+CS101+2024",
    "content_group_id": 1,
    "cohort_id": 1
  }'

# Asignar "Advanced Level" al cohort 2
curl -X POST /api/v2/content-group-assignments/ \
  -H "Content-Type: application/json" \
  -d '{
    "course_id": "course-v1:TestX+CS101+2024",
    "content_group_id": 2,
    "cohort_id": 2
  }'
```

### 3. Verificar asignaciones
```bash
curl -X GET "/api/v2/content-group-assignments/?course_id=course-v1:TestX+CS101+2024"
```

## Permisos Requeridos

- Usuario debe estar autenticado
- Usuario debe ser administrador o staff del curso (`IsAdminOrCourseStaff`)

## Códigos de Error Comunes

- `400`: Parámetros faltantes o inválidos
- `401`: No autenticado
- `403`: Sin permisos suficientes
- `404`: Content group o cohort no encontrado

## Integración con Cohorts v1

Esta API v2 se integra perfectamente con los endpoints de cohorts existentes en v1:

- **Crear cohorts**: `POST /api/v1/owly-courses/cohorts/create`
- **Listar cohorts**: `GET /api/v1/owly-courses/cohorts/list`
- **Gestionar miembros**: `/api/v1/owly-courses/cohorts/members/`

## Flujo Completo de Trabajo

1. **Crear cohorts** (usando API v1)
2. **Crear content groups** (usando API v2)
3. **Asignar content groups a cohorts** (usando API v2)
4. **Agregar estudiantes a cohorts** (usando API v1)
5. **Verificar asignaciones** (usando API v2)

Esto permite crear experiencias de aprendizaje personalizadas donde diferentes grupos de estudiantes ven contenido diferente basado en su cohort asignado.
