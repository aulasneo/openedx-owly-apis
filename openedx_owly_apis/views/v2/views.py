from typing import Dict, Any
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from openedx_owly_apis.utils.base_views import BaseAPIViewSet
from rest_framework.permissions import IsAuthenticated
from openedx_owly_apis.permissions import  IsAdminOrCourseStaff
from .serializers import (
    ContentGroupSerializer,
    ContentGroupListSerializer,
    ContentGroupUpdateSerializer,
    CohortAssignmentSerializer
)


class ContentGroupViewSet(BaseAPIViewSet):
    """
    ViewSet for managing OpenEdX content groups and their assignment to cohorts.
    
    Content groups allow instructors to create different versions of course content
    for different groups of students, typically organized by cohorts.
    """
    
    # Configuration for BaseAPIViewSet
    permission_classes = [IsAuthenticated, IsAdminOrCourseStaff]
    serializer_class = ContentGroupListSerializer  # For list/read operations
    create_serializer_class = ContentGroupSerializer  # For create operations
    update_serializer_class = ContentGroupUpdateSerializer  # For update operations
    
    # Implement the required logic methods from BaseAPIViewSet
    
    def perform_list_logic(self, query_params):
        """List all content groups for a course"""
        from openedx_owly_apis.operations.courses import list_content_groups_logic
        
        # Extract course_id from query params (handle both string and list)
        course_id = query_params.get('course_id')
        if isinstance(course_id, list):
            course_id = course_id[0] if course_id else None
            
        if not course_id:
            return {
                'success': False,
                'message': 'course_id parameter is required',
                'error_code': 'missing_course_id'
            }
        
        return list_content_groups_logic(
            course_id=course_id,
            user_identifier=self.request.user.id
        )
    
    def perform_create_logic(self, validated_data):
        """Create a new content group"""
        from openedx_owly_apis.operations.courses import create_content_group_logic
        
        return create_content_group_logic(
            course_id=validated_data['course_id'],
            name=validated_data['name'],
            description=validated_data.get('description', ''),
            user_identifier=self.request.user.id
        )
    
    def perform_update_logic(self, pk, validated_data):
        """Update an existing content group"""
        from openedx_owly_apis.operations.courses import update_content_group_logic
        
        return update_content_group_logic(
            course_id=validated_data['course_id'],
            group_id=pk,
            name=validated_data.get('name'),
            description=validated_data.get('description'),
            user_identifier=self.request.user.id
        )
    
    def perform_destroy_logic(self, pk, query_params):
        """Delete a content group"""
        from openedx_owly_apis.operations.courses import delete_content_group_logic
        
        # Extract course_id from query params (handle both string and list)
        course_id = query_params.get('course_id')
        if isinstance(course_id, list):
            course_id = course_id[0] if course_id else None
        
        if not course_id:
            return {
                'success': False,
                'message': 'course_id parameter is required',
                'error_code': 'missing_course_id'
            }
        
        return delete_content_group_logic(
            course_id=course_id,
            group_id=pk,
            user_identifier=self.request.user.id
        )


class ContentGroupCohortAssignmentViewSet(BaseAPIViewSet):
    """
    ViewSet for managing assignments between content groups and cohorts.
    
    This handles the relationship/assignment operations between content groups and cohorts,
    following proper CRUD patterns for assignment management.
    """
    
    # Configuration for BaseAPIViewSet
    permission_classes = [IsAuthenticated, IsAdminOrCourseStaff]
    serializer_class = CohortAssignmentSerializer  # For list/read operations
    create_serializer_class = CohortAssignmentSerializer  # For create operations
    update_serializer_class = CohortAssignmentSerializer  # For update operations
    
    # Implement the required logic methods from BaseAPIViewSet
    
    def perform_list_logic(self, query_params):
        """List all content group to cohort assignments for a course"""
        from openedx_owly_apis.operations.courses import list_content_group_cohort_assignments_logic
        
        # Extract course_id from query params (handle both string and list)
        course_id = query_params.get('course_id')
        if isinstance(course_id, list):
            course_id = course_id[0] if course_id else None
        
        if not course_id:
            return {
                'success': False,
                'message': 'course_id parameter is required',
                'error_code': 'missing_course_id'
            }
        
        return list_content_group_cohort_assignments_logic(
            course_id=course_id,
            user_identifier=self.request.user.id
        )
    
    def perform_create_logic(self, validated_data):
        """Create a new assignment (assign content group to cohort)"""
        from openedx_owly_apis.operations.courses import assign_content_group_to_cohort_logic
        
        return assign_content_group_to_cohort_logic(
            course_id=validated_data['course_id'],
            content_group_id=validated_data['content_group_id'],
            cohort_id=validated_data['cohort_id'],
            user_identifier=self.request.user.id
        )
    
    def perform_update_logic(self, pk, validated_data):
        """Update logic not implemented for assignments"""
        return {
            'success': False,
            'message': 'Update operation not supported for assignments',
            'error_code': 'operation_not_supported'
        }
    
    def destroy(self, request, pk=None, *args, **kwargs):
        """
        Override destroy to handle assignments without requiring pk.
        Assignments are identified by course_id + content_group_id + cohort_id.
        """
        from rest_framework.response import Response
        from rest_framework import status
        
        # Get query parameters
        query_params = dict(request.query_params)
        
        # Call our custom destroy logic
        result = self.perform_destroy_logic(pk, query_params)
        
        status_code = status.HTTP_200_OK if result.get('success') else status.HTTP_400_BAD_REQUEST
        return Response(result, status=status_code)
    
    def perform_destroy_logic(self, pk, query_params):
        """Delete an assignment (unassign content group from cohort)"""
        from openedx_owly_apis.operations.courses import unassign_content_group_from_cohort_logic
        
        # For assignments, we use query params since we don't have a single pk
        # Extract values from query params (handle both string and list)
        course_id = query_params.get('course_id')
        if isinstance(course_id, list):
            course_id = course_id[0] if course_id else None
            
        content_group_id = query_params.get('content_group_id')
        if isinstance(content_group_id, list):
            content_group_id = content_group_id[0] if content_group_id else None
            
        cohort_id = query_params.get('cohort_id')
        if isinstance(cohort_id, list):
            cohort_id = cohort_id[0] if cohort_id else None
        
        if not all([course_id, content_group_id, cohort_id]):
            return {
                'success': False,
                'message': 'course_id, content_group_id, and cohort_id parameters are required',
                'error_code': 'missing_parameters'
            }
        
        return unassign_content_group_from_cohort_logic(
            course_id=course_id,
            content_group_id=int(content_group_id),
            cohort_id=int(cohort_id),
            user_identifier=self.request.user.id
        )
    