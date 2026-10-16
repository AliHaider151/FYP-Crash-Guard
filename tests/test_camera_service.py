import json
import tempfile
import unittest
from pathlib import Path

from app.services.camera_service import load_cameras


class CameraServiceTests(unittest.TestCase):
    def test_loads_four_cameras_using_existing_sample_video(self):
        cameras = load_cameras()

        self.assertEqual([camera.name for camera in cameras], ["Camera 1", "Camera 2", "Camera 3", "Camera 4"])
        self.assertTrue(all(camera.video_path.is_file() for camera in cameras))
        self.assertTrue(all(camera.video_path.name == "accident-video-4.mp4" for camera in cameras))
        self.assertEqual(len({(camera.latitude, camera.longitude) for camera in cameras}), 4)
        self.assertTrue(all(28 <= camera.latitude <= 29 for camera in cameras))
        self.assertTrue(all(70 <= camera.longitude <= 71 for camera in cameras))

    def test_rejects_invalid_coordinates(self):
        payload = {
            "cameras": [
                {
                    "name": "Bad Camera",
                    "video_path": "assets/videos/accident-video-4.mp4",
                    "latitude": 120,
                    "longitude": 70,
                }
            ]
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "cameras.json"
            config_path.write_text(json.dumps(payload), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "coordinates"):
                load_cameras(config_path)


if __name__ == "__main__":
    unittest.main()