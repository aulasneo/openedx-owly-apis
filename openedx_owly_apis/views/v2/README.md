# OpenEdX Owly APIs v2 - Grades Management

## Descripción

La API v2 de Grades Management proporciona un CRUD completo para la gestión de calificaciones de estudiantes en cursos de OpenEdX. Esta API está diseñada siguiendo principios de clean code y arquitectura limpia.

## Características

- ✅ **CRUD completo** para calificaciones
- ✅ **Validaciones robustas** con mensajes de error claros
- ✅ **Paginación** para listados grandes
- ✅ **Filtrado avanzado** por curso, estudiante, unidad y rango de calificaciones
- ✅ **Documentación Swagger** completa
- ✅ **Manejo de errores** consistente
- ✅ **Logging** detallado para debugging
- ✅ **Permisos** de seguridad (IsAuthenticated, IsAdminOrCourseStaff)

## Endpoints

### Base URL
```
/api/v2/grades/
```

### 1. Crear Calificación
**POST** `/api/v2/grades/`

Crea una nueva calificación para un estudiante en una unidad específica.

#### Request Body
```json
{
    "course_id": "course-v1:TestX+CS101+2024",
    "student_username": "john_doe",
    "unit_id": "block-v1:TestX+CS101+2024+type@problem+block@problem1",
    "grade_value": 85.50,
    "max_grade": 100.00,
    "comment": "Excelente trabajo en el problema"
}
```

#### Response (201 Created)
```json
{
    "success": true,
    "message": "Grade created successfully",
    "data": {
        "id": "course-v1:TestX+CS101+2024_john_doe_block-v1:TestX+CS101+2024+type@problem+block@problem1",
        "course_id": "course-v1:TestX+CS101+2024",
        "student_username": "john_doe",
        "student_email": "john.doe@example.com",
        "unit_id": "block-v1:TestX+CS101+2024+type@problem+block@problem1",
        "unit_name": "Problem 1: Basic Calculations",
        "grade_value": 85.50,
        "max_grade": 100.00,
        "percentage": 85.50,
        "comment": "Excelente trabajo en el problema",
        "created_at": "2024-01-15T10:30:00Z",
        "updated_at": "2024-01-15T10:30:00Z",
        "graded_by": "instructor"
    }
}
```

### 2. Obtener Calificación
**GET** `/api/v2/grades/{id}/`

Obtiene una calificación específica por parámetros de consulta.

#### Query Parameters
- `course_id` (required): ID del curso
- `student_username` (required): Nombre de usuario del estudiante
- `unit_id` (required): ID de la unidad

#### Example
```
GET /api/v2/grades/1/?course_id=course-v1:TestX+CS101+2024&student_username=john_doe&unit_id=block-v1:TestX+CS101+2024+type@problem+block@problem1
```

#### Response (200 OK)
```json
{
    "success": true,
    "data": {
        "id": "course-v1:TestX+CS101+2024_john_doe_block-v1:TestX+CS101+2024+type@problem+block@problem1",
        "course_id": "course-v1:TestX+CS101+2024",
        "student_username": "john_doe",
        "student_email": "john.doe@example.com",
        "unit_id": "block-v1:TestX+CS101+2024+type@problem+block@problem1",
        "unit_name": "Problem 1: Basic Calculations",
        "grade_value": 85.50,
        "max_grade": 100.00,
        "percentage": 85.50,
        "comment": "Excelente trabajo en el problema",
        "created_at": "2024-01-15T10:30:00Z",
        "updated_at": "2024-01-15T10:30:00Z",
        "graded_by": "instructor"
    }
}
```

### 3. Actualizar Calificación
**PUT** `/api/v2/grades/{id}/` o **PATCH** `/api/v2/grades/{id}/`

Actualiza una calificación existente.

#### Query Parameters
- `course_id` (required): ID del curso
- `student_username` (required): Nombre de usuario del estudiante
- `unit_id` (required): ID de la unidad

#### Request Body (PUT - todos los campos, PATCH - campos opcionales)
```json
{
    "grade_value": 90.00,
    "max_grade": 100.00,
    "comment": "Calificación actualizada después de revisión"
}
```

#### Response (200 OK)
```json
{
    "success": true,
    "message": "Grade updated successfully",
    "data": {
        "id": "course-v1:TestX+CS101+2024_john_doe_block-v1:TestX+CS101+2024+type@problem+block@problem1",
        "course_id": "course-v1:TestX+CS101+2024",
        "student_username": "john_doe",
        "student_email": "john.doe@example.com",
        "unit_id": "block-v1:TestX+CS101+2024+type@problem+block@problem1",
        "unit_name": "Problem 1: Basic Calculations",
        "grade_value": 90.00,
        "max_grade": 100.00,
        "percentage": 90.00,
        "comment": "Calificación actualizada después de revisión",
        "created_at": "2024-01-15T10:30:00Z",
        "updated_at": "2024-01-15T11:45:00Z",
        "graded_by": "instructor"
    }
}
```

