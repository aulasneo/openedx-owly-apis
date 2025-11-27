"""
Swagger/OpenAPI schemas and documentation for v2 API endpoints.

This module contains all the Swagger documentation schemas separated from
the view logic to maintain clean code principles.
"""
from drf_yasg import openapi
from .serializers import GradeCreateSerializer, GradeUpdateSerializer, GradeResponseSerializer


class GradeSwaggerSchemas:
    """Swagger schemas for Grade endpoints."""
    
    # Common parameters
    COURSE_ID_PARAM = openapi.Parameter(
        'course_id',
        openapi.IN_QUERY,
        description="Course identifier (e.g., course-v1:ORG+NUM+RUN)",
        type=openapi.TYPE_STRING,
        required=True
    )
    
    STUDENT_USERNAME_PARAM = openapi.Parameter(
        'student_username',
        openapi.IN_QUERY,
        description="Student username",
        type=openapi.TYPE_STRING,
        required=True
    )
    
    UNIT_ID_PARAM = openapi.Parameter(
        'unit_id',
        openapi.IN_QUERY,
        description="Unit identifier (e.g., block-v1:ORG+NUM+RUN+type@TYPE+block@BLOCK)",
        type=openapi.TYPE_STRING,
        required=True
    )
    
    # Filter parameters
    COURSE_ID_FILTER_PARAM = openapi.Parameter(
        'course_id',
        openapi.IN_QUERY,
        description="Filter by course ID",
        type=openapi.TYPE_STRING,
        required=False
    )
    
    STUDENT_USERNAME_FILTER_PARAM = openapi.Parameter(
        'student_username',
        openapi.IN_QUERY,
        description="Filter by student username",
        type=openapi.TYPE_STRING,
        required=False
    )
    
    UNIT_ID_FILTER_PARAM = openapi.Parameter(
        'unit_id',
        openapi.IN_QUERY,
        description="Filter by unit ID",
        type=openapi.TYPE_STRING,
        required=False
    )
    
    MIN_GRADE_PARAM = openapi.Parameter(
        'min_grade',
        openapi.IN_QUERY,
        description="Filter by minimum grade value",
        type=openapi.TYPE_NUMBER,
        required=False
    )
    
    MAX_GRADE_FILTER_PARAM = openapi.Parameter(
        'max_grade_filter',
        openapi.IN_QUERY,
        description="Filter by maximum grade value",
        type=openapi.TYPE_NUMBER,
        required=False
    )
    
    PAGE_PARAM = openapi.Parameter(
        'page',
        openapi.IN_QUERY,
        description="Page number",
        type=openapi.TYPE_INTEGER,
        required=False,
        default=1
    )
    
    PAGE_SIZE_PARAM = openapi.Parameter(
        'page_size',
        openapi.IN_QUERY,
        description="Number of items per page (max 100)",
        type=openapi.TYPE_INTEGER,
        required=False,
        default=20
    )
    
    # Response schemas
    SUCCESS_RESPONSE_SCHEMA = openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'success': openapi.Schema(type=openapi.TYPE_BOOLEAN),
            'message': openapi.Schema(type=openapi.TYPE_STRING),
            'data': openapi.Schema(type=openapi.TYPE_OBJECT)
        }
    )
    
    ERROR_RESPONSE_SCHEMA = openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'success': openapi.Schema(type=openapi.TYPE_BOOLEAN),
            'error': openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'code': openapi.Schema(type=openapi.TYPE_STRING),
                    'status_code': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'details': openapi.Schema(type=openapi.TYPE_OBJECT)
                }
            )
        }
    )
    
    LIST_RESPONSE_SCHEMA = openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'success': openapi.Schema(type=openapi.TYPE_BOOLEAN),
            'data': openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'grades': openapi.Schema(
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Schema(type=openapi.TYPE_OBJECT)
                    ),
                    'pagination': openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'page': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'page_size': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'total_pages': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'total_items': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'has_next': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                            'has_previous': openapi.Schema(type=openapi.TYPE_BOOLEAN)
                        }
                    ),
                    'filters': openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'course_id': openapi.Schema(type=openapi.TYPE_STRING),
                            'student_username': openapi.Schema(type=openapi.TYPE_STRING),
                            'unit_id': openapi.Schema(type=openapi.TYPE_STRING),
                            'min_grade': openapi.Schema(type=openapi.TYPE_NUMBER),
                            'max_grade_filter': openapi.Schema(type=openapi.TYPE_NUMBER)
                        }
                    )
                }
            )
        }
    )
    
    # Common responses
    COMMON_RESPONSES = {
        400: openapi.Response(
            description="Invalid input data",
            schema=ERROR_RESPONSE_SCHEMA
        ),
        401: openapi.Response(
            description="Authentication required",
            schema=ERROR_RESPONSE_SCHEMA
        ),
        403: openapi.Response(
            description="Permission denied",
            schema=ERROR_RESPONSE_SCHEMA
        ),
        404: openapi.Response(
            description="Resource not found",
            schema=ERROR_RESPONSE_SCHEMA
        ),
        500: openapi.Response(
            description="Internal server error",
            schema=ERROR_RESPONSE_SCHEMA
        )
    }
    
    @classmethod
    def get_create_schema(cls):
        """Get schema for create grade endpoint."""
        return {
            'operation_summary': "Create a new grade",
            'operation_description': "Create a new grade for a student in a specific unit/problem",
            'request_body': GradeCreateSerializer,
            'responses': {
                201: openapi.Response(
                    description="Grade created successfully"
                ),
                **cls.COMMON_RESPONSES
            },
            'tags': ['Grades']
        }
    
    @classmethod
    def get_retrieve_schema(cls):
        """Get schema for retrieve grade endpoint."""
        return {
            'operation_summary': "Get a specific grade",
            'operation_description': "Retrieve a grade for a specific student and unit",
            'manual_parameters': [
                cls.COURSE_ID_PARAM,
                cls.STUDENT_USERNAME_PARAM,
                cls.UNIT_ID_PARAM
            ],
            'responses': {
                200: openapi.Response(
                    description="Grade retrieved successfully"
                ),
                **cls.COMMON_RESPONSES
            },
            'tags': ['Grades']
        }
    
    @classmethod
    def get_update_schema(cls):
        """Get schema for update grade endpoint."""
        return {
            'operation_summary': "Update a grade",
            'operation_description': "Update an existing grade for a student",
            'manual_parameters': [
                cls.COURSE_ID_PARAM,
                cls.STUDENT_USERNAME_PARAM,
                cls.UNIT_ID_PARAM
            ],
            'request_body': GradeUpdateSerializer,
            'responses': {
                200: openapi.Response(
                    description="Grade updated successfully"
                ),
                **cls.COMMON_RESPONSES
            },
            'tags': ['Grades']
        }
    
    @classmethod
    def get_partial_update_schema(cls):
        """Get schema for partial update grade endpoint."""
        return {
            'operation_summary': "Partially update a grade",
            'operation_description': "Partially update an existing grade for a student",
            'manual_parameters': [
                cls.COURSE_ID_PARAM,
                cls.STUDENT_USERNAME_PARAM,
                cls.UNIT_ID_PARAM
            ],
            'request_body': GradeUpdateSerializer,
            'responses': {
                200: openapi.Response(
                    description="Grade updated successfully"
                ),
                **cls.COMMON_RESPONSES
            },
            'tags': ['Grades']
        }
    
    @classmethod
    def get_delete_schema(cls):
        """Get schema for delete grade endpoint."""
        return {
            'operation_summary': "Delete a grade by ID",
            'operation_description': "Delete a grade using its composite ID (course_id+student_username+unit_id)",
            'responses': {
                204: openapi.Response(
                    description="Grade deleted successfully"
                ),
                **cls.COMMON_RESPONSES
            },
            'tags': ['Grades']
        }
    
    @classmethod
    def get_list_schema(cls):
        """Get schema for list grades endpoint."""
        return {
            'operation_summary': "List grades",
            'operation_description': "List grades with optional filtering and pagination",
            'manual_parameters': [
                cls.COURSE_ID_FILTER_PARAM,
                cls.STUDENT_USERNAME_FILTER_PARAM,
                cls.UNIT_ID_FILTER_PARAM,
                cls.MIN_GRADE_PARAM,
                cls.MAX_GRADE_FILTER_PARAM,
                cls.PAGE_PARAM,
                cls.PAGE_SIZE_PARAM
            ],
            'responses': {
                200: openapi.Response(
                    description="Grades listed successfully"
                ),
                **cls.COMMON_RESPONSES
            },
            'tags': ['Grades']
        }


