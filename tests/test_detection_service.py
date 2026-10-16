import unittest

import numpy as np

from app.services.detection_service import prepare_detection_frame, should_run_detection


class DetectionServiceTests(unittest.TestCase):
    def test_should_run_detection_every_n_frames(self):
        self.assertTrue(should_run_detection(0, interval=3))
        self.assertTrue(should_run_detection(3, interval=3))
        self.assertFalse(should_run_detection(1, interval=3))

    def test_prepare_detection_frame_downsizes_large_frames(self):
        frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
        processed = prepare_detection_frame(frame, max_width=640, max_height=360)

        self.assertLessEqual(processed.shape[1], 640)
        self.assertLessEqual(processed.shape[0], 360)


if __name__ == "__main__":
    unittest.main()
