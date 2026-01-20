"""Tests for lib/github.py - GitHub branch protection."""

import json
import subprocess
from unittest.mock import MagicMock, patch

import pytest

from lib.github import (
    OwnerType,
    PlanTier,
    RepoInfo,
    can_use_bypass_actors,
    check_release_pat,
    check_ruleset_status,
    compare_protection_config,
    create_ruleset,
    delete_ruleset,
    get_pat_creation_url,
    get_protection_recommendation,
    get_repo_info,
    get_ruleset_details,
    setup_branch_protection,
    setup_release_workflow,
)
from core.errors import GitHubError, ProtectionError


class TestOwnerTypeAndPlanTier:
    """Tests for enum types."""

    def test_owner_type_values(self):
        """Should have correct string values."""
        assert OwnerType.USER.value == "user"
        assert OwnerType.ORGANIZATION.value == "organization"

    def test_plan_tier_values(self):
        """Should have correct string values."""
        assert PlanTier.FREE.value == "free"
        assert PlanTier.PRO.value == "pro"
        assert PlanTier.TEAM.value == "team"
        assert PlanTier.ENTERPRISE.value == "enterprise"


class TestRepoInfo:
    """Tests for RepoInfo dataclass."""

    def test_creates_repo_info(self):
        """Should create RepoInfo with all fields."""
        info = RepoInfo(
            owner="user",
            name="repo",
            owner_type=OwnerType.USER,
            plan=PlanTier.FREE,
            visibility="public",
            default_branch="main",
        )
        assert info.owner == "user"
        assert info.name == "repo"
        assert info.owner_type == OwnerType.USER
        assert info.plan == PlanTier.FREE