# Decorators para usar en las views
def swagger_create_grade(func):
    """Decorator for create grade endpoint."""
    from drf_yasg.utils import swagger_auto_schema
    return swagger_auto_schema(**GradeSwaggerSchemas.get_create_schema())(func)


def swagger_retrieve_grade(func):
    """Decorator for retrieve grade endpoint."""
    from drf_yasg.utils import swagger_auto_schema
    return swagger_auto_schema(**GradeSwaggerSchemas.get_retrieve_schema())(func)


def swagger_update_grade(func):
    """Decorator for update grade endpoint."""
    from drf_yasg.utils import swagger_auto_schema
    return swagger_auto_schema(**GradeSwaggerSchemas.get_update_schema())(func)


def swagger_partial_update_grade(func):
    """Decorator for partial update grade endpoint."""
    from drf_yasg.utils import swagger_auto_schema
    return swagger_auto_schema(**GradeSwaggerSchemas.get_partial_update_schema())(func)


def swagger_delete_grade(func):
    """Decorator for delete grade endpoint."""
    from drf_yasg.utils import swagger_auto_schema
    return swagger_auto_schema(**GradeSwaggerSchemas.get_delete_schema())(func)


def swagger_list_grades(func):
    """Decorator for list grades endpoint."""
    from drf_yasg.utils import swagger_auto_schema
    return swagger_auto_schema(**GradeSwaggerSchemas.get_list_schema())(func)