### 4. Eliminar Calificación
**DELETE** `/api/v2/grades/{id}/`

Elimina una calificación específica.

#### Query Parameters
- `course_id` (required): ID del curso
- `student_username` (required): Nombre de usuario del estudiante
- `unit_id` (required): ID de la unidad

#### Response (204 No Content)
```json
{
    "success": true,
    "message": "Grade deleted successfully"
}
```

### 5. Listar Calificaciones
**GET** `/api/v2/grades/`

Lista calificaciones con filtrado y paginación opcionales.

#### Query Parameters
- `course_id` (optional): Filtrar por ID del curso
- `student_username` (optional): Filtrar por nombre de usuario del estudiante
- `unit_id` (optional): Filtrar por ID de la unidad
- `min_grade` (optional): Filtrar por calificación mínima
- `max_grade_filter` (optional): Filtrar por calificación máxima
- `page` (optional, default=1): Número de página
- `page_size` (optional, default=20, max=100): Elementos por página

#### Example
```
GET /api/v2/grades/?course_id=course-v1:TestX+CS101+2024&min_grade=80&page=1&page_size=10
```

#### Response (200 OK)
```json
{
    "success": true,
    "data": {
        "grades": [
            {
                "id": "course-v1:TestX+CS101+2024_john_doe_block-v1:TestX+CS101+2024+type@problem+block@problem1",
                "course_id": "course-v1:TestX+CS101+2024",
                "student_username": "john_doe",
                "student_email": "john.doe@example.com",
                "unit_id": "block-v1:TestX+CS101+2024+type@problem+block@problem1",
                "unit_name": "Problem 1: Basic Calculations",
                "grade_value": 90.00,
                "max_grade": 100.00,
                "percentage": 90.00,
                "comment": "Excelente trabajo",
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T11:45:00Z",
                "graded_by": "instructor"
            }
        ],
        "pagination": {
            "page": 1,
            "page_size": 10,
            "total_pages": 5,
            "total_items": 47,
            "has_next": true,
            "has_previous": false
        },
        "filters": {
            "course_id": "course-v1:TestX+CS101+2024",
            "min_grade": 80,
            "student_username": null,
            "unit_id": null,
            "max_grade_filter": null
        }
    }
}
```

## Códigos de Error

### Códigos HTTP
- `200` - OK: Operación exitosa
- `201` - Created: Recurso creado exitosamente
- `204` - No Content: Recurso eliminado exitosamente
- `400` - Bad Request: Datos de entrada inválidos
- `401` - Unauthorized: No autenticado
- `403` - Forbidden: Sin permisos suficientes
- `404` - Not Found: Recurso no encontrado
- `500` - Internal Server Error: Error interno del servidor

### Códigos de Error Personalizados
- `GRADE_NOT_FOUND` - Calificación no encontrada
- `STUDENT_NOT_FOUND` - Estudiante no encontrado
- `COURSE_NOT_FOUND` - Curso no encontrado
- `UNIT_NOT_FOUND` - Unidad no encontrada
- `INVALID_GRADE_VALUE` - Valor de calificación inválido
- `INVALID_OPENEDX_KEY` - Identificador de OpenEdX inválido
- `VALIDATION_ERROR` - Error de validación
- `PERMISSION_DENIED` - Permisos insuficientes

### Ejemplo de Respuesta de Error
```json
{
    "success": false,
    "error": {
        "message": "Student not found: invalid_user",
        "code": "STUDENT_NOT_FOUND",
        "status_code": 404,
        "details": {
            "field": "student_username",
            "value": "invalid_user"
        }
    }
}
```

## Validaciones

### Formato de IDs de OpenEdX
- **Course ID**: `course-v1:ORG+COURSE+RUN`
- **Unit ID**: `block-v1:ORG+COURSE+RUN+type@TYPE+block@BLOCK`

### Validaciones de Calificaciones
- `grade_value` debe ser >= 0
- `max_grade` debe ser > 0
- `grade_value` no puede exceder `max_grade`
- `max_grade` no puede exceder 10,000
- `comment` no puede exceder 1,000 caracteres

### Validaciones de Usuario
- `username` debe tener entre 2 y 150 caracteres
- Solo se permiten letras, números, guiones bajos, guiones y puntos

### Validaciones de Paginación
- `page` debe ser >= 1
- `page_size` debe estar entre 1 y 100

## Permisos

### Requerimientos de Autenticación
- Todos los endpoints requieren autenticación (`IsAuthenticated`)
- Todos los endpoints requieren permisos de administrador o staff del curso (`IsAdminOrCourseStaff`)

### Niveles de Acceso
- **Administradores**: Acceso completo a todas las operaciones
- **Course Staff**: Acceso a operaciones dentro de sus cursos asignados
- **Estudiantes**: Sin acceso a estos endpoints