class TestGetRepoInfo:
    """Tests for get_repo_info()."""

    def test_detects_user_free(self):
        """Should detect user with free plan."""
        with patch("subprocess.run") as mock_run:
            # Repo API call
            repo_result = MagicMock()
            repo_result.stdout = json.dumps(
                {
                    "owner": {"type": "User"},
                    "visibility": "public",
                    "default_branch": "main",
                }
            )

            # User API call (no plan = free)
            user_result = MagicMock()
            user_result.stdout = json.dumps({"plan": {"name": "free"}})

            mock_run.side_effect = [repo_result, user_result]

            info = get_repo_info("testuser/testrepo")

            assert info is not None
            assert info.owner == "testuser"
            assert info.name == "testrepo"
            assert info.owner_type == OwnerType.USER
            assert info.plan == PlanTier.FREE

    def test_detects_user_pro(self):
        """Should detect user with pro plan."""
        with patch("subprocess.run") as mock_run:
            repo_result = MagicMock()
            repo_result.stdout = json.dumps(
                {
                    "owner": {"type": "User"},
                    "visibility": "public",
                    "default_branch": "main",
                }
            )

            user_result = MagicMock()
            user_result.stdout = json.dumps({"plan": {"name": "pro"}})

            mock_run.side_effect = [repo_result, user_result]

            info = get_repo_info("testuser/testrepo")

            assert info.plan == PlanTier.PRO

    def test_detects_org_team(self):
        """Should detect organization with team plan."""
        with patch("subprocess.run") as mock_run:
            repo_result = MagicMock()
            repo_result.stdout = json.dumps(
                {
                    "owner": {"type": "Organization"},
                    "visibility": "private",
                    "default_branch": "main",
                }
            )

            org_result = MagicMock()
            org_result.stdout = json.dumps({"plan": {"name": "team"}})

            mock_run.side_effect = [repo_result, org_result]

            info = get_repo_info("testorg/testrepo")

            assert info.owner_type == OwnerType.ORGANIZATION
            assert info.plan == PlanTier.TEAM

    def test_detects_org_enterprise(self):
        """Should detect organization with enterprise plan."""
        with patch("subprocess.run") as mock_run:
            repo_result = MagicMock()
            repo_result.stdout = json.dumps(
                {
                    "owner": {"type": "Organization"},
                    "visibility": "internal",
                    "default_branch": "main",
                }
            )

            org_result = MagicMock()
            org_result.stdout = json.dumps({"plan": {"name": "enterprise"}})

            mock_run.side_effect = [repo_result, org_result]

            info = get_repo_info("testorg/testrepo")

            assert info.plan == PlanTier.ENTERPRISE

    def test_auto_detects_from_git_remote(self):
        """Should auto-detect repo from git remote."""
        with patch("subprocess.run") as mock_run:
            # git remote get-url
            remote_result = MagicMock()
            remote_result.stdout = "https://github.com/owner/repo.git\n"

            # repo API
            repo_result = MagicMock()
            repo_result.stdout = json.dumps(
                {
                    "owner": {"type": "User"},
                    "visibility": "public",
                    "default_branch": "main",
                }
            )

            # user API
            user_result = MagicMock()
            user_result.stdout = json.dumps({"plan": {"name": "free"}})

            mock_run.side_effect = [remote_result, repo_result, user_result]

            info = get_repo_info()  # No repo argument

            assert info is not None
            assert info.owner == "owner"
            assert info.name == "repo"

    def test_returns_none_for_invalid_repo(self):
        """Should return None for invalid repo format."""
        result = get_repo_info("invalid-repo-format")
        assert result is None

    def test_raises_on_api_error(self):
        """Should raise GitHubError on API failure."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, "gh", stderr=b"Not found")

            with pytest.raises(GitHubError):
                get_repo_info("user/repo")


class TestCanUseBypassActors:
    """Tests for can_use_bypass_actors()."""

    def test_user_free_cannot_bypass(self):
        """User Free plan cannot use bypass actors."""
        info = RepoInfo(
            owner="user",
            name="repo",
            owner_type=OwnerType.USER,
            plan=PlanTier.FREE,
            visibility="public",
            default_branch="main",
        )
        assert can_use_bypass_actors(info) is False

    def test_user_pro_can_bypass(self):
        """User Pro plan can use bypass actors."""
        info = RepoInfo(
            owner="user",
            name="repo",
            owner_type=OwnerType.USER,
            plan=PlanTier.PRO,
            visibility="public",
            default_branch="main",
        )
        assert can_use_bypass_actors(info) is True

    def test_org_free_cannot_bypass(self):
        """Org Free plan cannot use bypass actors."""
        info = RepoInfo(
            owner="org",
            name="repo",
            owner_type=OwnerType.ORGANIZATION,
            plan=PlanTier.FREE,
            visibility="public",
            default_branch="main",
        )
        assert can_use_bypass_actors(info) is False

    def test_org_team_can_bypass(self):
        """Org Team plan can use bypass actors."""
        info = RepoInfo(
            owner="org",
            name="repo",
            owner_type=OwnerType.ORGANIZATION,
            plan=PlanTier.TEAM,
            visibility="private",
            default_branch="main",
        )
        assert can_use_bypass_actors(info) is True

    def test_org_enterprise_can_bypass(self):
        """Org Enterprise plan can use bypass actors."""
        info = RepoInfo(
            owner="org",
            name="repo",
            owner_type=OwnerType.ORGANIZATION,
            plan=PlanTier.ENTERPRISE,
            visibility="internal",
            default_branch="main",
        )
        assert can_use_bypass_actors(info) is True


class TestCheckRulesetStatus:
    """Tests for check_ruleset_status()."""

    def test_finds_existing_ruleset(self):
        """Should find existing devkit-protection ruleset."""
        with patch("subprocess.run") as mock_run:
            result = MagicMock()
            result.stdout = json.dumps(
                [
                    {"name": "other-ruleset", "id": 1},
                    {
                        "name": "devkit-protection",
                        "id": 123,
                        "enforcement": "active",
                        "bypass_actors": [{"actor_id": 5}],
                    },
                ]
            )
            mock_run.return_value = result

            status = check_ruleset_status("user/repo")

            assert status["exists"] is True
            assert status["ruleset_id"] == 123
            assert status["enforcement"] == "active"
            assert status["has_bypass"] is True

    def test_no_ruleset_found(self):
        """Should return exists=False when no ruleset."""
        with patch("subprocess.run") as mock_run:
            result = MagicMock()
            result.stdout = json.dumps([{"name": "other-ruleset", "id": 1}])
            mock_run.return_value = result

            status = check_ruleset_status("user/repo")

            assert status["exists"] is False
            assert status["ruleset_id"] is None

    def test_handles_api_error(self):
        """Should handle API errors gracefully."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, "gh")

            status = check_ruleset_status("user/repo")

            assert status["exists"] is False


