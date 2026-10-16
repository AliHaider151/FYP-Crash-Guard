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
                "FIREBASE_KEY_PATH=keys/custom.json\n"
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
            self.assertEqual(config.firebase_key_path, "keys/custom.json")
            self.assertEqual(config.cloudinary.cloud_name, "test-cloud")
            self.assertEqual(config.cloudinary.api_key, "test-key")
            self.assertEqual(config.cloudinary.api_secret, "test-secret")
            self.assertEqual(config.incident_verification.api_key, "test-amd-key")
            self.assertEqual(config.incident_verification.model, "DeepSeek-V4-Flash-Vision-Exp")
            self.assertEqual(config.incident_verification.frame_count, 5)


if __name__ == "__main__":
    unittest.main()
