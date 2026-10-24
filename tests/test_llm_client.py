"""Unit tests for the Gemma client with mocked provider responses."""
from unittest.mock import MagicMock, patch
import pytest
from app.core.llm_client import GemmaClient
from app.core.models import Target, TargetType


def test_gemma_client_batch_success():
    client = GemmaClient(api_key="test-key")

    mock_response = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = (
        '{"results": [{'
        '  "qualified_name": "add",'
        '  "docstring": "Add two numbers.",'
        '  "param_annotations": {"a": "float", "b": "float"},'
        '  "return_annotation": "float",'
        '  "confidence": 0.98'
        '}]}'
    )
    mock_response.choices = [mock_choice]
    mock_response.usage.prompt_tokens = 45
    mock_response.usage.completion_tokens = 32

    target = Target(
        file_path="math.py",
        qualified_name="add",
        target_type=TargetType.FUNCTION,
        start_byte=0,
        end_byte=35,
        start_line=1,
        end_line=2,
        signature="def add(a, b):",
        parameters=["a", "b"],
        missing_type_annotations=["a", "b"],
    )

    with patch.object(client.client.chat.completions, "create", return_value=mock_response):
        patches, tokens_in, tokens_out, latency = client.generate_batch(
            "math.py", "def add(a, b):\n    return a + b\n", [target]
        )

    assert len(patches) == 1
    assert patches[0].target_qualified_name == "add"
    assert patches[0].generated_docstring == "Add two numbers."
    assert patches[0].param_annotations == {"a": "float", "b": "float"}
    assert patches[0].return_annotation == "float"
    assert tokens_in == 45
    assert tokens_out == 32
    assert latency >= 0


def test_gemma_client_retry_on_malformed_json():
    client = GemmaClient(api_key="test-key")

    # First attempt returns invalid JSON, second returns valid JSON
    bad_choice = MagicMock()
    bad_choice.message.content = "Invalid json string"
    bad_response = MagicMock()
    bad_response.choices = [bad_choice]
    bad_response.usage.prompt_tokens = 10
    bad_response.usage.completion_tokens = 5

    good_choice = MagicMock()
    good_choice.message.content = '{"results": []}'
    good_response = MagicMock()
    good_response.choices = [good_choice]
    good_response.usage.prompt_tokens = 10
    good_response.usage.completion_tokens = 10

    target = Target(
        file_path="math.py",
        qualified_name="foo",
        target_type=TargetType.FUNCTION,
        start_byte=0,
        end_byte=20,
        start_line=1,
        end_line=2,
        signature="def foo():",
    )

    with patch.object(client.client.chat.completions, "create", side_effect=[bad_response, good_response]):
        patches, tokens_in, tokens_out, _ = client.generate_batch(
            "math.py", "def foo(): pass", [target]
        )

    assert patches == []
    assert tokens_in == 20
    assert tokens_out == 15