class TestCreateRuleset:
    """Tests for create_ruleset()."""

    def test_creates_ruleset_with_bypass(self):
        """Should create ruleset with admin bypass."""
        with patch("subprocess.run") as mock_run:
            # check_ruleset_status returns no existing ruleset
            check_result = MagicMock()
            check_result.stdout = json.dumps([])

            # create succeeds
            create_result = MagicMock()

            mock_run.side_effect = [check_result, create_result]

            config = {"require_reviews": 1, "linear_history": True}
            ok, msg = create_ruleset("user/repo", config, bypass_actors=True)

            assert ok is True
            assert "admin bypass" in msg

    def test_creates_ruleset_without_bypass(self):
        """Should create ruleset without bypass for free plans."""
        with patch("subprocess.run") as mock_run:
            check_result = MagicMock()
            check_result.stdout = json.dumps([])

            create_result = MagicMock()

            mock_run.side_effect = [check_result, create_result]

            config = {"require_reviews": 1, "linear_history": True}
            ok, msg = create_ruleset("user/repo", config, bypass_actors=False)

            assert ok is True
            assert "admin bypass" not in msg

    def test_deletes_existing_ruleset_first(self):
        """Should delete existing ruleset before creating new one."""
        with patch("subprocess.run") as mock_run:
            # Existing ruleset
            check_result = MagicMock()
            check_result.stdout = json.dumps([{"name": "devkit-protection", "id": 99}])

            # Delete succeeds
            delete_result = MagicMock()

            # Create succeeds
            create_result = MagicMock()

            mock_run.side_effect = [check_result, delete_result, create_result]

            config = {"require_reviews": 1}
            ok, msg = create_ruleset("user/repo", config)

            assert ok is True
            assert mock_run.call_count == 3  # check, delete, create

    def test_raises_on_create_failure(self):
        """Should raise ProtectionError on failure."""
        with patch("subprocess.run") as mock_run:
            check_result = MagicMock()
            check_result.stdout = json.dumps([])

            mock_run.side_effect = [
                check_result,
                subprocess.CalledProcessError(1, "gh", stderr=b"API error"),
            ]

            with pytest.raises(ProtectionError):
                create_ruleset("user/repo", {})


class TestDeleteRuleset:
    """Tests for delete_ruleset()."""

    def test_deletes_ruleset(self):
        """Should delete ruleset by ID."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock()

            ok, msg = delete_ruleset("user/repo", 123)

            assert ok is True
            assert "123" in msg

    def test_handles_delete_failure(self):
        """Should handle delete failure."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, "gh", stderr=b"Not found")

            ok, msg = delete_ruleset("user/repo", 999)

            assert ok is False
            assert "Failed" in msg


