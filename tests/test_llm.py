"""Проверки интеграции без запуска и скачивания настоящей модели."""

import io
import json
import unittest
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError

from fastapi import HTTPException
from pydantic import ValidationError

import app
import llm


class SuggestionTests(unittest.TestCase):
    def response(self, content, **changes):
        data = {"done": True, "message": {"content": content}, **changes}
        response = MagicMock()
        response.read.return_value = json.dumps(data).encode()
        response.__enter__.return_value = response
        return response

    @patch("llm.build_opener")
    def test_extract_and_send_schema(self, opener):
        opener.return_value.open.return_value = self.response(
            json.dumps({"tool": " Jira ", "reason": "Первая задача"})
        )
        fields = llm.suggest_fields("Мне нужна Jira для первой задачи")
        self.assertEqual(fields.tool, "Jira")
        self.assertEqual(fields.reason, "Первая задача")
        request = opener.return_value.open.call_args.args[0]
        payload = json.loads(request.data)
        self.assertFalse(payload["think"])
        self.assertFalse(payload["stream"])
        self.assertEqual(set(payload["format"]["required"]), {"tool", "reason"})
        self.assertEqual(payload["messages"][1]["role"], "user")
        self.assertEqual(opener.return_value.open.call_args.kwargs["timeout"], 90)

    @patch("llm.build_opener")
    def test_missing_information_can_be_empty(self, opener):
        opener.return_value.open.return_value = self.response('{"tool":"Jira","reason":""}')
        self.assertEqual(llm.suggest_fields("Нужна Jira").reason, "")

    @patch("llm.build_opener")
    def test_bad_model_responses(self, opener):
        for content in ["not json", "[]", '{}', '{"tool":42,"reason":"Task"}',
                        '{"tool":"Jira","reason":null}',
                        '{"tool":"Jira","reason":"Task","id":1}']:
            with self.subTest(content=content):
                opener.return_value.open.return_value = self.response(content)
                with self.assertRaises(llm.LLMError) as raised:
                    llm.suggest_fields("Test")
                self.assertEqual(raised.exception.status_code, 502)

    @patch("llm.build_opener")
    def test_incomplete_and_oversized_response(self, opener):
        for response in [self.response('{}', done=False),
                         self.response('{"tool":"Jira","reason":"Task"}', done_reason="length")]:
            opener.return_value.open.return_value = response
            with self.assertRaises(llm.LLMError) as raised:
                llm.suggest_fields("Test")
            self.assertEqual(raised.exception.status_code, 502)
        opener.return_value.open.return_value.read.return_value = b'x' * 131073
        with self.assertRaises(llm.LLMError):
            llm.suggest_fields("Test")

    @patch("llm.build_opener")
    def test_unavailable_timeout_and_missing_model(self, opener):
        errors = [
            (URLError("Connection refused"), 503),
            (TimeoutError(), 504),
            (HTTPError("http://localhost", 404, "Missing model", {}, io.BytesIO()), 503),
        ]
        for error, expected in errors:
            with self.subTest(error=type(error).__name__):
                opener.return_value.open.side_effect = error
                with self.assertRaises(llm.LLMError) as raised:
                    llm.suggest_fields("Test")
                self.assertEqual(raised.exception.status_code, expected)

    def test_input_validation(self):
        for text in ["", " \t\n", "x" * 2001]:
            with self.subTest(length=len(text)), self.assertRaises(ValidationError):
                app.SuggestionInput(text=text)

    @patch("app.storage.create_request")
    @patch("app.llm.suggest_fields")
    def test_suggestion_does_not_create_request(self, suggest, create):
        suggest.return_value = llm.DraftFields(tool="Jira", reason="Task")
        result = app.suggest_fields(app.SuggestionInput(text="Request"))
        self.assertEqual(result.tool, "Jira")
        create.assert_not_called()

    @patch("app.llm.suggest_fields")
    def test_errors_become_http_errors(self, suggest):
        for code in [502, 503, 504]:
            with self.subTest(code=code):
                suggest.side_effect = llm.LLMError(code, "Test error")
                with self.assertRaises(HTTPException) as raised:
                    app.suggest_fields(app.SuggestionInput(text="Request"))
                self.assertEqual(raised.exception.status_code, code)


if __name__ == "__main__":
    unittest.main()
