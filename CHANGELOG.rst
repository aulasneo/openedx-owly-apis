Change Log
##########

..
   All enhancements and patches to openedx_owly_apis will be documented
   in this file.  It adheres to the structure of https://keepachangelog.com/ ,
   but in reStructuredText instead of Markdown (for ease of incorporation into
   Sphinx documentation and the PyPI description).

   This project adheres to Semantic Versioning (https://semver.org/).

.. There should always be an "Version 1.0.0 (2025-08-27)" section for changes pending release.

Version 1.0.0 (2025-08-27)
**********

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
