import os
import unittest
from unittest.mock import patch

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "crashguard_site.settings")

import django

django.setup()

from django.test import Client

from app.services.camera_service import load_cameras


class WebDashboardTests(unittest.TestCase):
    def test_dashboard_lists_configured_cameras(self):
        response = Client().get("/", HTTP_HOST="localhost")

        self.assertEqual(response.status_code, 200)
        for camera in load_cameras():
            self.assertIn(camera.name.encode(), response.content)
            self.assertIn(camera.location.encode(), response.content)

    def test_start_requires_a_configured_camera(self):
        client = Client(enforce_csrf_checks=True)
        client.get("/", HTTP_HOST="localhost")
        csrf_token = client.cookies["csrftoken"].value

        response = client.post(
            "/detection/start/",
            {"camera": "not-configured"},
            HTTP_HOST="localhost",
            HTTP_X_CSRFTOKEN=csrf_token,
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "Select a configured camera.")

    def test_start_uses_the_configured_camera(self):
        camera = load_cameras()[0]
        with patch("app.web.views.detection_manager.start", return_value=True) as start:
            response = Client().post(
                "/detection/start/",
                {"camera": camera.name},
                HTTP_HOST="localhost",
            )

        self.assertEqual(response.status_code, 200)
        start.assert_called_once_with(camera)


if __name__ == "__main__":
    unittest.main()
