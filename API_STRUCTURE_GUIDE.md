# Guía de Estructura para Futuras APIs v2

Esta guía documenta la estructura establecida para crear nuevas APIs en el proyecto, siguiendo los patrones de Clean Code y CRUD implementados en Content Groups API.

## 📁 Estructura de Archivos

Para cada nueva API, crear la siguiente estructura:

```
openedx_owly_apis/views/v2/
├── views.py              # ViewSets principales
├── serializers.py        # Serializers para validación
├── urls.py              # Configuración de URLs
└── tests/               # Tests unitarios (opcional)
    ├── test_views.py
    └── test_serializers.py
```

## 🏗️ Arquitectura de Clases

### 1. Clase Base: BaseAPIViewSet

Ya implementada en `utils/base_views.py`:

```python
class BaseAPIViewSet(BaseCRUDViewSet):
    """
    Clase base para APIs que no usan modelos Django directamente.
    Implementa Template Method Pattern para CRUD operations.
    """
```

**Características:**
- ✅ Hereda de `BaseCRUDViewSet`
- ✅ Maneja validación automática con serializers
- ✅ Códigos HTTP estándar
- ✅ Template Method Pattern con `perform_*_logic()`

### 2. ViewSets Específicos

Cada entidad debe tener su propio ViewSet:

```python
class [Entity]ViewSet(BaseAPIViewSet):
    """
    ViewSet for managing [Entity Description].
    
    [Detailed description of what this entity does]
    """
    
    # Configuration
    permission_classes = [IsAuthenticated, IsAdminOrCourseStaff]
    serializer_class = [Entity]ListSerializer
    create_serializer_class = [Entity]CreateSerializer
    update_serializer_class = [Entity]UpdateSerializer
    
    # Logic methods (Template Method Pattern)
    def perform_list_logic(self, query_params): ...
    def perform_create_logic(self, validated_data): ...
    def perform_update_logic(self, pk, validated_data): ...
    def perform_destroy_logic(self, pk, query_params): ...
```

## 📝 Serializers Pattern

### Estructura de Serializers

```python
# serializers.py

class [Entity]CreateSerializer(serializers.Serializer):
    """Serializer for creating [Entity]."""
    field1 = serializers.CharField(max_length=255)
    field2 = serializers.CharField(required=False)
    
    def validate_field1(self, value):
        # Custom validation
        return value

class [Entity]UpdateSerializer(serializers.Serializer):
    """Serializer for updating [Entity]."""
    field1 = serializers.CharField(max_length=255, required=False)
    field2 = serializers.CharField(required=False)

class [Entity]ListSerializer(serializers.Serializer):
    """Serializer for listing [Entity] (read-only)."""
    id = serializers.IntegerField(read_only=True)
    field1 = serializers.CharField(read_only=True)
    field2 = serializers.CharField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
```

### Principios de Serializers

1. **Separación por operación**: Create, Update, List
2. **Validación específica**: Métodos `validate_*()` para cada campo
3. **Campos opcionales**: Usar `required=False` apropiadamente
4. **Read-only fields**: Para campos que no se modifican

## 🔗 URLs Pattern

### Configuración de URLs

```python
# urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import [Entity]ViewSet, [Entity][Relation]ViewSet

router = DefaultRouter()
router.register(r'[entities]', [Entity]ViewSet, basename='[entities]')
router.register(r'[entity-relations]', [Entity][Relation]ViewSet, basename='[entity-relations]')

urlpatterns = [
    path('', include(router.urls)),
]
```

### Convenciones de Naming

- **Entidades principales**: `entities` (plural, kebab-case)
- **Relaciones**: `entity-relations` (descriptivo, kebab-case)
- **Basenames**: Igual que el path para consistencia

## 🎯 Logic Functions Pattern

### Ubicación
Todas las funciones lógicas van en `operations/[module].py`

### Estructura de Logic Functions

```python
# operations/[module].py

def list_[entities]_logic(course_id: str, user_identifier=None) -> dict:
    """
    List all [entities] for a course.
    
    Args:
        course_id (str): Course identifier
        user_identifier: User performing the action
        
    Returns:
        dict: Success/error response with list of [entities]
    """
    logger = logging.getLogger(__name__)
    
    try:
        # Validation
        if not course_id:
            return {
                "success": False,
                "error": "missing_course_id",
                "message": "course_id is required"
            }
        
        # Get user
        User = get_user_model()
        acting_user = User.objects.get(id=user_identifier)
        
        # Business logic here
        # ...
        
        return {
            "success": True,
            "[entities]": data,
            "total": len(data)
        }
        
    except Exception as e:
        logger.exception(f"Failed to list [entities]: {str(e)}")
        return {
            "success": False,
            "error": "[entities]_list_failed",
            "message": f"Failed to list [entities]: {str(e)}"
        }
```

