# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Request and response validation models for PromptVault API."""

from .auth_requests import (
    ChangePasswordRequest,
    LoginRequest,
    PasswordResetConfirmRequest,
    PasswordResetRequestRequest,
    RefreshTokenRequest,
    RegisterRequest,
    RevokeSessionRequest,
)
from .auth_responses import (
    MessageResponse,
    PasswordResetRequestResponse,
    PasswordStrengthResponse,
    RevokeSessionResponse,
    SessionListResponse,
    SessionResponse,
    TokenResponse,
    UserResponse,
)
from .enums import ExportFormat, ImportMode
from .requests import (
    BackupCleanupRequest,
    BackupCompressRequest,
    BackupCreateRequest,
    BulkDeleteRequest,
    ExportRequest,
    FrontendLogEntry,
    ImportRequest,
    PromptCreateRequest,
    PromptUpdateRequest,
    VersionRevertRequest,
)
from .sharing_requests import PromptVisibilityUpdateRequest, ShareGrantRequest
from .sharing_responses import (
    ShareGranteeInfo,
    ShareListResponse,
    ShareResponse,
    UserSearchResponse,
    UserSuggestion,
)
from .undo_responses import (
    UndoHistoryResponse,
    UndoOperationResponse,
    UndoResultResponse,
)

__all__ = [
    # Prompt requests
    "PromptCreateRequest",
    "PromptUpdateRequest",
    "ExportRequest",
    "ImportRequest",
    "BackupCreateRequest",
    "BackupCleanupRequest",
    "BackupCompressRequest",
    "VersionRevertRequest",
    "FrontendLogEntry",
    "BulkDeleteRequest",
    # Enums
    "ExportFormat",
    "ImportMode",
    # Auth requests
    "RegisterRequest",
    "LoginRequest",
    "RefreshTokenRequest",
    "ChangePasswordRequest",
    "PasswordResetRequestRequest",
    "PasswordResetConfirmRequest",
    "RevokeSessionRequest",
    # Auth responses
    "UserResponse",
    "TokenResponse",
    "SessionResponse",
    "MessageResponse",
    "PasswordResetRequestResponse",
    "PasswordStrengthResponse",
    "SessionListResponse",
    "RevokeSessionResponse",
    # Undo responses
    "UndoOperationResponse",
    "UndoHistoryResponse",
    "UndoResultResponse",
    # Sharing requests
    "ShareGrantRequest",
    "PromptVisibilityUpdateRequest",
    # Sharing responses
    "UserSuggestion",
    "ShareGranteeInfo",
    "ShareResponse",
    "ShareListResponse",
    "UserSearchResponse",
]
