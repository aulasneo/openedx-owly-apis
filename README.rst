openedx-owly-apis
#################

Extra API endpoints for Open edX
********************************

This Django app provides additional REST API endpoints for Open edX to enable advanced features such as analytics, course management, and role inspection. It is intended to be deployed inside an Open edX platform using Tutor.

Installation (via Tutor plugin)
*******************************

Use the Tutor plugin from aulasneo to install and enable these APIs inside your Open edX deployment:

- Repository: https://github.com/aulasneo/tutor-contrib-owly

Quick start with Tutor:

1. Install the plugin

   .. code-block:: bash

      tutor plugins install git+https://github.com/aulasneo/tutor-contrib-owly.git

2. Enable and configure

   .. code-block:: bash

      tutor plugins enable owly
      tutor config save

3. Apply and start

   .. code-block:: bash

      tutor images build openedx
      tutor local launch

Once enabled, the app is included in LMS and exposes endpoints under the paths registered by ``openedx_owly_apis/urls.py``.

API Summary
***********

Base router registrations are defined in ``openedx_owly_apis/urls.py``:

- ``/owly-analytics/`` → ``OpenedXAnalyticsViewSet``
- ``/owly-config/`` → ``OpenedXConfigViewSet``
- ``/owly-courses/`` → ``OpenedXCourseViewSet``
- ``/owly-roles/`` → ``OpenedXRolesViewSet``

Authentication is supported via JWT/Bearer/Session. Specific permissions are enforced per endpoint (see notes below).

v1 Contract Source of Truth
===========================

The v1 API contract is now defined by serializer classes in
``openedx_owly_apis/views/v1/serializers.py``.

- Request bodies and query parameters are validated at the view boundary before
  calling the business logic in ``openedx_owly_apis/operations/``.
- Serializer field names are the authoritative wire contract for v1.
- The API validates and rejects malformed payloads; it does not normalize them.
- Caller-side systems such as ``owly-server`` are responsible for shaping their
  payloads to match the documented serializer contract exactly.

Response Envelope
=================

v1 endpoints now use a consistent envelope pattern:

- Success: ``{"success": true, "data": {...}}``
- Error: ``{"success": false, "error": "<message>", "error_detail": {...}, "error_code": "<code>"}``

``error_detail`` contains the structured machine-readable error information used
for validation feedback and client-side reformulation.

Configuration endpoints (GET)
=============================

ViewSet: ``openedx_owly_apis/views/config_openedx.py``
Requires: Authenticated user.

- ``GET /owly-config/enable_owly_chat``
  Check if the Owly chat feature is enabled via waffle flag. Can check for a specific user by providing an ``email`` query parameter.

Analytics endpoints (GET)
=========================

ViewSet: ``openedx_owly_apis/views/analytics.py``
Requires: Admin or Course Staff permissions.

- ``GET /owly-analytics/overview?course_id=<course-key>``
  Returns overview analytics for a course or platform-wide stats.

- ``GET /owly-analytics/enrollments?course_id=<course-key>``
  Returns detailed enrollment analytics for a course.

- ``GET /owly-analytics/discussions?course_id=<course-key>``
  Returns forum analytics and configuration for a course.

- ``GET /owly-analytics/detailed?course_id=<course-key>``
  Returns a comprehensive, combined analytics payload for a course.

Course management endpoints (POST)
==================================

ViewSet: ``openedx_owly_apis/views/courses.py``
Requires: Authenticated user. Additional role-based permissions per action.

- ``POST /owly-courses/create``
  Create a new course. Requires admin or course creator.

- ``POST /owly-courses/structure``
  Create or edit course structure. Requires admin, course creator, or course staff.

- ``POST /owly-courses/content/html``
  Add HTML content to a vertical. Requires admin, course creator, or course staff.

- ``POST /owly-courses/content/video``
  Add video content to a vertical. Requires admin, course creator, or course staff.

- ``POST /owly-courses/content/problem``
  Add problems/exercises to a vertical using XML. Requires admin, course creator, or course staff.

- ``POST /owly-courses/content/problem/create``
  Create a problem component with structured data (e.g., multiple choice). Requires admin, course creator, or course staff.
  The exact payload contract is defined by ``CreateProblemComponentRequestSerializer``.

- ``POST /owly-courses/content/discussion``
  Add discussion components to a vertical. Requires admin, course creator, or course staff.

- ``POST /owly-courses/content/publish``
  Publish a course or course component (unit, subsection, etc.). Requires admin or course staff.

- ``POST /owly-courses/xblock/delete``
  Delete an XBlock component from a course. Requires admin or course staff.

- ``POST /owly-courses/settings/update``
  Update general course settings (dates, details, etc.). Requires admin or course staff.

- ``POST /owly-courses/settings/advanced``
  Update advanced course settings. Requires admin or course staff.

- ``POST /owly-courses/certificates/configure``
  Configure or activate/deactivate course certificates. Requires admin or course staff.

- ``POST /owly-courses/units/availability/control``
  Control unit availability and due dates. Requires admin or course staff.

Staff management endpoints
--------------------------

- ``POST /owly-courses/staff/manage``
  Add or remove a user from a course staff role (``staff`` or ``course_creator``). Requires admin or course staff.

- ``GET /owly-courses/staff/list?course_id=<course-key>``
  List users with staff roles for a given course. Requires admin or course staff.

Roles endpoint (GET)
====================

ViewSet: ``openedx_owly_apis/views/roles.py``
Requires: Authenticated user.

- ``GET /owly-roles/me?course_id=<course-key>&org=<org-key>``
  Returns the effective role of the authenticated user, including flags for:

  - ``superadmin`` (Django superuser or global staff)
  - ``course_staff`` (instructor/staff/limited_staff for given course)
  - ``course_creator`` (global or org-specific according to platform settings)
  - ``authenticated``

Permissions and Authentication
********************************
- Authentication classes: JWT (``JwtAuthentication``), Bearer (``BearerAuthentication``), Session.
- Permissions:

  - Analytics: ``IsAdminOrCourseStaff``
  - Courses: action-specific guards such as ``IsAdminOrCourseCreator``, ``IsAdminOrCourseCreatorOrCourseStaff``, ``IsAdminOrCourseStaff``
  - Roles: ``IsAuthenticated``
  - Config: ``IsAuthenticated``

Access Control Policy
=====================

The API follows this rule:

- if the underlying Open edX implementation path already performs the correct
  access control for the authenticated user, the API should preserve that
  behavior and avoid adding stricter app-level checks
- if an endpoint uses lower-level access paths that could bypass normal Open edX
  visibility or authoring controls, the API adds the minimum explicit guardrails
  needed to avoid that bypass

Async course structure job polling additionally verifies that the requesting
user is authorized to inspect the cached job state.

Development
***********

- Source paths of interest:

  - Views: ``openedx_owly_apis/views/``
  - Operations logic: ``openedx_owly_apis/operations/``
  - URL routing: ``openedx_owly_apis/urls.py``

License
*******

AGPL-3.0. See `LICENSE.txt <LICENSE.txt>`_.

Project Links
*************

- CI: https://github.com/aulasneo/openedx-owly-apis/actions/workflows/ci.yml
- Issues: https://github.com/aulasneo/openedx-owly-apis/issues