class TestGetProtectionRecommendation:
    """Tests for get_protection_recommendation()."""

    def test_recommends_pat_for_user_free(self):
        """Should recommend PAT for user free plan."""
        info = RepoInfo(
            owner="user",
            name="repo",
            owner_type=OwnerType.USER,
            plan=PlanTier.FREE,
            visibility="public",
            default_branch="main",
        )

        rec = get_protection_recommendation(info)

        assert rec["can_bypass"] is False
        assert rec["needs_pat"] is True
        assert "RELEASE_PAT" in rec["warning"]

    def test_no_pat_needed_for_user_pro(self):
        """Should not need PAT for user pro plan."""
        info = RepoInfo(
            owner="user",
            name="repo",
            owner_type=OwnerType.USER,
            plan=PlanTier.PRO,
            visibility="public",
            default_branch="main",
        )

        rec = get_protection_recommendation(info)

        assert rec["can_bypass"] is True
        assert rec["needs_pat"] is False
        assert rec["warning"] is None

    def test_warns_org_free(self):
        """Should warn about limitations for org free."""
        info = RepoInfo(
            owner="org",
            name="repo",
            owner_type=OwnerType.ORGANIZATION,
            plan=PlanTier.FREE,
            visibility="public",
            default_branch="main",
        )

        rec = get_protection_recommendation(info)

        assert rec["can_bypass"] is False
        assert "limited" in rec["recommendation"].lower()

    def test_full_support_org_team(self):
        """Should have full support for org team."""
        info = RepoInfo(
            owner="org",
            name="repo",
            owner_type=OwnerType.ORGANIZATION,
            plan=PlanTier.TEAM,
            visibility="private",
            default_branch="main",
        )

        rec = get_protection_recommendation(info)

        assert rec["can_bypass"] is True
        assert rec["needs_pat"] is False


class TestSetupBranchProtection:
    """Tests for setup_branch_protection()."""

    def test_skips_when_disabled(self):
        """Should skip when protection disabled in config."""
        results = setup_branch_protection("user/repo", {"enabled": False})

        assert len(results) == 1
        assert results[0][0] == "protection"
        assert "Disabled" in results[0][2]

    def test_full_workflow_with_bypass(self):
        """Should run full workflow with bypass support."""
        with patch("lib.github.get_repo_info") as mock_info:
            with patch("lib.github.create_ruleset") as mock_create:
                mock_info.return_value = RepoInfo(
                    owner="user",
                    name="repo",
                    owner_type=OwnerType.USER,
                    plan=PlanTier.PRO,
                    visibility="public",
                    default_branch="main",
                )
                mock_create.return_value = (True, "Created ruleset")

                results = setup_branch_protection("user/repo")

                assert any("repo type" in r[0] for r in results)
                assert any("ruleset" in r[0] for r in results)
                # No warning for Pro plan
                assert not any("warning" in r[0] for r in results)

    def test_adds_warning_for_free_plan(self):
        """Should add warning for free plan."""
        with patch("lib.github.get_repo_info") as mock_info:
            with patch("lib.github.create_ruleset") as mock_create:
                mock_info.return_value = RepoInfo(
                    owner="user",
                    name="repo",
                    owner_type=OwnerType.USER,
                    plan=PlanTier.FREE,
                    visibility="public",
                    default_branch="main",
                )
                mock_create.return_value = (True, "Created ruleset")

                results = setup_branch_protection("user/repo")

                assert any("warning" in r[0] for r in results)
                assert any("action required" in r[0] for r in results)

    def test_handles_repo_info_failure(self):
        """Should handle repo info failure gracefully."""
        with patch("lib.github.get_repo_info") as mock_info:
            mock_info.return_value = None

            results = setup_branch_protection("user/repo")

            assert any(r[1] is False for r in results)
            assert any("Could not detect" in r[2] for r in results)


