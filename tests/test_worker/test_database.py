from unittest.mock import MagicMock, patch

import pytest

from api.worker.database import SessionManager


class TestSessionManager:
    """Tests for SessionManager context manager."""

    def test_context_manager_enters(self):
        """Test entering context manager."""
        with patch("api.worker.database.SessionLocal") as mock_session:
            mock_session.return_value = MagicMock()

            with SessionManager() as session:
                assert session is not None

    def test_context_manager_exits_on_success(self):
        """Test session commits on successful exit."""
        mock_session = MagicMock()
        mock_session.is_active = True

        with patch("api.worker.database.SessionLocal", return_value=mock_session), SessionManager():
            pass

        mock_session.commit.assert_called_once()

    def test_context_manager_rollback_on_exception(self):
        """Test session rolls back on exception."""
        mock_session = MagicMock()
        mock_session.is_active = True

        with patch("api.worker.database.SessionLocal", return_value=mock_session):
            with pytest.raises(ValueError):
                with SessionManager():
                    raise ValueError("test")

        mock_session.rollback.assert_called_once()

    def test_session_closed_on_exit(self):
        """Test session is closed after use."""
        mock_session = MagicMock()

        with patch("api.worker.database.SessionLocal", return_value=mock_session), SessionManager():
            pass

        mock_session.close.assert_called_once()


class TestGetSession:
    """Tests for get_session function."""

    def test_returns_session_manager(self):
        """Test get_session returns SessionManager."""
        from api.worker.database import get_session

        with patch("api.worker.database.SessionLocal") as mock_session:
            mock_session.return_value = MagicMock()
            result = get_session()

            assert isinstance(result, SessionManager)
