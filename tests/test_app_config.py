import os
import tempfile
import unittest
from pathlib import Path


class AppConfigTests(unittest.TestCase):
    def test_config_uses_environment_when_present(self):
        from app.config import AppConfig

        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = Path(tmpdir) / ".env"
            env_path.write_text(
                "MODEL_PATH=custom-model.pt\n"
                "APP_NAME=Custom App\n"
                "FIREBASE_SERVICE_ACCOUNT_JSON={\"type\":\"service_account\"}\n"
                "CLOUDINARY_CLOUD_NAME=test-cloud\n"
                "CLOUDINARY_API_KEY=test-key\n"
                "CLOUDINARY_API_SECRET=test-secret\n"
                "AMD_API_KEY=test-amd-key\n"
                "INCIDENT_VERIFICATION_FRAME_COUNT=5\n",
                encoding="utf-8",
            )

            config = AppConfig(env_file=str(env_path))
            self.assertEqual(config.model_path, "custom-model.pt")
            self.assertEqual(config.app_name, "Custom App")
            self.assertEqual(config.firebase_credentials_json, '{"type":"service_account"}')
            self.assertEqual(config.cloudinary.cloud_name, "test-cloud")
            self.assertEqual(config.cloudinary.api_key, "test-key")
            self.assertEqual(config.cloudinary.api_secret, "test-secret")
            self.assertEqual(config.incident_verification.api_key, "test-amd-key")
            self.assertEqual(config.incident_verification.model, "DeepSeek-V4-Flash-Vision-Exp")
            self.assertEqual(config.incident_verification.frame_count, 5)

    def test_resolve_path_handles_relative_and_absolute_paths(self):
        from app.config import AppConfig

        config = AppConfig()

        self.assertEqual(
            config.resolve_path("models/model.pt"),
            (config.project_root / "models/model.pt").resolve(),
        )
        absolute_path = config.project_root / "absolute-model.pt"
        self.assertEqual(config.resolve_path(str(absolute_path)), absolute_path)

    def test_config_reads_quoted_multiline_firebase_json(self):
        from app.config import AppConfig

        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = Path(tmpdir) / ".env"
            env_path.write_text(
                """FIREBASE_SERVICE_ACCOUNT_JSON='{
  "type": "service_account",
  "private_key": "line1\\\\nline2\\\\n"
}'
""",
                encoding="utf-8",
            )

            config = AppConfig(env_file=str(env_path))

        import json

        service_account = json.loads(config.firebase_credentials_json)
        self.assertEqual(service_account["type"], "service_account")
        self.assertEqual(service_account["private_key"], "line1\nline2\n")


if __name__ == "__main__":
    unittest.main()
