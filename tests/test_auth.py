"""Tests for the auth gate logic."""

from __future__ import annotations

from unittest.mock import MagicMock, patch


class TestCheckPassword:
    @patch("dashboard.auth.st")
    def test_no_secret_configured_allows_access(self, mock_st):
        """No auth secret = access granted (local dev)."""
        mock_st.secrets = MagicMock()
        mock_st.secrets.__getitem__ = MagicMock(side_effect=KeyError("auth"))
        from dashboard.auth import check_password

        assert check_password() is True

    @patch("dashboard.auth.st")
    def test_empty_password_allows_access(self, mock_st):
        """Empty password secret = access granted."""
        auth_section = MagicMock()
        auth_section.__getitem__ = MagicMock(return_value="")
        mock_st.secrets = MagicMock()
        mock_st.secrets.__getitem__ = MagicMock(return_value=auth_section)
        from dashboard.auth import check_password

        assert check_password() is True

    @patch("dashboard.auth.st")
    def test_correct_password_authenticates(self, mock_st):
        """Already authenticated session = True."""
        auth_section = MagicMock()
        auth_section.__getitem__ = MagicMock(return_value="secret123")
        mock_st.secrets = MagicMock()
        mock_st.secrets.__getitem__ = MagicMock(return_value=auth_section)
        mock_st.session_state = {"authenticated": True}
        from dashboard.auth import check_password

        assert check_password() is True

    @patch("dashboard.auth.st")
    def test_unauthenticated_shows_login(self, mock_st):
        """Not yet authenticated = returns False (shows login form)."""
        auth_section = MagicMock()
        auth_section.__getitem__ = MagicMock(return_value="secret123")
        mock_st.secrets = MagicMock()
        mock_st.secrets.__getitem__ = MagicMock(return_value=auth_section)
        mock_st.session_state = {}
        mock_st.text_input = MagicMock(return_value="")
        mock_st.button = MagicMock(return_value=False)
        from dashboard.auth import check_password

        assert check_password() is False
