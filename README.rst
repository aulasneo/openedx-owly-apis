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
- ``/owly-courses/`` → ``OpenedXCourseViewSet``
- ``/owly-roles/`` → ``OpenedXRolesViewSet``

Authentication is supported via JWT/Bearer/Session. Specific permissions are enforced per endpoint (see notes below).

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
  Add problems/exercises to a vertical. Requires admin, course creator, or course staff.

- ``POST /owly-courses/content/discussion``
  Add discussion components to a vertical. Requires admin, course creator, or course staff.

- ``POST /owly-courses/settings/update``
  Update general course settings (dates, details, etc.). Requires admin or course staff.

- ``POST /owly-courses/settings/advanced``
  Update advanced course settings. Requires admin or course staff.

- ``POST /owly-courses/certificates/configure``
  Configure course certificates. Requires admin or course staff.

- ``POST /owly-courses/units/availability/control``
  Control unit availability and due dates. Requires admin or course staff.

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
*****************************

- Authentication classes: JWT (``JwtAuthentication``), Bearer (``BearerAuthentication``), Session.
- Permissions:

  - Analytics: ``IsAdminOrCourseStaff``
  - Courses: action-specific guards such as ``IsAdminOrCourseCreator``, ``IsAdminOrCourseCreatorOrCourseStaff``, ``IsAdminOrCourseStaff``
  - Roles: ``IsAuthenticated``

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

