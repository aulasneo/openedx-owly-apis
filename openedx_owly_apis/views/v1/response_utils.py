"""Shared response helpers for v1 APIs."""

from rest_framework import status
from rest_framework.response import Response


def _error_payload(message, code, details=None):
    structured_error = {
        "code": code,
        "message": message,
    }
    if details:
        structured_error["details"] = details

    payload = {
        "success": False,
        "error": message,
        "error_detail": structured_error,
    }
    # Transitional mirrors used by current tests/callers.
    payload["error_code"] = code
    return payload


def error_response(message, code, *, details=None, http_status=status.HTTP_400_BAD_REQUEST):
    return Response(_error_payload(message, code, details), status=http_status)


def serializer_error_response(serializer, *, code="validation_error"):
    return error_response(
        "Validation failed",
        code,
        details=serializer.errors,
        http_status=status.HTTP_400_BAD_REQUEST,
    )


def success_response(data, *, http_status=status.HTTP_200_OK):
    payload = {
        "success": True,
        "data": data,
    }
    # Transitional mirrors used by current tests/callers.
    if isinstance(data, dict):
        payload.update(data)
    return Response(payload, status=http_status)


def logic_result_response(result, *, success_status=status.HTTP_200_OK, error_status=status.HTTP_400_BAD_REQUEST):
    if not isinstance(result, dict):
        return error_response(
            "Unexpected response type from business logic",
            "invalid_logic_result",
            details={"type": type(result).__name__},
            http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    if result.get("success") is False or result.get("error"):
        code = result.get("error")
        if isinstance(code, dict):
            code = "operation_failed"
        code = code or "operation_failed"
        details = {
            key: value
            for key, value in result.items()
            if key not in {"success", "error", "message"}
        }
        return error_response(
            result.get("message", "Operation failed"),
            code,
            details=details or None,
            http_status=error_status,
        )

    return success_response(result, http_status=success_status)
