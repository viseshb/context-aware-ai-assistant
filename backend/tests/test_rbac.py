from __future__ import annotations

import json

import pytest

from app.security.rbac import filter_tool_result_for_user, validate_tool_call
from app.utils.errors import AuthorizationError


def test_admin_can_call_any_github_tool():
    user = {"role": "admin"}
    validate_tool_call(user, "github_get_repo_info", {"repo": "acme/private-repo"})
    validate_tool_call(user, "github_get_repo_metrics", {"repo": "acme/private-repo"})
    validate_tool_call(user, "github_count_commits", {"repo": "acme/private-repo"})
    validate_tool_call(user, "github_list_repos", {"org": "acme"})


def test_member_can_list_only_orgs_they_have_repo_access_to():
    user = {"role": "member", "allowed_repos": ["acme/private-repo"], "allowed_channels": [], "allowed_db_tables": []}
    validate_tool_call(user, "github_list_repos", {"org": "acme"})

    with pytest.raises(AuthorizationError):
        validate_tool_call(user, "github_list_repos", {"org": "otherorg"})


def test_member_repo_list_results_are_filtered_to_allowed_repos():
    user = {"role": "member", "allowed_repos": ["acme/private-repo"], "allowed_channels": [], "allowed_db_tables": []}
    raw = json.dumps([
        {"name": "acme/private-repo", "private": True},
        {"name": "acme/other-repo", "private": True},
    ])

    filtered = json.loads(filter_tool_result_for_user(user, "github_list_repos", raw))

    assert filtered == [{"name": "acme/private-repo", "private": True}]


def test_member_channel_and_table_list_results_are_filtered():
    user = {
        "role": "member",
        "allowed_repos": [],
        "allowed_channels": ["eng-alerts"],
        "allowed_db_tables": ["public.events"],
    }

    channels_raw = json.dumps([
        {"name": "eng-alerts", "id": "C1"},
        {"name": "finance", "id": "C2"},
    ])
    tables_raw = json.dumps([
        {"schema": "public", "table": "events"},
        {"schema": "public", "table": "users"},
    ])

    filtered_channels = json.loads(filter_tool_result_for_user(user, "slack_list_channels", channels_raw))
    filtered_tables = json.loads(filter_tool_result_for_user(user, "db_list_tables", tables_raw))

    assert filtered_channels == [{"name": "eng-alerts", "id": "C1"}]
    assert filtered_tables == [{"schema": "public", "table": "events"}]