## Ejemplos de Uso

### Python con requests
```python
import requests

# Configuración
base_url = "https://api.example.com/api/v2/grades/"
headers = {
    "Authorization": "Bearer YOUR_TOKEN",
    "Content-Type": "application/json"
}

# Crear calificación
grade_data = {
    "course_id": "course-v1:TestX+CS101+2024",
    "student_username": "john_doe",
    "unit_id": "block-v1:TestX+CS101+2024+type@problem+block@problem1",
    "grade_value": 85.50,
    "max_grade": 100.00,
    "comment": "Buen trabajo"
}

response = requests.post(base_url, json=grade_data, headers=headers)
print(response.json())

# Listar calificaciones con filtros
params = {
    "course_id": "course-v1:TestX+CS101+2024",
    "min_grade": 80,
    "page_size": 20
}

response = requests.get(base_url, params=params, headers=headers)
print(response.json())
```

### cURL
```bash
# Crear calificación
curl -X POST "https://api.example.com/api/v2/grades/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "course_id": "course-v1:TestX+CS101+2024",
    "student_username": "john_doe",
    "unit_id": "block-v1:TestX+CS101+2024+type@problem+block@problem1",
    "grade_value": 85.50,
    "max_grade": 100.00,
    "comment": "Buen trabajo"
  }'

# Obtener calificación
curl -X GET "https://api.example.com/api/v2/grades/1/?course_id=course-v1:TestX+CS101+2024&student_username=john_doe&unit_id=block-v1:TestX+CS101+2024+type@problem+block@problem1" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Listar calificaciones
curl -X GET "https://api.example.com/api/v2/grades/?course_id=course-v1:TestX+CS101+2024&min_grade=80" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Arquitectura y Clean Code

### Principios Aplicados
- **Single Responsibility Principle**: Cada clase tiene una responsabilidad específica
- **Separation of Concerns**: Lógica de negocio separada de la presentación
- **DRY (Don't Repeat Yourself)**: Reutilización de código mediante mixins y utilidades
- **Explicit is Better Than Implicit**: Validaciones y errores claros
- **Fail Fast**: Validación temprana de datos de entrada

### Estructura del Código
```
v2/
├── __init__.py
├── views.py          # ViewSets con lógica de presentación
├── serializers.py    # Serialización y validación de datos
├── validators.py     # Validaciones personalizadas
├── exceptions.py     # Manejo de errores personalizado
├── urls.py          # Configuración de URLs
└── README.md        # Esta documentación
```

### Patrones de Diseño Utilizados
- **ViewSet Pattern**: Para organizar endpoints relacionados
- **Serializer Pattern**: Para validación y serialización de datos
- **Mixin Pattern**: Para reutilización de validaciones
- **Builder Pattern**: Para construcción de respuestas de error
- **Decorator Pattern**: Para manejo de errores

## Testing

### Casos de Prueba Recomendados
1. **Crear calificación válida**
2. **Crear calificación con datos inválidos**
3. **Obtener calificación existente**
4. **Obtener calificación inexistente**
5. **Actualizar calificación existente**
6. **Actualizar calificación inexistente**
7. **Eliminar calificación existente**
8. **Eliminar calificación inexistente**
9. **Listar calificaciones sin filtros**
10. **Listar calificaciones con filtros**
11. **Paginación correcta**
12. **Validaciones de permisos**

### Ejemplo de Test
```python
import pytest
from rest_framework.test import APIClient
from rest_framework import status

class TestGradeAPI:
    def setup_method(self):
        self.client = APIClient()
        # Setup authentication and test data
    
    def test_create_grade_success(self):
        data = {
            "course_id": "course-v1:TestX+CS101+2024",
            "student_username": "test_user",
            "unit_id": "block-v1:TestX+CS101+2024+type@problem+block@test",
            "grade_value": 85.0,
            "max_grade": 100.0,
            "comment": "Test comment"
        }
        
        response = self.client.post('/api/v2/grades/', data)
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['success'] is True
        assert response.data['data']['grade_value'] == 85.0
```

## Monitoreo y Logging

### Logs Generados
- Creación de calificaciones
- Actualizaciones de calificaciones
- Eliminación de calificaciones
- Errores de validación
- Errores de permisos
- Errores de sistema

### Métricas Recomendadas
- Número de calificaciones creadas por día
- Tiempo de respuesta promedio
- Tasa de errores por endpoint
- Uso de filtros más comunes
- Distribución de calificaciones por curso

## Versionado

Esta es la versión 2 de la API de calificaciones. Los cambios principales respecto a v1:
- Arquitectura más limpia y modular
- Mejor manejo de errores
- Validaciones más robustas
- Documentación completa
- Paginación mejorada
- Filtrado avanzado

## Soporte

Para soporte técnico o reportar bugs, contacta al equipo de desarrollo o crea un issue en el repositorio del proyecto.
