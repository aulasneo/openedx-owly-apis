from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet


class BaseCRUDViewSet(ModelViewSet):
    """
    Base class for CRUD ViewSets that provides standard functionality
    for creating and updating objects with separate serializers.

    Required attributes in child classes:
    - queryset: Model QuerySet
    - serializer_class: Serializer for listing/reading (used for responses)
    - create_serializer_class: Serializer for creating objects
    - update_serializer_class: Serializer for updating objects (optional, uses create_serializer_class by default)
    - filter_fields: Fields for filtering (optional)
    - permission_classes: Permission classes (optional)
    """

    filter_backends = (DjangoFilterBackend,)
    filter_fields = ()

    # Serializers that must be defined in child classes
    create_serializer_class = None
    update_serializer_class = None

    def get_create_serializer_class(self):
        """Returns the serializer for creating objects"""
        if self.create_serializer_class is None:
            raise NotImplementedError(
                f"{self.__class__.__name__} must define 'create_serializer_class'"
            )
        return self.create_serializer_class

    def get_update_serializer_class(self):
        """Returns the serializer for updating objects"""
        if self.update_serializer_class is not None:
            return self.update_serializer_class
        return self.get_create_serializer_class()

    def create(self, request, *args, **kwargs):
        """Create a new object"""
        serializer_class = self.get_create_serializer_class()
        serializer = serializer_class(data=request.data)

        if serializer.is_valid():
            serializer.save()
            # Use response serializer (serializer_class) for the response
            response_serializer = self.get_serializer(instance=serializer.instance)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        """Update an existing object"""
        instance = self.get_object()
        serializer_class = self.get_update_serializer_class()
        partial = kwargs.pop('partial', False)

        serializer = serializer_class(instance, data=request.data, partial=partial)

        if serializer.is_valid():
            serializer.save()
            # Use response serializer (serializer_class) for the response
            response_serializer = self.get_serializer(instance=serializer.instance)
            return Response(response_serializer.data, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, *args, **kwargs):
        """Partial update (PATCH)"""
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)


class BaseAPIViewSet(BaseCRUDViewSet):
    """
    Base class for API ViewSets that don't use Django models directly.

    This class provides CRUD functionality for APIs that interact with external services
    (like OpenEdX) instead of Django models. Child classes must implement the logic methods.

    Required attributes in child classes:
    - serializer_class: Serializer for listing/reading (used for responses)
    - create_serializer_class: Serializer for creating objects
    - update_serializer_class: Serializer for updating objects (optional)
    - permission_classes: Permission classes

    Required methods in child classes:
    - perform_list_logic(self, validated_params) -> dict
    - perform_create_logic(self, validated_data) -> dict
    - perform_update_logic(self, pk, validated_data) -> dict
    - perform_destroy_logic(self, pk, validated_params) -> dict
    """

    # Override queryset to None since we don't use Django models
    queryset = None

    def list(self, request):
        """List objects using external API logic"""
        # Get query parameters for validation if needed
        query_params = dict(request.query_params)

        # Call the logic method that child classes must implement
        result = self.perform_list_logic(query_params)

        status_code = status.HTTP_200_OK if result.get('success') else status.HTTP_400_BAD_REQUEST
        return Response(result, status=status_code)

    def create(self, request, *args, **kwargs):
        """Create a new object using external API logic"""
        # Use serializer for validation
        serializer_class = self.get_create_serializer_class()
        serializer = serializer_class(data=request.data)

        if not serializer.is_valid():
            return Response({
                'success': False,
                'message': 'Validation failed',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        validated_data = serializer.validated_data

        # Call the logic method that child classes must implement
        result = self.perform_create_logic(validated_data)

        status_code = status.HTTP_201_CREATED if result.get('success') else status.HTTP_400_BAD_REQUEST
        return Response(result, status=status_code)

    def update(self, request, pk=None, *args, **kwargs):
        """Update an existing object using external API logic"""
        if not pk:
            return Response({
                'success': False,
                'message': 'ID is required',
                'error_code': 'missing_id'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Use serializer for validation
        serializer_class = self.get_update_serializer_class()
        partial = kwargs.get('partial', False)
        serializer = serializer_class(data=request.data, partial=partial)

        if not serializer.is_valid():
            return Response({
                'success': False,
                'message': 'Validation failed',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        validated_data = serializer.validated_data

        # Call the logic method that child classes must implement
        result = self.perform_update_logic(pk, validated_data)

        status_code = status.HTTP_200_OK if result.get('success') else status.HTTP_400_BAD_REQUEST
        return Response(result, status=status_code)

    def destroy(self, request, pk=None, *args, **kwargs):
        """Delete an object using external API logic"""
        if not pk:
            return Response({
                'success': False,
                'message': 'ID is required',
                'error_code': 'missing_id'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Get query parameters for additional validation if needed
        query_params = dict(request.query_params)

        # Call the logic method that child classes must implement
        result = self.perform_destroy_logic(pk, query_params)

        status_code = status.HTTP_200_OK if result.get('success') else status.HTTP_400_BAD_REQUEST
        return Response(result, status=status_code)

    # Abstract methods that child classes must implement
    def perform_list_logic(self, query_params):
        """
        Implement the logic for listing objects.

        Args:
            query_params (dict): Query parameters from the request

        Returns:
            dict: Response with success/error and data
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement 'perform_list_logic'"
        )

    def perform_create_logic(self, validated_data):
        """
        Implement the logic for creating objects.

        Args:
            validated_data (dict): Validated data from serializer

        Returns:
            dict: Response with success/error and created object data
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement 'perform_create_logic'"
        )

    def perform_update_logic(self, pk, validated_data):
        """
        Implement the logic for updating objects.

        Args:
            pk: Primary key/ID of the object to update
            validated_data (dict): Validated data from serializer

        Returns:
            dict: Response with success/error and updated object data
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement 'perform_update_logic'"
        )

    def perform_destroy_logic(self, pk, query_params):
        """
        Implement the logic for deleting objects.

        Args:
            pk: Primary key/ID of the object to delete
            query_params (dict): Query parameters from the request

        Returns:
            dict: Response with success/error and deletion confirmation
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement 'perform_destroy_logic'"
        )
