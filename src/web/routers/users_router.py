# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""User search (typeahead) routes.

- ``GET /users/search``  find active users by username/email prefix, for the
  share-modal recipient picker.

Requires authentication (any authenticated user, not owner-only — anyone
composing a share needs to find recipients). When ``AUTH_ENABLED=false`` this
route is not mounted at all (see routing_setup.py).
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status

from src.db.models.user import User
from src.db.repositories.user_repository import UserRepository
from src.db.session import get_db
from src.web.dependencies.bypass import get_current_user_or_default
from src.web.middleware.rate_limit import limiter, read_limit
from src.web.models.sharing_responses import UserSearchResponse, UserSuggestion

router = APIRouter(
    prefix="/users",
    tags=["Users"],
)


@router.get(
    "/search",
    summary="Search active users by username/email prefix",
    description="""
    Typeahead lookup for the sharing recipient picker.

    **Authentication:** required (any authenticated user).

    **Constraints:**
    - `q` minimum 2 characters
    - Up to 10 results
    - Active accounts only
    - Matches username OR email prefix, but the response contains
      usernames only (no email field)
    """,
    responses={
        200: {"description": "Matching users (usernames only)"},
        400: {"description": "q is too short"},
        401: {"description": "Authentication required"},
        429: {"description": "Rate limit exceeded"},
    },
)
@limiter.limit(read_limit)
async def search_users(
    request: Request,
    response: Response,
    q: str = Query(..., description="Username or email prefix, min 2 chars"),
    user: User = Depends(get_current_user_or_default),
    db=Depends(get_db),
):
    """Search active users by username/email prefix (authenticated)."""
    if len(q) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Search query must be at least 2 characters",
        )

    user_repo = UserRepository(db)
    matches = user_repo.search_active_by_prefix(q, limit=10)

    return UserSearchResponse(
        users=[UserSuggestion(id=u.id, username=u.username) for u in matches]
    )