### Principios de Logic Functions

1. **Naming consistente**: `[action]_[entity]_logic`
2. **Type hints**: Siempre especificar tipos de parámetros y retorno
3. **Logging**: Para auditoría y debugging
4. **Error handling**: Try/catch con mensajes descriptivos
5. **Validación**: Verificar parámetros requeridos
6. **Respuesta estándar**: `{"success": bool, "data": ..., "error": ...}`

## 🚀 Ejemplo Completo: Nueva API "Announcements"

### 1. ViewSet

```python
# views.py
class AnnouncementViewSet(BaseAPIViewSet):
    """
    ViewSet for managing course announcements.
    
    Announcements allow instructors to communicate important
    information to students in their courses.
    """
    
    permission_classes = [IsAuthenticated, IsAdminOrCourseStaff]
    serializer_class = AnnouncementListSerializer
    create_serializer_class = AnnouncementCreateSerializer
    update_serializer_class = AnnouncementUpdateSerializer
    
    def perform_list_logic(self, query_params):
        """List all announcements for a course"""
        from openedx_owly_apis.operations.announcements import list_announcements_logic
        
        course_id = query_params.get('course_id')
        if not course_id:
            return {
                'success': False,
                'message': 'course_id parameter is required',
                'error_code': 'missing_course_id'
            }
        
        return list_announcements_logic(
            course_id=course_id,
            user_identifier=self.request.user.id
        )
    
    def perform_create_logic(self, validated_data):
        """Create a new announcement"""
        from openedx_owly_apis.operations.announcements import create_announcement_logic
        
        return create_announcement_logic(
            course_id=validated_data['course_id'],
            title=validated_data['title'],
            content=validated_data['content'],
            user_identifier=self.request.user.id
        )
```

### 2. Serializers

```python
# serializers.py
class AnnouncementCreateSerializer(serializers.Serializer):
    course_id = serializers.CharField(max_length=255)
    title = serializers.CharField(max_length=255)
    content = serializers.CharField()
    
    def validate_course_id(self, value):
        if not value.strip():
            raise serializers.ValidationError("course_id cannot be empty")
        return value.strip()

class AnnouncementListSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    title = serializers.CharField(read_only=True)
    content = serializers.CharField(read_only=True)
    course_id = serializers.CharField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
```

## ✅ Checklist para Nuevas APIs

### Antes de empezar:
- [ ] Definir la entidad y sus relaciones
- [ ] Identificar operaciones CRUD necesarias
- [ ] Planificar estructura de datos

### Durante desarrollo:
- [ ] Crear serializers (Create, Update, List)
- [ ] Implementar ViewSet heredando de `BaseAPIViewSet`
- [ ] Implementar métodos `perform_*_logic()`
- [ ] Crear logic functions en `operations/`
- [ ] Configurar URLs en router
- [ ] Agregar documentación en docstrings

### Después de implementar:
- [ ] Probar todos los endpoints CRUD
- [ ] Verificar validaciones de serializers
- [ ] Revisar logs y manejo de errores
- [ ] Actualizar documentación de API

## 🎨 Principios de Clean Code Aplicados

1. **Single Responsibility**: Cada clase tiene una responsabilidad específica
2. **Open/Closed**: Extensible via herencia, cerrado para modificación
3. **Dependency Inversion**: ViewSets dependen de abstracciones (BaseAPIViewSet)
4. **Template Method**: Patrón implementado en BaseAPIViewSet
5. **Separation of Concerns**: ViewSets, Serializers, Logic separados
6. **DRY**: No repetir código, usar herencia apropiadamente

## 📊 Estructura Final de Endpoints

Siguiendo esta estructura, cada nueva API tendrá:

```
GET    /api/v2/[entities]/?course_id=...           # List
POST   /api/v2/[entities]/                         # Create  
PUT    /api/v2/[entities]/{id}/                    # Update
DELETE /api/v2/[entities]/{id}/?course_id=...      # Delete
```

Esta estructura garantiza:
- ✅ **Consistencia** entre todas las APIs
- ✅ **Mantenibilidad** del código
- ✅ **Escalabilidad** para futuras funcionalidades
- ✅ **Clean Code** principles aplicados
- ✅ **CRUD completo** y funcional

## 📋 Resumen de Archivos Implementados

### Content Groups API (Ejemplo de Referencia)

```
openedx_owly_apis/
├── utils/base_views.py                    # BaseAPIViewSet
├── views/v2/
│   ├── views.py                          # ContentGroupViewSet + AssignmentViewSet
│   ├── serializers.py                    # Serializers para validación
│   └── urls.py                           # URLs configuradas
├── operations/courses.py                  # Logic functions
└── urls.py                               # URLs principales con v2
```

Esta implementación sirve como **template** para todas las futuras APIs del proyecto.
