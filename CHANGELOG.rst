Change Log
##########

..
   All enhancements and patches to openedx_owly_apis will be documented
   in this file.  It adheres to the structure of https://keepachangelog.com/ ,
   but in reStructuredText instead of Markdown (for ease of incorporation into
   Sphinx documentation and the PyPI description).

   This project adheres to Semantic Versioning (https://semver.org/).

.. There should always be an "Version 1.4.0 (2025-10-22)" section for changes pending release.

Version 1.6.0 (2025-12-11)
**************************

Added
=====

* **Grade Management**:
  - Add grade management operations for student assessments

Changed
=======

* Simplify API URL structure by removing redundant path prefixes
* Standardize whitespace and improve logging in grade management operations
* Extract parse_grade_id function to validators module with comprehensive test coverage

Version 1.5.0 (2025-10-31)
**************************

Added
=====

* **Course Tree API**:
  - Add endpoint with search and traversal capabilities
  - Implement CMS-first course tree building with modulestore traversal and debug logging
  - Support draft and published modulestore branches

* **Unit Contents**:
  - Add API endpoint to fetch unit contents and their raw data

* **ORA Grading**:
  - Add student response extraction and improve workflow handling

Changed
=======

* Refactor permission to ``IsAdminOrCourseStaff``

Fixed
=====

* Update permission requirements for unit contents endpoint

Version 1.4.0 (2025-10-22)
**************************

Added
=====

* **Course Staff Management APIs**:
  - ``POST /staff/manage``: Add or remove users from course staff roles (staff, course_creator)
  - ``GET /staff/list``: List all users with course staff roles, with optional role filtering
  - Support for simplified role types: staff and course_creator roles
  - Enhanced role management with detailed user information

* **Open Response Assessment (ORA) Management**:
  - ``POST /content/ora``: Create ORA components with full configuration support
  - ``POST /content/ora/grade``: Grade ORA submissions using staff assessment
  - ``GET /content/ora/details``: Get detailed ORA information including rubric structure
  - ``GET /content/ora/submissions``: List all submissions for an ORA component
  - Support for peer assessment, self-assessment, and staff assessment workflows
  - Comprehensive rubric management and grading capabilities

* **Cohort Management APIs**:
  - ``POST /cohorts/create``: Create new cohorts with manual or random assignment
  - ``GET /cohorts/list``: List all cohorts in a course
  - ``POST /cohorts/members/add``: Add users to specific cohorts
  - ``POST /cohorts/members/remove``: Remove users from cohorts
  - ``GET /cohorts/members/list``: List all members of a cohort
  - ``DELETE /cohorts/delete``: Delete cohorts and their memberships

Changed
=======

* Reorganized course management endpoints with clearer permission models
* Enhanced error handling and validation across all endpoints
* Improved documentation with detailed examples and error scenarios
* Standardized response formats across all API endpoints
* Improved submission retrieval logic and error handling in ORA functions
* Refactored ORA content logic and tests for clarity

Documentation
=============

* Added comprehensive API documentation for course staff management
* Detailed ORA workflow documentation with grading examples
* Cohort management usage examples and best practices
* Enhanced endpoint documentation with request/response examples
* Fixed changelog header underline length
* Formatting cleanups and clarity improvements in ORA documentation

Version 1.2.0 (2025-09-23)
**************************

Added
=====

- Add course staff management endpoints and enhance waffle flag checks (ed44fa2)
- Add OpenedXConfigViewSet for managing Owly chat feature toggle (5b480a2)

Changed
=======

- Remove unused authentication and permission imports from config view (d2e6e98)
- Remove authentication and permission classes from OpenedXConfigViewSet (1146370)

Documentation
=============

- Improve API documentation formatting and clarity for course staff endpoints (db63cbe)


Version 1.1.0 (2025-09-08)
**************************

Added
=====

* Problem creation endpoints and logic for multiple problem types:
  - Support for dropdown problems with XML generation
  - Enhanced XML generation for multiple choice problems with input validation and escaping
  - ``POST /add_problem_content`` endpoint for problem integration
* Content publishing functionality:
  - ``POST /publish`` endpoint for publishing courses and units
  - Content publishing logic with modulestore integration
* XBlock management capabilities:
  - ``POST /delete_xblock`` endpoint for removing course components
  - Delete XBlock logic with modulestore integration
* Certificate management enhancements:
  - Toggle certificate logic for managing certificate active status
  - Certificate activation/deactivation integration in course configuration
  - Simplified certificate activation logic without certificate_id requirement

Changed
=======

* Enhanced XML generation for problem types with improved input validation and error handling
* Reorganized imports in courses.py for better code readability
* Updated delete_xblock logic to use acting_user parameter consistently

Fixed
=====

* Corrected delete_xblock logic parameter usage from user_identifier to acting_user

Version 1.0.0 (2025-08-27)
***************************

Added
=====

* DRF ViewSets and endpoints for analytics: ``overview``, ``enrollments``, ``discussions``, ``detailed`` under ``/owly-analytics/`` (see ``openedx_owly_apis/views/analytics.py``).
* Course management endpoints under ``/owly-courses/`` (see ``openedx_owly_apis/views/courses.py``):
  - ``POST /create``: create course.
  - ``POST /structure``: create/edit course structure (chapters, subsections, verticals).
  - ``POST /content/html``: add HTML component to vertical.
  - ``POST /content/video``: add Video component to vertical.
  - ``POST /content/problem``: add Problem component to vertical.
  - ``POST /content/discussion``: add Discussion component to vertical.
  - ``POST /settings/update``: update course settings (dates/details/etc.).
  - ``POST /settings/advanced``: update advanced settings.
  - ``POST /certificates/configure``: enable/configure certificates.
  - ``POST /units/availability/control``: control unit availability and due dates.
* Roles endpoint under ``/owly-roles/me`` to determine effective user role (see ``openedx_owly_apis/views/roles.py``).
* Authentication via ``JwtAuthentication`` and ``SessionAuthentication`` across ViewSets.

Documentation
=============

* README: comprehensive API overview, endpoint list, and Tutor plugin installation instructions for ``tutor-contrib-owly``.
