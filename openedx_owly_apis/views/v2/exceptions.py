"""
Custom exception handlers and error responses for v2 API.

This module provides consistent error handling and response formatting
for the v2 API endpoints.
"""
import logging
from typing import Dict, Any, Optional
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler
from django.core.exceptions import ValidationError as DjangoValidationError
from opaque_keys import InvalidKeyError

logger = logging.getLogger(__name__)


class GradeAPIException(Exception):
    """Base exception for Grade API operations."""
    
    def __init__(self, message: str, error_code: str = None, status_code: int = 400):
        self.message = message
        self.error_code = error_code or 'GRADE_API_ERROR'
        self.status_code = status_code
        super().__init__(self.message)


class GradeNotFoundError(GradeAPIException):
    """Exception raised when a grade is not found."""
    
    def __init__(self, course_id: str, student_username: str, unit_id: str):
        message = f"Grade not found for student '{student_username}' in unit '{unit_id}' of course '{course_id}'"
        super().__init__(message, 'GRADE_NOT_FOUND', 404)


class StudentNotFoundError(GradeAPIException):
    """Exception raised when a student is not found."""
    
    def __init__(self, username: str):
        message = f"Student not found: {username}"
        super().__init__(message, 'STUDENT_NOT_FOUND', 404)


class CourseNotFoundError(GradeAPIException):
    """Exception raised when a course is not found."""
    
    def __init__(self, course_id: str):
        message = f"Course not found: {course_id}"
        super().__init__(message, 'COURSE_NOT_FOUND', 404)


class UnitNotFoundError(GradeAPIException):
    """Exception raised when a unit is not found."""
    
    def __init__(self, unit_id: str):
        message = f"Unit not found: {unit_id}"
        super().__init__(message, 'UNIT_NOT_FOUND', 404)


class InvalidGradeValueError(GradeAPIException):
    """Exception raised when grade values are invalid."""
    
    def __init__(self, grade_value: float, max_grade: float):
        message = f"Invalid grade values: {grade_value}/{max_grade}. Grade cannot exceed maximum grade."
        super().__init__(message, 'INVALID_GRADE_VALUE', 400)


class PermissionDeniedError(GradeAPIException):
    """Exception raised when user lacks permission."""
    
    def __init__(self, action: str, resource: str = None):
        message = f"Permission denied for action '{action}'"
        if resource:
            message += f" on resource '{resource}'"
        super().__init__(message, 'PERMISSION_DENIED', 403)


def format_error_response(
    error_message: str,
    error_code: str = None,
    details: Dict[str, Any] = None,
    status_code: int = 400
) -> Dict[str, Any]:
    """
    Format a consistent error response.
    
    Args:
        error_message (str): Human-readable error message
        error_code (str, optional): Machine-readable error code
        details (Dict[str, Any], optional): Additional error details
        status_code (int): HTTP status code
        
    Returns:
        Dict[str, Any]: Formatted error response
    """
    error_response = {
        'success': False,
        'error': {
            'message': error_message,
            'code': error_code or 'API_ERROR',
            'status_code': status_code
        }
    }
    
    if details:
        error_response['error']['details'] = details
    
    return error_response


