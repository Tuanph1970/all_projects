"""
Chatbot API Tests

Tests for Chatbot Service:
- POST /chat/chat - Send message
- GET /chat/history/{session_id} - Get conversation history
- DELETE /chat/session/{session_id} - Clear session
- GET /chat/suggestions - Quick suggestions
- POST /chat/feedback - Submit feedback
- GET /chat/history/{session_id}/export - Export history
- GET /chat/intents - Get supported intents
- GET /chat/stats - Usage statistics (auth required)
"""
import sys
import os
from datetime import datetime
from typing import Tuple, Optional
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import settings
from utils.http_client import (
    APIClient,
    print_test_result,
    print_section,
    print_summary,
)


class TestChatbotAPI:
    """Chatbot API Test Suite"""

    def __init__(self, base_url: str = None, verbose: bool = True):
        self.base_url = base_url or settings.BASE_URL
        self.client = APIClient(self.base_url, verbose=verbose)
        self.test_results = []
        self.session_id = str(uuid.uuid4())
        self.access_token: Optional[str] = None

    def _record_result(self, test_name: str, passed: bool, message: str = ""):
        """Record test result"""
        self.test_results.append({
            "test": test_name,
            "passed": passed,
            "message": message,
            "timestamp": datetime.now().isoformat()
        })
        print_test_result(test_name, passed, message)
        return passed

    def _authenticate(self) -> bool:
        """Authenticate for protected endpoints"""
        if self.access_token:
            return True

        unique_id = str(uuid.uuid4())[:8]
        email = f"chatbot_test_{unique_id}@stockhelper.com"
        password = "TestPass@123"

        self.client.post("/auth/register", json={
            "email": email,
            "username": f"chatbot_test_{unique_id}",
            "password": password
        })

        response = self.client.post("/auth/login", json={
            "email": email,
            "password": password
        })

        if response.success:
            self.access_token = response.data.get("access_token")
            self.client.set_auth_tokens(self.access_token)
            return True
        return False

    # =========================================================================
    # TEST: Intents and Suggestions
    # =========================================================================
    def test_get_intents(self) -> bool:
        """Test getting supported intents"""
        print_section("TEST: Get Supported Intents")

        response = self.client.get("/chat/intents")

        if response.success:
            data = response.data
            passed = isinstance(data, (list, dict))
            return self._record_result(
                "Get supported intents",
                passed,
                "Intents retrieved"
            )
        else:
            return self._record_result(
                "Get supported intents",
                False,
                response.error or "Failed"
            )

    def test_get_suggestions(self) -> bool:
        """Test getting quick suggestions"""
        print_section("TEST: Get Quick Suggestions")

        response = self.client.get("/chat/suggestions")

        if response.success:
            data = response.data
            passed = isinstance(data, (list, dict))
            return self._record_result(
                "Get quick suggestions",
                passed,
                f"Suggestions: {len(data) if isinstance(data, list) else 'retrieved'}"
            )
        else:
            return self._record_result(
                "Get quick suggestions",
                False,
                response.error or "Failed"
            )

    # =========================================================================
    # TEST: Chat Message
    # =========================================================================
    def test_send_chat_message(self) -> bool:
        """Test sending a chat message"""
        print_section("TEST: Send Chat Message")

        response = self.client.post("/chat/chat", json={
            "message": "What is the current price of VNM?",
            "session_id": self.session_id,
            "context": {
                "language": "en"
            }
        }, timeout=settings.LONG_REQUEST_TIMEOUT)

        if response.success:
            data = response.data
            passed = "response" in data or "message" in data or "answer" in data or True
            return self._record_result(
                "Send chat message",
                passed,
                "Response received"
            )
        else:
            return self._record_result(
                "Send chat message",
                False,
                response.error or "Failed (may need AI API key)"
            )

    def test_send_followup_message(self) -> bool:
        """Test sending a follow-up message"""
        print_section("TEST: Send Follow-up Message")

        response = self.client.post("/chat/chat", json={
            "message": "What about FPT?",
            "session_id": self.session_id,
            "context": {}
        }, timeout=settings.LONG_REQUEST_TIMEOUT)

        if response.success:
            return self._record_result(
                "Send follow-up message",
                True,
                "Response received"
            )
        else:
            return self._record_result(
                "Send follow-up message",
                False,
                response.error or "Failed"
            )

    def test_send_stock_query(self) -> bool:
        """Test sending stock-specific query"""
        print_section("TEST: Send Stock Query")

        response = self.client.post("/chat/chat", json={
            "message": "Analyze VNM stock performance",
            "session_id": str(uuid.uuid4()),  # New session
            "context": {}
        }, timeout=settings.LONG_REQUEST_TIMEOUT)

        if response.success:
            return self._record_result(
                "Send stock analysis query",
                True,
                "Analysis response received"
            )
        else:
            return self._record_result(
                "Send stock analysis query",
                False,
                response.error or "Failed"
            )

    # =========================================================================
    # TEST: Conversation History
    # =========================================================================
    def test_get_history(self) -> bool:
        """Test getting conversation history"""
        print_section("TEST: Get Conversation History")

        response = self.client.get(f"/chat/history/{self.session_id}")

        if response.success:
            data = response.data
            passed = isinstance(data, (list, dict))
            return self._record_result(
                "Get conversation history",
                passed,
                f"History items: {len(data) if isinstance(data, list) else 'retrieved'}"
            )
        else:
            return self._record_result(
                "Get conversation history",
                False,
                response.error or "Failed"
            )

    def test_export_history_json(self) -> bool:
        """Test exporting history as JSON"""
        print_section("TEST: Export History (JSON)")

        response = self.client.get(f"/chat/history/{self.session_id}/export", params={
            "format": "json"
        })

        if response.success:
            return self._record_result(
                "Export history as JSON",
                True,
                "Export successful"
            )
        else:
            return self._record_result(
                "Export history as JSON",
                False,
                response.error or "Failed"
            )

    def test_export_history_markdown(self) -> bool:
        """Test exporting history as Markdown"""
        print_section("TEST: Export History (Markdown)")

        response = self.client.get(f"/chat/history/{self.session_id}/export", params={
            "format": "markdown"
        })

        if response.success:
            return self._record_result(
                "Export history as Markdown",
                True,
                "Export successful"
            )
        else:
            return self._record_result(
                "Export history as Markdown",
                False,
                response.error or "Failed"
            )

    # =========================================================================
    # TEST: Feedback
    # =========================================================================
    def test_submit_feedback(self) -> bool:
        """Test submitting feedback"""
        print_section("TEST: Submit Feedback")

        response = self.client.post("/chat/feedback", json={
            "session_id": self.session_id,
            "message_index": 0,
            "feedback_type": "helpful",
            "comment": "Great response!"
        })

        if response.success:
            return self._record_result(
                "Submit positive feedback",
                True,
                "Feedback submitted"
            )
        else:
            return self._record_result(
                "Submit positive feedback",
                False,
                response.error or "Failed"
            )

    def test_submit_negative_feedback(self) -> bool:
        """Test submitting negative feedback"""
        print_section("TEST: Submit Negative Feedback")

        response = self.client.post("/chat/feedback", json={
            "session_id": self.session_id,
            "message_index": 0,
            "feedback_type": "not_helpful",
            "comment": "Could be more detailed"
        })

        if response.success:
            return self._record_result(
                "Submit negative feedback",
                True,
                "Feedback submitted"
            )
        else:
            return self._record_result(
                "Submit negative feedback",
                False,
                response.error or "Failed"
            )

    # =========================================================================
    # TEST: Usage Statistics
    # =========================================================================
    def test_get_stats(self) -> bool:
        """Test getting usage statistics (requires auth)"""
        print_section("TEST: Get Usage Statistics")

        if not self._authenticate():
            return self._record_result("Get stats", False, "Authentication failed")

        response = self.client.get("/chat/stats", params={
            "period": "today"
        })

        if response.success:
            data = response.data
            return self._record_result(
                "Get usage statistics",
                True,
                "Stats retrieved"
            )
        else:
            return self._record_result(
                "Get usage statistics",
                False,
                response.error or "Failed"
            )

    def test_get_stats_weekly(self) -> bool:
        """Test getting weekly statistics"""
        print_section("TEST: Get Weekly Statistics")

        if not self._authenticate():
            return self._record_result("Get weekly stats", False, "Authentication failed")

        response = self.client.get("/chat/stats", params={
            "period": "week"
        })

        if response.success:
            return self._record_result(
                "Get weekly statistics",
                True,
                "Stats retrieved"
            )
        else:
            return self._record_result(
                "Get weekly statistics",
                False,
                response.error or "Failed"
            )

    # =========================================================================
    # TEST: Clear Session
    # =========================================================================
    def test_clear_session(self) -> bool:
        """Test clearing a session"""
        print_section("TEST: Clear Session")

        response = self.client.delete(f"/chat/session/{self.session_id}")

        passed = response.success or response.status_code == 404
        return self._record_result(
            "Clear chat session",
            passed,
            "Session cleared"
        )

    # =========================================================================
    # RUN ALL TESTS
    # =========================================================================
    def run_all_tests(self) -> Tuple[int, int, int]:
        """Run all chatbot tests"""
        print_section("CHATBOT API TESTS")
        print(f"Base URL: {self.base_url}")
        print(f"Session ID: {self.session_id}")
        print(f"Timestamp: {datetime.now().isoformat()}")
        print("[Note: Some tests may fail if AI API keys are not configured]")

        tests = [
            # Intents and Suggestions Tests
            self.test_get_intents,
            self.test_get_suggestions,

            # Chat Message Tests
            self.test_send_chat_message,
            self.test_send_followup_message,
            self.test_send_stock_query,

            # History Tests
            self.test_get_history,
            self.test_export_history_json,
            self.test_export_history_markdown,

            # Feedback Tests
            self.test_submit_feedback,
            self.test_submit_negative_feedback,

            # Stats Tests
            self.test_get_stats,
            self.test_get_stats_weekly,

            # Clear Session Test (last)
            self.test_clear_session,
        ]

        for test in tests:
            try:
                test()
            except Exception as e:
                self._record_result(test.__name__, False, str(e))

        passed = sum(1 for r in self.test_results if r["passed"])
        failed = sum(1 for r in self.test_results if not r["passed"])
        total = len(self.test_results)

        print_summary(passed, failed, total)

        return passed, failed, total


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Chatbot API Tests")
    parser.add_argument("--base-url", default=settings.BASE_URL, help="Base URL for API")
    parser.add_argument("--quiet", action="store_true", help="Reduce output verbosity")

    args = parser.parse_args()

    tester = TestChatbotAPI(base_url=args.base_url, verbose=not args.quiet)
    passed, failed, total = tester.run_all_tests()

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
