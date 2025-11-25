# Ejemplo de uso de la clase BaseCRUDViewSet

from openedx_owly_apis.utils.base_views import BaseCRUDViewSet
from .models import Company
from .serializers import CompanySerializer, CompanyListSerializer


class CompanyViewSet(BaseCRUDViewSet):
    """
    ViewSet para el modelo Company usando la clase base BaseCRUDViewSet
    """
    # Configuración básica requerida
    queryset = Company.objects.all()
    serializer_class = CompanyListSerializer  # Para listar y respuestas
    create_serializer_class = CompanySerializer  # Para crear
    update_serializer_class = CompanySerializer  # Para actualizar (opcional)
    
    # Configuración de filtros
    filter_fields = ('is_enabled',)
    
    # Permisos (descomenta según necesites)
    # permission_classes = (IsAppAuthenticated, IsAppStaff, IsAuthenticated, IsSuperUser)


# Ejemplo con diferentes serializers para create y update
class AnotherExampleViewSet(BaseCRUDViewSet):
    """
    Ejemplo con serializers diferentes para create y update
    """
    queryset = Company.objects.all()
    serializer_class = CompanyListSerializer  # Para listar y respuestas
    create_serializer_class = CompanyCreateSerializer  # Específico para crear
    update_serializer_class = CompanyUpdateSerializer  # Específico para actualizar
    
    filter_fields = ('is_enabled', 'created_at')


# Ejemplo mínimo (usando el mismo serializer para create y update)
class MinimalExampleViewSet(BaseCRUDViewSet):
    """
    Ejemplo mínimo - usa el mismo serializer para create y update
    """
    queryset = Company.objects.all()
    serializer_class = CompanyListSerializer  # Para listar y respuestas
    create_serializer_class = CompanySerializer  # Para create y update
    
    # filter_fields es opcional
    # update_serializer_class es opcional (usa create_serializer_class por defecto)