def handle_openedx_errors(func):
    """
    Decorator to handle common OpenEdX-related errors.
    
    Args:
        func: Function to wrap
        
    Returns:
        Wrapped function with error handling
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except InvalidKeyError as e:
            logger.error(f"Invalid OpenEdX key error: {e}")
            raise GradeAPIException(
                f"Invalid OpenEdX identifier: {str(e)}",
                'INVALID_OPENEDX_KEY',
                400
            )
        except DjangoValidationError as e:
            logger.error(f"Django validation error: {e}")
            raise GradeAPIException(
                f"Validation error: {str(e)}",
                'VALIDATION_ERROR',
                400
            )
        except Exception as e:
            logger.error(f"Unexpected error in {func.__name__}: {e}")
            raise GradeAPIException(
                f"Unexpected error: {str(e)}",
                'UNEXPECTED_ERROR',
                500
            )
    
    return wrapper


def custom_exception_handler(exc, context):
    """
    Custom exception handler for v2 API.
    
    Args:
        exc: Exception instance
        context: Context information
        
    Returns:
        Response: Formatted error response
    """
    # Call REST framework's default exception handler first
    response = exception_handler(exc, context)
    
    # Handle custom Grade API exceptions
    if isinstance(exc, GradeAPIException):
        error_response = format_error_response(
            error_message=exc.message,
            error_code=exc.error_code,
            status_code=exc.status_code
        )
        return Response(error_response, status=exc.status_code)
    
    # Handle OpenEdX key errors
    if isinstance(exc, InvalidKeyError):
        error_response = format_error_response(
            error_message=f"Invalid OpenEdX identifier: {str(exc)}",
            error_code='INVALID_OPENEDX_KEY',
            status_code=400
        )
        return Response(error_response, status=status.HTTP_400_BAD_REQUEST)
    
    # Handle Django validation errors
    if isinstance(exc, DjangoValidationError):
        error_response = format_error_response(
            error_message=f"Validation error: {str(exc)}",
            error_code='VALIDATION_ERROR',
            status_code=400
        )
        return Response(error_response, status=status.HTTP_400_BAD_REQUEST)
    
    # If response is None, this was not handled by the default handler
    if response is None:
        logger.error(f"Unhandled exception: {exc}")
        error_response = format_error_response(
            error_message="An unexpected error occurred",
            error_code='INTERNAL_SERVER_ERROR',
            status_code=500
        )
        return Response(error_response, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    # Customize the response format for handled exceptions
    if hasattr(response, 'data'):
        custom_data = format_error_response(
            error_message=str(exc),
            error_code='API_ERROR',
            details=response.data,
            status_code=response.status_code
        )
        response.data = custom_data
    
    return response


def log_api_error(
    error: Exception,
    context: Dict[str, Any] = None,
    user: str = None,
    endpoint: str = None
) -> None:
    """
    Log API errors with context information.
    
    Args:
        error (Exception): The error that occurred
        context (Dict[str, Any], optional): Additional context
        user (str, optional): Username of the user
        endpoint (str, optional): API endpoint where error occurred
    """
    log_data = {
        'error_type': type(error).__name__,
        'error_message': str(error),
        'user': user,
        'endpoint': endpoint
    }
    
    if context:
        log_data['context'] = context
    
    logger.error(f"API Error: {log_data}")


class ErrorResponseBuilder:
    """Builder class for creating consistent error responses."""
    
    @staticmethod
    def not_found(resource: str, identifier: str = None) -> Dict[str, Any]:
        """Build a not found error response."""
        message = f"{resource} not found"
        if identifier:
            message += f": {identifier}"
        
        return format_error_response(
            error_message=message,
            error_code=f"{resource.upper()}_NOT_FOUND",
            status_code=404
        )
    
    @staticmethod
    def validation_error(field: str, message: str) -> Dict[str, Any]:
        """Build a validation error response."""
        return format_error_response(
            error_message=f"Validation error for field '{field}': {message}",
            error_code='VALIDATION_ERROR',
            details={'field': field, 'message': message},
            status_code=400
        )
    
    @staticmethod
    def permission_denied(action: str, resource: str = None) -> Dict[str, Any]:
        """Build a permission denied error response."""
        message = f"Permission denied for action '{action}'"
        if resource:
            message += f" on resource '{resource}'"
        
        return format_error_response(
            error_message=message,
            error_code='PERMISSION_DENIED',
            status_code=403
        )
    
    @staticmethod
    def invalid_input(message: str, details: Dict[str, Any] = None) -> Dict[str, Any]:
        """Build an invalid input error response."""
        return format_error_response(
            error_message=message,
            error_code='INVALID_INPUT',
            details=details,
            status_code=400
        )
    
    @staticmethod
    def internal_error(message: str = None) -> Dict[str, Any]:
        """Build an internal server error response."""
        return format_error_response(
            error_message=message or "An internal server error occurred",
            error_code='INTERNAL_SERVER_ERROR',
            status_code=500
        )