class TestGetRulesetDetails:
    """Tests for get_ruleset_details()."""

    def test_returns_ruleset_details(self):
        """Should return full ruleset details when found."""
        with patch("lib.github.check_ruleset_status") as mock_status:
            with patch("subprocess.run") as mock_run:
                mock_status.return_value = {"exists": True, "ruleset_id": 123}

                ruleset_data = {
                    "id": 123,
                    "name": "devkit-protection",
                    "rules": [
                        {"type": "required_linear_history"},
                        {
                            "type": "pull_request",
                            "parameters": {"required_approving_review_count": 1},
                        },
                    ],
                }
                result = MagicMock()
                result.stdout = json.dumps(ruleset_data)
                mock_run.return_value = result

                details = get_ruleset_details("user/repo")

                assert details is not None
                assert details["id"] == 123
                assert len(details["rules"]) == 2

    def test_returns_none_when_not_found(self):
        """Should return None when ruleset doesn't exist."""
        with patch("lib.github.check_ruleset_status") as mock_status:
            mock_status.return_value = {"exists": False, "ruleset_id": None}

            details = get_ruleset_details("user/repo")

            assert details is None

    def test_handles_api_error(self):
        """Should return None on API error."""
        with patch("lib.github.check_ruleset_status") as mock_status:
            with patch("subprocess.run") as mock_run:
                mock_status.return_value = {"exists": True, "ruleset_id": 123}
                mock_run.side_effect = subprocess.CalledProcessError(1, "gh")

                details = get_ruleset_details("user/repo")

                assert details is None


class TestCompareProtectionConfig:
    """Tests for compare_protection_config()."""

    def test_no_discrepancies_when_matching(self):
        """Should return empty list when config matches GitHub."""
        with patch("lib.github.get_ruleset_details") as mock_details:
            mock_details.return_value = {
                "rules": [
                    {"type": "required_linear_history"},
                    {
                        "type": "pull_request",
                        "parameters": {
                            "required_approving_review_count": 1,
                            "dismiss_stale_reviews_on_push": False,
                        },
                    },
                ]
            }

            config = {
                "enabled": True,
                "linear_history": True,
                "require_reviews": 1,
                "dismiss_stale_reviews": False,
            }

            discrepancies = compare_protection_config("user/repo", config)

            assert discrepancies == []

    def test_detects_missing_ruleset(self):
        """Should detect when ruleset doesn't exist."""
        with patch("lib.github.get_ruleset_details") as mock_details:
            mock_details.return_value = None

            config = {"enabled": True, "require_reviews": 1}

            discrepancies = compare_protection_config("user/repo", config)

            assert len(discrepancies) == 1
            assert discrepancies[0]["setting"] == "ruleset"
            assert discrepancies[0]["github_value"] == "not configured"

    def test_detects_review_count_mismatch(self):
        """Should detect require_reviews mismatch."""
        with patch("lib.github.get_ruleset_details") as mock_details:
            mock_details.return_value = {
                "rules": [
                    {
                        "type": "pull_request",
                        "parameters": {"required_approving_review_count": 0},
                    }
                ]
            }

            config = {"require_reviews": 1}

            discrepancies = compare_protection_config("user/repo", config)

            assert any(d["setting"] == "require_reviews" for d in discrepancies)
            review_disc = next(d for d in discrepancies if d["setting"] == "require_reviews")
            assert review_disc["config_value"] == 1
            assert review_disc["github_value"] == 0

    def test_detects_linear_history_mismatch(self):
        """Should detect linear_history mismatch."""
        with patch("lib.github.get_ruleset_details") as mock_details:
            mock_details.return_value = {"rules": []}  # No linear history rule

            config = {"linear_history": True}

            discrepancies = compare_protection_config("user/repo", config)

            assert any(d["setting"] == "linear_history" for d in discrepancies)

    def test_detects_dismiss_stale_mismatch(self):
        """Should detect dismiss_stale_reviews mismatch."""
        with patch("lib.github.get_ruleset_details") as mock_details:
            mock_details.return_value = {
                "rules": [
                    {
                        "type": "pull_request",
                        "parameters": {"dismiss_stale_reviews_on_push": True},
                    }
                ]
            }

            config = {"dismiss_stale_reviews": False}

            discrepancies = compare_protection_config("user/repo", config)

            assert any(d["setting"] == "dismiss_stale_reviews" for d in discrepancies)


