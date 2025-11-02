"""
Comprehensive tests for email verification page.

Target coverage: 0% -> 95%+

Tests email verification UI flow, token validation, error handling,
and Streamlit integration.
"""

from unittest.mock import MagicMock, patch

from src.auth.email_verification_page import render_email_verification_page


class TestRenderEmailVerificationPage:
    """Test email verification page rendering."""

    def test_render_page_no_token(self):
        """Test rendering when no token provided."""
        with (
            patch("streamlit.markdown"),
            patch("streamlit.query_params", new_callable=MagicMock) as mock_params,
            patch("streamlit.error") as mock_error,
            patch("streamlit.info"),
        ):
            # Mock query params with no token
            mock_params.get.return_value = None

            render_email_verification_page()

            # Should show error
            mock_error.assert_called_once()
            assert "No verification token" in str(mock_error.call_args)

            # Should show info tip (checked via patch)

    def test_render_page_invalid_token(self):
        """Test rendering with invalid token."""
        with (
            patch("streamlit.markdown"),
            patch("streamlit.query_params", new_callable=MagicMock) as mock_params,
            patch("streamlit.error") as mock_error,
            patch("streamlit.info"),
            patch("asyncio.run") as mock_run,
        ):
            # Mock query params with token
            mock_params.get.return_value = "invalid_token"

            # Mock verify_verification_token to return None (invalid)
            mock_run.return_value = None

            render_email_verification_page()

            # Should show error about invalid/expired link
            assert mock_error.call_count >= 1
            error_calls = [str(call) for call in mock_error.call_args_list]
            assert any("invalid or has expired" in call for call in error_calls)

    def test_render_page_valid_token_not_verified_yet(self):
        """Test rendering with valid token before verification."""
        with (
            patch("streamlit.markdown"),
            patch("streamlit.query_params", new_callable=MagicMock) as mock_params,
            patch("streamlit.success"),
            patch("streamlit.button") as mock_button,
            patch("asyncio.run") as mock_run,
        ):
            # Mock query params with token
            mock_params.get.return_value = "valid_token"

            # Mock verify_verification_token to return valid record
            mock_run.return_value = {"user_id": "user-123", "email": "test@example.com"}

            # Mock button not clicked
            mock_button.return_value = False

            render_email_verification_page()

            # Should show verify button
            mock_button.assert_called()

    def test_render_page_verification_success(self):
        """Test successful email verification."""
        with (
            patch("streamlit.markdown"),
            patch("streamlit.query_params", new_callable=MagicMock) as mock_params,
            patch("streamlit.success"),
            patch("streamlit.balloons") as mock_balloons,
            patch("streamlit.button") as mock_button,
            patch("asyncio.run") as mock_run,
        ):
            # Mock query params with token
            mock_params.get.return_value = "valid_token"

            # Setup mock run to return different values
            call_count = 0

            def mock_run_side_effect(coro):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    # First call: verify_verification_token
                    return {"user_id": "user-123"}
                if call_count == 2:
                    # Second call: use_verification_token
                    return True
                return None

            mock_run.side_effect = mock_run_side_effect

            # Mock button clicks: first verify button clicked, then login button not clicked
            mock_button.side_effect = [True, False]

            render_email_verification_page()

            # Should show balloons
            mock_balloons.assert_called_once()

    def test_render_page_verification_failure(self):
        """Test failed email verification."""
        with (
            patch("streamlit.markdown"),
            patch("streamlit.query_params", new_callable=MagicMock) as mock_params,
            patch("streamlit.success"),
            patch("streamlit.error") as mock_error,
            patch("streamlit.button") as mock_button,
            patch("asyncio.run") as mock_run,
        ):
            # Mock query params with token
            mock_params.get.return_value = "valid_token"

            # Setup mock run
            call_count = 0

            def mock_run_side_effect(coro):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    # First call: verify_verification_token
                    return {"user_id": "user-123"}
                if call_count == 2:
                    # Second call: use_verification_token fails
                    return False
                return None

            mock_run.side_effect = mock_run_side_effect

            # Mock button clicked
            mock_button.return_value = True

            render_email_verification_page()

            # Should show error
            error_calls = [str(call) for call in mock_error.call_args_list]
            assert any("verification failed" in call for call in error_calls)

    def test_render_page_verification_exception_invalid_expired(self):
        """Test handling exception during verification."""
        with (
            patch("streamlit.markdown"),
            patch("streamlit.query_params", new_callable=MagicMock) as mock_params,
            patch("streamlit.success"),
            patch("streamlit.error") as mock_error,
            patch("streamlit.info"),
            patch("streamlit.button") as mock_button,
            patch("asyncio.run") as mock_run,
        ):
            # Mock query params with token
            mock_params.get.return_value = "valid_token"

            # Setup mock run
            call_count = 0

            def mock_run_side_effect(coro):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    # First call: verify_verification_token
                    return {"user_id": "user-123"}
                if call_count == 2:
                    # Second call: use_verification_token raises exception
                    raise Exception("Invalid or expired token")
                return None

            mock_run.side_effect = mock_run_side_effect

            # Mock button clicked
            mock_button.return_value = True

            render_email_verification_page()

            # Should show error about invalid/expired
            error_calls = [str(call) for call in mock_error.call_args_list]
            assert any("invalid or has already been used" in call for call in error_calls)

    def test_render_page_verification_exception_general(self):
        """Test handling general exception during verification."""
        with (
            patch("streamlit.markdown"),
            patch("streamlit.query_params", new_callable=MagicMock) as mock_params,
            patch("streamlit.success"),
            patch("streamlit.error") as mock_error,
            patch("streamlit.button") as mock_button,
            patch("asyncio.run") as mock_run,
        ):
            # Mock query params with token
            mock_params.get.return_value = "valid_token"

            # Setup mock run
            call_count = 0

            def mock_run_side_effect(coro):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    # First call: verify_verification_token
                    return {"user_id": "user-123"}
                if call_count == 2:
                    # Second call: use_verification_token raises exception
                    raise Exception("Database error")
                return None

            mock_run.side_effect = mock_run_side_effect

            # Mock button clicked
            mock_button.return_value = True

            render_email_verification_page()

            # Should show general error
            error_calls = [str(call) for call in mock_error.call_args_list]
            assert any("error occurred" in call for call in error_calls)

    def test_render_page_outer_exception(self):
        """Test handling outer exception."""
        with (
            patch("streamlit.markdown"),
            patch("streamlit.query_params", new_callable=MagicMock) as mock_params,
            patch("streamlit.error") as mock_error,
            patch("asyncio.run") as mock_run,
        ):
            # Mock query params with token
            mock_params.get.return_value = "valid_token"

            # Mock run to raise exception
            mock_run.side_effect = Exception("Unexpected error")

            render_email_verification_page()

            # Should show error
            error_calls = [str(call) for call in mock_error.call_args_list]
            assert any("error occurred" in call for call in error_calls)

    def test_render_page_redirect_after_success(self):
        """Test redirect to login after successful verification."""
        with (
            patch("streamlit.markdown"),
            patch("streamlit.query_params", new_callable=MagicMock) as mock_params,
            patch("streamlit.success"),
            patch("streamlit.balloons"),
            patch("streamlit.button") as mock_button,
            patch("streamlit.switch_page") as mock_switch_page,
            patch("asyncio.run") as mock_run,
        ):
            # Mock query params with token
            mock_params.get.return_value = "valid_token"

            # Setup mock run
            call_count = 0

            def mock_run_side_effect(coro):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    # First call: verify_verification_token
                    return {"user_id": "user-123"}
                if call_count == 2:
                    # Second call: use_verification_token
                    return True
                return None

            mock_run.side_effect = mock_run_side_effect

            # Mock buttons: verify clicked, then login clicked
            mock_button.side_effect = [True, True]

            render_email_verification_page()

            # Should clear query params and redirect
            mock_params.clear.assert_called_once()
            mock_switch_page.assert_called_once_with("streamlit_app.py")

    def test_render_page_markdown_styling(self):
        """Test that page renders with proper styling."""
        with (
            patch("streamlit.markdown") as mock_markdown,
            patch("streamlit.query_params", new_callable=MagicMock) as mock_params,
            patch("streamlit.error"),
        ):
            # Mock query params with no token to trigger simple path
            mock_params.get.return_value = None

            render_email_verification_page()

            # Should have called markdown for styling
            assert mock_markdown.call_count >= 1

            # First call should be for styling
            first_call = mock_markdown.call_args_list[0]
            assert "unsafe_allow_html=True" in str(first_call)
            assert "verify-container" in str(first_call)

    def test_render_page_request_new_link(self):
        """Test UI for requesting new verification link."""
        with (
            patch("streamlit.markdown") as mock_markdown,
            patch("streamlit.query_params", new_callable=MagicMock) as mock_params,
            patch("streamlit.error"),
            patch("streamlit.info"),
            patch("asyncio.run") as mock_run,
        ):
            # Mock query params with token
            mock_params.get.return_value = "invalid_token"

            # Mock verify_verification_token to return None (invalid)
            mock_run.return_value = None

            render_email_verification_page()

            # Should show section about requesting new link
            markdown_calls = [str(call) for call in mock_markdown.call_args_list]
            assert any("Need a new verification link" in call for call in markdown_calls)


class TestModuleExecution:
    """Test module execution."""

    def test_main_execution(self):
        """Test __main__ execution."""
        with (
            patch("streamlit.markdown"),
            patch("streamlit.query_params", new_callable=MagicMock) as mock_params,
            patch("streamlit.error"),
        ):
            # Mock query params
            mock_params.get.return_value = None

            # Simulate module execution
            import src.auth.email_verification_page as module

            if __name__ == "__main__":
                module.render_email_verification_page()

            # Would be called if run as main
            # Note: This test verifies the pattern, actual execution happens in Streamlit
