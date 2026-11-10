"""Проверки через HTTP: настоящий сервер и отдельная временная база."""

import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen


PROJECT_DIR = Path(__file__).resolve().parents[1]


class RequestsApiTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.database = Path(self.temp_dir.name) / "test.db"
        self.start_server()

    def start_server(self):
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        self.base_url = f"http://127.0.0.1:{port}"
        self.server = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app:app",
             "--host", "127.0.0.1", "--port", str(port)],
            cwd=PROJECT_DIR,
            env=dict(os.environ, LEARNING_REQUESTS_DB=str(self.database)),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self.addCleanup(self.stop_server, self.server)
        for _ in range(50):
            if self.server.poll() is not None:
                self.fail("Сервер завершился до запуска")
            try:
                if self.call("/health") == (200, {"status": "ok"}):
                    return
            except OSError:
                time.sleep(0.2)
        self.fail("Сервер не запустился за отведённое время")

    @staticmethod
    def stop_server(server):
        if server.poll() is None:
            server.terminate()
            server.wait(timeout=10)

    def call(self, path, payload=None):
        request = Request(
            self.base_url + path,
            data=None if payload is None else json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        try:
            response = urlopen(request, timeout=3)
        except HTTPError as error:
            response = error
        with response:
            return response.status, json.load(response)

    def create(self):
        status, saved = self.call(
            "/api/requests",
            {"tool": "  Учебная Jira  ", "reason": "Первая задача; O'Brien"},
        )
        self.assertEqual(status, 201)
        return saved

    def test_health_and_home_page(self):
        self.assertEqual(self.call("/health"), (200, {"status": "ok"}))
        with urlopen(self.base_url + "/", timeout=3) as response:
            self.assertEqual(response.status, 200)
            self.assertEqual(response.headers.get_content_type(), "text/html")
            self.assertIn('id="create-form"', response.read().decode("utf-8"))

    def test_create_and_read_request(self):
        saved = self.create()
        self.assertIsInstance(saved["id"], int)
        self.assertGreater(saved["id"], 0)
        self.assertEqual(saved["tool"], "Учебная Jira")
        self.assertEqual(saved["reason"], "Первая задача; O'Brien")
        self.assertEqual(saved["status"], "created")
        self.assertEqual(self.call(f'/api/requests/{saved["id"]}'), (200, saved))

    def test_invalid_data_is_not_saved(self):
        payloads = [
            {}, {"tool": "Jira"}, {"reason": "Task"},
            {"tool": "", "reason": "Task"},
            {"tool": " \t\n", "reason": "Task"},
            {"tool": "Jira", "reason": " \t\n"},
            {"tool": 42, "reason": "Task"},
            {"tool": "Jira", "reason": None},
        ]
        for payload in payloads:
            with self.subTest(payload=payload):
                status, body = self.call("/api/requests", payload)
                self.assertEqual(status, 422)
                self.assertTrue(body["detail"])
        self.assertEqual(self.call("/api/requests/1")[0], 404)
        self.assertEqual(self.create()["id"], 1)

    def test_unknown_and_invalid_id(self):
        self.assertEqual(
            self.call("/api/requests/999"),
            (404, {"detail": "Заявка не найдена"}),
        )
        self.assertEqual(self.call("/api/requests/not-a-number")[0], 422)

    def test_invalid_suggestion_text(self):
        for payload in [{}, {"text": "   "}, {"text": "x" * 2001}]:
            with self.subTest(payload=payload):
                self.assertEqual(self.call("/api/suggestions", payload)[0], 422)

    def test_request_survives_restart(self):
        saved = self.create()
        self.stop_server(self.server)
        self.start_server()
        self.assertEqual(self.call(f'/api/requests/{saved["id"]}'), (200, saved))
        another = self.create()
        self.assertNotEqual(another["id"], saved["id"])


if __name__ == "__main__":
    unittest.main()