class TestCheckReleasePat:
    """Tests for check_release_pat()."""

    def test_returns_true_when_pat_exists(self):
        """Should return True when RELEASE_PAT is found."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout="RELEASE_PAT\t2024-01-01\nOTHER_SECRET\t2024-01-01\n"
            )

            exists, msg = check_release_pat("user/repo")

            assert exists is True
            assert "configured" in msg.lower()

    def test_returns_false_when_pat_missing(self):
        """Should return False when RELEASE_PAT is not found."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="OTHER_SECRET\t2024-01-01\n")

            exists, msg = check_release_pat("user/repo")

            assert exists is False
            assert "not found" in msg.lower()

    def test_auto_detects_repo(self):
        """Should auto-detect repo from git remote when not provided."""
        with patch("lib.github.get_repo_info") as mock_info:
            with patch("subprocess.run") as mock_run:
                mock_info.return_value = RepoInfo(
                    owner="user",
                    name="repo",
                    owner_type=OwnerType.USER,
                    plan=PlanTier.FREE,
                    visibility="public",
                    default_branch="main",
                )
                mock_run.return_value = MagicMock(stdout="RELEASE_PAT\t2024-01-01\n")

                exists, msg = check_release_pat()

                assert exists is True
                mock_run.assert_called_once()
                assert "-R" in mock_run.call_args[0][0]
                assert "user/repo" in mock_run.call_args[0][0]

    def test_handles_api_error(self):
        """Should handle API errors gracefully."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, "gh", stderr="error")

            exists, msg = check_release_pat("user/repo")

            assert exists is False
            assert "could not check" in msg.lower()


class TestGetPatCreationUrl:
    """Tests for get_pat_creation_url()."""

    def test_returns_github_url(self):
        """Should return GitHub PAT creation URL."""
        url = get_pat_creation_url()

        assert "github.com" in url
        assert "personal-access-tokens" in url


class TestSetupReleaseWorkflow:
    """Tests for setup_release_workflow()."""

    def test_returns_success_when_pat_exists(self):
        """Should return success when RELEASE_PAT is configured."""
        with patch("lib.github.get_repo_info") as mock_info:
            with patch("lib.github.check_release_pat") as mock_pat:
                mock_info.return_value = RepoInfo(
                    owner="user",
                    name="repo",
                    owner_type=OwnerType.USER,
                    plan=PlanTier.FREE,
                    visibility="public",
                    default_branch="main",
                )
                mock_pat.return_value = (True, "RELEASE_PAT configured")

                results = setup_release_workflow("user/repo")

                assert any(r[0] == "RELEASE_PAT" and r[1] is True for r in results)

    def test_returns_instructions_when_pat_missing(self):
        """Should return setup instructions when RELEASE_PAT is missing."""
        with patch("lib.github.get_repo_info") as mock_info:
            with patch("lib.github.check_release_pat") as mock_pat:
                mock_info.return_value = RepoInfo(
                    owner="user",
                    name="repo",
                    owner_type=OwnerType.USER,
                    plan=PlanTier.FREE,
                    visibility="public",
                    default_branch="main",
                )
                mock_pat.return_value = (False, "RELEASE_PAT not found")

                results = setup_release_workflow("user/repo")

                assert any(r[0] == "RELEASE_PAT" and r[1] is False for r in results)
                assert any("action required" in r[0] for r in results)
                assert any("instructions" in r[0] for r in results)

    def test_handles_repo_info_failure(self):
        """Should handle repo info failure gracefully."""
        with patch("lib.github.get_repo_info") as mock_info:
            mock_info.return_value = None

            results = setup_release_workflow("user/repo")

            assert any(r[1] is False for r in results)
            assert any("Could not detect" in r[2] for r in results)
