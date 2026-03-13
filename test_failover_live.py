"""Live failover test — forces Claude failure, verifies OpenAI responds."""

import os
from unittest.mock import MagicMock, patch

from dotenv import load_dotenv

load_dotenv()

# Verify OpenAI key is set
assert os.environ.get("OPENAI_API_KEY"), "OPENAI_API_KEY not set in .env"
print(f"OpenAI key: {os.environ['OPENAI_API_KEY'][:20]}...")


def test_failover_with_real_openai():
    """Force Claude 529 → verify OpenAI backup responds with real API."""
    import anthropic

    from src.ai_provider import create_message

    # Patch only the Anthropic client to simulate 529 overloaded
    with patch("src.ai_provider.anthropic.Anthropic") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client

        mock_resp = MagicMock()
        mock_resp.status_code = 529
        mock_client.messages.create.side_effect = anthropic.APIStatusError(
            message="overloaded", response=mock_resp, body=None
        )

        # This should failover to real OpenAI
        tools = [
            {
                "name": "get_daily_context",
                "description": "Get today's family context",
                "input_schema": {"type": "object", "properties": {}, "required": []},
            }
        ]

        response, provider = create_message(
            system="You are a helpful family assistant. Reply briefly.",
            tools=tools,
            messages=[{"role": "user", "content": "Say hello in one sentence."}],
            max_tokens=100,
        )

        print(f"\nProvider: {provider}")
        print(f"Stop reason: {response.stop_reason}")
        print(f"Content blocks: {len(response.content)}")
        for block in response.content:
            if hasattr(block, "text"):
                print(f"Response text: {block.text}")
            elif hasattr(block, "name"):
                print(f"Tool call: {block.name}")

        assert provider == "openai", f"Expected openai, got {provider}"
        assert len(response.content) > 0, "No content in response"
        print("\n✅ FAILOVER TEST PASSED — OpenAI responded successfully")


def test_both_down():
    """Force both providers down → verify AllProvidersDownError."""
    import anthropic

    from src.ai_provider import AllProvidersDownError, create_message

    with patch("src.ai_provider.anthropic.Anthropic") as mock_claude, \
         patch("src.ai_provider.OpenAI") as mock_openai_cls:

        # Claude fails
        mock_client = MagicMock()
        mock_claude.return_value = mock_client
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_client.messages.create.side_effect = anthropic.APIStatusError(
            message="server error", response=mock_resp, body=None
        )

        # OpenAI also fails
        mock_oai = MagicMock()
        mock_openai_cls.return_value = mock_oai
        mock_oai.chat.completions.create.side_effect = Exception("OpenAI down too")

        try:
            create_message(
                system="test",
                tools=[],
                messages=[{"role": "user", "content": "hi"}],
            )
            assert False, "Should have raised AllProvidersDownError"
        except AllProvidersDownError:
            print("✅ BOTH-DOWN TEST PASSED — AllProvidersDownError raised correctly")


if __name__ == "__main__":
    test_failover_with_real_openai()
    print()
    test_both_down()
    print("\n🎉 All failover tests passed!")
