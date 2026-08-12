# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Prompt repository for PromptVault.

This module provides data access layer for Prompt model with advanced
search, filtering, and relationship management capabilities.
"""

import logging
import re
from typing import List, NamedTuple, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, and_, func, select, text
from sqlalchemy.exc import OperationalError, ProgrammingError

from src.db.models import Prompt, PromptShare, Tag, Category, PromptBranch
from src.db.repositories.base import BaseRepository
from src.db.search.fts import (
    MATCH_START,
    active_dialect,
    sanitize_fts_query,
    fts5_snippet_args,
    ts_headline_options,
)

logger = logging.getLogger(__name__)

# bm25()/ts_rank column weights: title > prompt > note (data-model.md, FR-001).
_RANK_WEIGHT_TITLE = 10.0
_RANK_WEIGHT_PROMPT = 4.0
_RANK_WEIGHT_NOTE = 1.0


class RankedMatch(NamedTuple):
    """One FTS hit: relevance rank (lower = more relevant) and its snippet."""

    rank: float
    match_context: Optional[str]


class PromptRepository(BaseRepository[Prompt]):
    """Repository for Prompt model with search and filtering.

    Provides methods for CRUD operations plus advanced features like:
    - Full-text search (LIKE-based, FTS deferred to future phase)
    - Category filtering
    - Tag filtering
    - Favorite filtering
    - Eager loading of relationships
    """

    def __init__(self, session: Session):
        """Initialize PromptRepository.

        Args:
            session: Database session
        """
        super().__init__(Prompt, session)

    def _apply_visibility_filter(
        self,
        q,
        visible_to_user_id: Optional[str],
        shared_only: bool,
    ):
        """Apply the owned/shared/legacy-public visibility scope to a query.

        Args:
            q: Base SQLAlchemy query over Prompt
            visible_to_user_id: Scope to this user's owned + shared +
                legacy-public prompts; None leaves the query unscoped
                (admin/anonymous-mode behavior — sees everything)
            shared_only: When True (and visible_to_user_id is set), narrow to
                the explicit-grant branch only, excluding legacy_public and
                owned prompts (the "shared with me" filter)

        Returns:
            The query with the visibility filter applied (or unchanged if
            visible_to_user_id is None)
        """
        if visible_to_user_id is None:
            return q

        shared_subquery = select(PromptShare.prompt_id).where(
            PromptShare.grantee_user_id == visible_to_user_id
        )

        if shared_only:
            return q.filter(Prompt.id.in_(shared_subquery))

        return q.filter(
            or_(
                Prompt.user_id == visible_to_user_id,
                Prompt.legacy_public.is_(True),
                Prompt.id.in_(shared_subquery),
            )
        )

    def _fts_matches(self, query: str) -> Optional[Dict[int, RankedMatch]]:
        """Run the dialect-native FTS lookup for ``query``.

        Returns a mapping of prompt id -> (rank, match_context) covering every
        row the FTS engine matches, or ``None`` when the query sanitizes to
        empty or the underlying dialect isn't handled (caller falls back to
        the substring path per FR-010/FR-011).

        Raises whatever the driver raises on a genuine FTS operational/parse
        error; callers wrap this in try/except to implement the fallback
        (FR-010).
        """
        safe_query = sanitize_fts_query(query)
        if safe_query is None:
            return None

        dialect = active_dialect(self.session)
        matches: Dict[int, RankedMatch] = {}

        if dialect == "sqlite":
            match_expr = safe_query.to_fts5_match()
            # Snippet from the "prompt" body column (index 1 of title,prompt,note).
            snippet_col, start_sel, end_sel, ellipsis, tokens = fts5_snippet_args(1)
            rows = self.session.execute(
                text(
                    """
                    SELECT
                        prompts_fts.rowid AS id,
                        bm25(prompts_fts, :w_title, :w_prompt, :w_note) AS rank,
                        snippet(prompts_fts, :snippet_col, :start_sel, :end_sel, :ellipsis, :tokens) AS snippet
                    FROM prompts_fts
                    WHERE prompts_fts MATCH :match_expr
                    """
                ),
                {
                    "w_title": _RANK_WEIGHT_TITLE,
                    "w_prompt": _RANK_WEIGHT_PROMPT,
                    "w_note": _RANK_WEIGHT_NOTE,
                    "snippet_col": snippet_col,
                    "start_sel": start_sel,
                    "end_sel": end_sel,
                    "ellipsis": ellipsis,
                    "tokens": tokens,
                    "match_expr": match_expr,
                },
            )
            for row in rows:
                # snippet() always returns an excerpt of the body column even
                # when the match was only in title/note; only surface it as
                # match_context when it actually contains a highlighted hit.
                snippet = row.snippet if row.snippet and MATCH_START in row.snippet else None
                matches[row.id] = RankedMatch(row.rank, snippet)
            return matches

        if dialect == "postgresql":
            tsquery = safe_query.to_tsquery()
            rows = self.session.execute(
                text(
                    """
                    SELECT
                        id,
                        ts_rank(search_vector, to_tsquery('simple', :tsquery)) AS rank,
                        ts_headline(
                            'simple', prompt, to_tsquery('simple', :tsquery), :headline_opts
                        ) AS snippet
                    FROM prompts
                    WHERE search_vector @@ to_tsquery('simple', :tsquery)
                    """
                ),
                {"tsquery": tsquery, "headline_opts": ts_headline_options()},
            )
            for row in rows:
                # ts_headline always returns an excerpt of the body column
                # even when the match was only in title/note; only surface
                # it when it actually contains a highlighted hit.
                snippet = row.snippet if row.snippet and MATCH_START in row.snippet else None
                # ts_rank is higher-is-better; negate so both dialects sort
                # ascending by "rank" (lower = more relevant) downstream.
                matches[row.id] = RankedMatch(-row.rank, snippet)
            return matches

        return None

    def _apply_common_filters(
        self,
        q,
        category: Optional[str],
        tags: Optional[List[str]],
        favorite: Optional[bool],
        visible_to_user_id: Optional[str],
        shared_only: bool,
    ):
        """Apply category/tags/favorite/visibility filters shared by search() and count()."""
        if category:
            q = q.join(Category).filter(Category.name == category)

        if tags and len(tags) > 0:
            q = q.join(Prompt.tags).filter(Tag.name.in_(tags)).distinct()

        if favorite is not None:
            q = q.filter(Prompt.favorite == favorite)
            if visible_to_user_id is not None:
                q = q.filter(Prompt.user_id == visible_to_user_id)
        else:
            q = self._apply_visibility_filter(q, visible_to_user_id, shared_only)

        return q

    def _case_sensitive_predicate(self, query: str):
        """Build the case-sensitive substring predicate (dialect-portable, no Python post-filter).

        Postgres ``LIKE`` is already case-sensitive. SQLite's ``LIKE`` is
        case-insensitive for ASCII by default, so SQLite uses ``GLOB``
        (case-sensitive) with its wildcard characters escaped instead.
        """
        if active_dialect(self.session) == "sqlite":
            # GLOB's own wildcards (*, ?, [...]) must be escaped via character
            # classes so a literal query with those characters still matches
            # literally, then the real wildcards are added around it.
            escaped = re.sub(r"[*?\[\]]", lambda m: f"[{m.group(0)}]", query)
            pattern = f"*{escaped}*"
            return or_(
                Prompt.title.op("GLOB")(pattern),
                Prompt.prompt.op("GLOB")(pattern),
                Prompt.note.op("GLOB")(pattern),
            )
        return or_(
            Prompt.title.like(f"%{query}%"),
            Prompt.prompt.like(f"%{query}%"),
            Prompt.note.like(f"%{query}%"),
        )

    def _apply_substring_query_filter(self, q, query: str, case_sensitive: bool):
        """Apply the non-FTS substring predicate for ``query`` (shared by search()/count())."""
        if case_sensitive:
            return q.filter(self._case_sensitive_predicate(query))
        search_pattern = f"%{query}%"
        return q.filter(
            or_(
                Prompt.title.ilike(search_pattern),
                Prompt.prompt.ilike(search_pattern),
                Prompt.note.ilike(search_pattern),
            )
        )

    def search(
        self,
        query: Optional[str] = None,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        favorite: Optional[bool] = None,
        limit: Optional[int] = None,
        offset: int = 0,
        case_sensitive: bool = False,
        visible_to_user_id: Optional[str] = None,
        shared_only: bool = False,
        ranked: bool = True,
    ) -> List[Tuple[Prompt, Optional[str]]]:
        """Search prompts with multiple filters.

        Args:
            query: Text search in title, prompt content, and note
            category: Filter by category name
            tags: Filter by tag names (prompts with ANY of these tags)
            favorite: Filter by favorite status. When combined with
                visible_to_user_id, restricted to owned prompts only —
                favorite is the owner's personal preference, so shared and
                legacy-public prompts never match it for a recipient.
            limit: Maximum number of results
            offset: Number of results to skip
            case_sensitive: Enforce case-sensitive matching on query (uses
                the substring path; no ranking/snippet)
            visible_to_user_id: Scope results to this user's owned + shared +
                legacy-public prompts (None = unscoped, e.g. admin)
            shared_only: Narrow to prompts explicitly shared with
                visible_to_user_id (excludes legacy_public and owned)
            ranked: Use index-backed relevance ranking (default True).
                False restores the legacy substring ordering.

        Returns:
            List of (Prompt, match_context) tuples. ``match_context`` is a
            snippet with ``[[MATCH]]``/``[[/MATCH]]`` sentinels around hits,
            or None (no body snippet, ranked=False, or case_sensitive=True).

        Example:
            # Search for favorited marketing prompts
            repo.search(query="email", category="Marketing", favorite=True)
        """
        use_fts = bool(query) and ranked and not case_sensitive

        if use_fts:
            fts_result = self._try_fts_search(
                query=query,
                category=category,
                tags=tags,
                favorite=favorite,
                limit=limit,
                offset=offset,
                visible_to_user_id=visible_to_user_id,
                shared_only=shared_only,
            )
            if fts_result is not None:
                return fts_result
            # Empty-after-sanitization or FTS error: fall through to substring path.

        q = self.session.query(Prompt)

        if query:
            q = self._apply_substring_query_filter(q, query, case_sensitive)

        q = self._apply_common_filters(q, category, tags, favorite, visible_to_user_id, shared_only)

        # Order by most recently updated (must come before limit/offset)
        q = q.order_by(Prompt.updated_at.desc().nullslast(), Prompt.created_at.desc())

        q = q.offset(offset)
        if limit:
            q = q.limit(limit)

        return [(prompt, None) for prompt in q.all()]

    def _try_fts_search(
        self,
        query: str,
        category: Optional[str],
        tags: Optional[List[str]],
        favorite: Optional[bool],
        limit: Optional[int],
        offset: int,
        visible_to_user_id: Optional[str],
        shared_only: bool,
    ) -> Optional[List[Tuple[Prompt, Optional[str]]]]:
        """Attempt the ranked FTS path; returns None to signal fallback.

        None means either the sanitized query was empty (FR-010/FR-011) or
        the FTS engine raised an operational/parse error (FR-010) — in both
        cases the caller falls back to the substring path.
        """
        try:
            matches = self._fts_matches(query)
        except (OperationalError, ProgrammingError):
            logger.warning("FTS query failed; falling back to substring search", exc_info=True)
            return None

        if matches is None:
            return None
        if not matches:
            return []

        q = self.session.query(Prompt).filter(Prompt.id.in_(matches.keys()))
        q = self._apply_common_filters(q, category, tags, favorite, visible_to_user_id, shared_only)

        prompts = q.all()
        # Deterministic order: relevance (lower rank = more relevant), then id
        # as a tiebreaker so OFFSET/LIMIT pagination is stable (FR-014).
        prompts.sort(key=lambda p: (matches[p.id].rank, p.id))

        page = prompts[offset:]
        if limit:
            page = page[:limit]

        return [(prompt, matches[prompt.id].match_context) for prompt in page]

    def count(
        self,
        query: Optional[str] = None,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        favorite: Optional[bool] = None,
        case_sensitive: bool = False,
        visible_to_user_id: Optional[str] = None,
        shared_only: bool = False,
        ranked: bool = True,
    ) -> int:
        """Count prompts matching the same filters as search().

        Mirrors search()'s filter-building logic exactly (minus limit/offset/
        ordering) so total_count/total_pages reflect the same result set that
        search() would page through (FR-008).

        Args:
            query: Text search in title, prompt content, and note
            category: Filter by category name
            tags: Filter by tag names (prompts with ANY of these tags)
            favorite: Filter by favorite status (owned-only when
                visible_to_user_id is set — see search())
            case_sensitive: Enforce case-sensitive matching on query
            visible_to_user_id: Scope results to this user's owned + shared +
                legacy-public prompts (None = unscoped, e.g. admin)
            shared_only: Narrow to prompts explicitly shared with
                visible_to_user_id (excludes legacy_public and owned)
            ranked: Use the FTS predicate (default True); must match search()

        Returns:
            Total number of matching prompts
        """
        use_fts = bool(query) and ranked and not case_sensitive

        if use_fts:
            try:
                matches = self._fts_matches(query)
            except (OperationalError, ProgrammingError):
                logger.warning("FTS count failed; falling back to substring count", exc_info=True)
                matches = None

            if matches is not None:
                if not matches:
                    return 0
                q = self.session.query(Prompt).filter(Prompt.id.in_(matches.keys()))
                q = self._apply_common_filters(
                    q, category, tags, favorite, visible_to_user_id, shared_only
                )
                return q.count()
            # Empty-after-sanitization or FTS error: fall through to substring path.

        q = self.session.query(Prompt)

        if query:
            q = self._apply_substring_query_filter(q, query, case_sensitive)

        q = self._apply_common_filters(q, category, tags, favorite, visible_to_user_id, shared_only)

        return q.count()

    def get_with_relationships(self, prompt_id: int) -> Optional[Prompt]:
        """Get a prompt with all relationships eagerly loaded.

        This method eagerly loads category, tags, versions, branches, and user
        to avoid N+1 query problems.

        Args:
            prompt_id: Prompt ID

        Returns:
            Prompt with all relationships loaded, or None if not found
        """
        return (
            self.session.query(Prompt)
            .filter(Prompt.id == prompt_id)
            .options(
                joinedload(Prompt.category),
                joinedload(Prompt.tags),
                joinedload(Prompt.versions),
                joinedload(Prompt.branches),
                joinedload(Prompt.user),
            )
            .first()
        )

    def get_by_category(self, category_name: str) -> List[Prompt]:
        """Get all prompts in a specific category.

        Args:
            category_name: Category name

        Returns:
            List of prompts in the category
        """
        return (
            self.session.query(Prompt)
            .join(Category)
            .filter(Category.name == category_name)
            .all()
        )

    def get_by_tag(self, tag_name: str) -> List[Prompt]:
        """Get all prompts with a specific tag.

        Args:
            tag_name: Tag name

        Returns:
            List of prompts with the tag
        """
        return (
            self.session.query(Prompt)
            .join(Prompt.tags)
            .filter(Tag.name == tag_name)
            .all()
        )

    def get_favorites(self, limit: Optional[int] = None) -> List[Prompt]:
        """Get all favorited prompts.

        Args:
            limit: Maximum number of results

        Returns:
            List of favorited prompts
        """
        q = self.session.query(Prompt).filter(Prompt.favorite == True)
        if limit:
            q = q.limit(limit)
        return q.all()

    def set_favorite(self, prompt_id: int, favorite: bool) -> Optional[Prompt]:
        """Set favorite status for a prompt.

        Args:
            prompt_id: Prompt ID
            favorite: New favorite status

        Returns:
            Updated prompt or None if not found
        """
        return self.update(prompt_id, favorite=favorite)

    def add_tag(self, prompt_id: int, tag: Tag) -> Optional[Prompt]:
        """Add a tag to a prompt.

        Args:
            prompt_id: Prompt ID
            tag: Tag object to add

        Returns:
            Updated prompt or None if not found
        """
        prompt = self.get_by_id(prompt_id)
        if prompt and tag not in prompt.tags:
            prompt.tags.append(tag)
            self.session.flush()
        return prompt

    def remove_tag(self, prompt_id: int, tag: Tag) -> Optional[Prompt]:
        """Remove a tag from a prompt.

        Args:
            prompt_id: Prompt ID
            tag: Tag object to remove

        Returns:
            Updated prompt or None if not found
        """
        prompt = self.get_by_id(prompt_id)
        if prompt and tag in prompt.tags:
            prompt.tags.remove(tag)
            self.session.flush()
        return prompt

    def create_with_tags(self, tags: List[Tag], **kwargs) -> Prompt:
        """Create a prompt and attach tags in one flush.

        Args:
            tags: Tag objects to attach to the new prompt
            **kwargs: Prompt model attributes

        Returns:
            The created Prompt (flushed, ID populated)
        """
        prompt = Prompt(**kwargs)
        prompt.tags = tags
        self.session.add(prompt)
        self.session.flush()
        return prompt

    def apply_update(self, instance: Prompt, tags: List[Tag], **kwargs) -> Prompt:
        """Apply field updates and tag assignment to an existing prompt, then flush.

        Args:
            instance: Prompt instance to update (already loaded/attached)
            tags: New tag list to assign
            **kwargs: Fields to set on the prompt

        Returns:
            The updated Prompt
        """
        for key, value in kwargs.items():
            setattr(instance, key, value)
        instance.tags = tags
        self.session.flush()
        return instance

    def create_main_branch(self, prompt_id: int, version_id: str) -> PromptBranch:
        """Create the initial "main" branch pointer for a prompt.

        Args:
            prompt_id: Prompt ID
            version_id: Version ID the branch should point to

        Returns:
            The created PromptBranch
        """
        branch = PromptBranch(
            prompt_id=prompt_id,
            branch_name="main",
            current_version_id=version_id,
        )
        self.session.add(branch)
        return branch

    def get_by_ids(self, prompt_ids: List[int]) -> List[Prompt]:
        """Get multiple prompts by ID.

        Args:
            prompt_ids: List of prompt IDs

        Returns:
            List of found prompts (may be fewer than requested IDs)
        """
        return self.session.query(Prompt).filter(Prompt.id.in_(prompt_ids)).all()

    def bulk_update_tags(
        self,
        prompts: List[Prompt],
        tags_to_add: Optional[List[Tag]] = None,
        tags_to_remove: Optional[List[Tag]] = None,
    ) -> None:
        """Add and/or remove tags across multiple prompts in one pass.

        Args:
            prompts: Prompts to update
            tags_to_add: Tags to attach if not already present
            tags_to_remove: Tags to detach if present
        """
        tags_to_add = tags_to_add or []
        tags_to_remove = tags_to_remove or []
        for prompt in prompts:
            for tag in tags_to_add:
                if tag not in prompt.tags:
                    prompt.tags.append(tag)
            for tag in tags_to_remove:
                if tag in prompt.tags:
                    prompt.tags.remove(tag)
        self.session.flush()

    def get_statistics(self) -> Dict[str, int]:
        """Get prompt statistics.

        Returns:
            Dictionary with statistics:
            - total: Total number of prompts
            - favorites: Number of favorited prompts
            - with_versions: Number of prompts with version history
        """
        total = self.count()
        favorites = self.session.query(Prompt).filter(Prompt.favorite == True).count()

        # Count prompts that have at least one version
        with_versions = self.session.query(Prompt).filter(Prompt.versions.any()).count()

        return {"total": total, "favorites": favorites, "with_versions": with_versions}
