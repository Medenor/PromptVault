# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Category and tag management routes (aggregation module).

The endpoint implementations were split into two focused modules:

- ``categories_router`` — every ``/categories/*`` endpoint
- ``tags_router`` — every ``/tags/*`` endpoint

Shared-per-domain helpers live alongside their routes (category helpers in
``categories_router``, tag helpers in ``tags_router``); none are genuinely
shared across both domains, so no separate shared module is needed.

The aggregated ``router`` is exported unchanged so ``routers.__init__`` keeps
importing ``from src.web.routers.tag_category import router``.
"""

from fastapi import APIRouter

from src.web.routers.categories_router import router as _categories_router
from src.web.routers.tags_router import router as _tags_router

# Aggregate the split routers into a single router exported as ``router``.
#
# Both sub-routers use an empty prefix and the shared
# ``["Tag/Category Management"]`` tag, matching the original module. app.py
# mounts this aggregated router under ``/api``.
#
# Category and tag paths occupy disjoint URL namespaces (``/categories/*`` vs
# ``/tags/*``) and different HTTP methods for their dynamic segments, so there
# is no cross-domain path shadowing regardless of include order.
router = APIRouter()
router.include_router(_categories_router)
router.include_router(_tags_router)
