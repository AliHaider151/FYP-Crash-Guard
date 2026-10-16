import json
import unittest
from unittest.mock import Mock

import numpy as np
import requests

from app.config import IncidentVerificationConfig
from app.services.incident_verification_service import (
    _empty_result,
    _apply_hazard_safety_guard,
    sample_frame_indices,
    validate_verification_result,
    verify_incident,
)


def valid_result():
    return {
        "verdict": "uncertain",
        "confidence": 61,
        "incident_types": ["vehicle_collision"],
        "visual_evidence": ["Two vehicles are stopped close together."],
        "alternative_explanations": ["Traffic congestion may explain the stop."],
        "hazards_detected": [],
        "severity": "unknown",
        "requires_more_frames": True,
        "recommended_action": "human_review",
        "reasoning_summary": "The sampled frames do not establish a collision.",
    }


class IncidentVerificationTests(unittest.TestCase):
    def test_random_frame_indices_are_unique_ordered_and_spread_across_clip(self):
        indices = sample_frame_indices(100, 8)

        self.assertEqual(len(indices), 8)
        self.assertEqual(indices, sorted(set(indices)))
        self.assertLess(indices[0], 15)
        self.assertGreater(indices[-1], 85)

    def test_frame_sampling_caps_count_to_available_frames(self):
        self.assertEqual(sample_frame_indices(3, 8), [0, 1, 2])
        self.assertEqual(sample_frame_indices(0, 8), [])

    def test_schema_rejects_invalid_verdict_and_extra_keys(self):
        result = valid_result()
        result["verdict"] = "probably"
        with self.assertRaises(ValueError):
            validate_verification_result(result)

        result = valid_result()
        result["extra"] = "not allowed"
        with self.assertRaises(ValueError):
            validate_verification_result(result)

    def test_missing_api_key_returns_uncertain_without_network_request(self):
        post = Mock()
        result = verify_incident(
            [np.zeros((32, 32, 3), dtype=np.uint8)],
            [],
            config=IncidentVerificationConfig(api_key=""),
            post=post,
        )

        self.assertEqual(result["verdict"], "uncertain")
        self.assertEqual(result["recommended_action"], "human_review")
        post.assert_not_called()

    def test_successful_request_includes_multiple_images_and_validates_json(self):
        response = Mock()
        response.json.return_value = {
            "choices": [{"message": {"content": json.dumps(valid_result())}}]
        }
        post = Mock(return_value=response)
        frames = [np.zeros((40, 64, 3), dtype=np.uint8) for _ in range(12)]
        config = IncidentVerificationConfig(api_key="test-key", frame_count=4)

        result = verify_incident(
            frames,
            [{"cls_name": "mild", "conf": 0.71}],
            config=config,
            post=post,
        )

        self.assertEqual(result, valid_result())
        args, kwargs = post.call_args
        self.assertEqual(args[0], "https://developer.amd.com.cn/radeon/api/v1/chat/completions")
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer test-key")
        self.assertEqual(kwargs["json"]["model"], "DeepSeek-V4-Flash-Vision-Exp")
        content = kwargs["json"]["messages"][1]["content"]
        image_parts = [part for part in content if part["type"] == "image_url"]
        self.assertEqual(len(image_parts), 4)

    def test_api_failure_returns_uncertain_for_human_review(self):
        post = Mock(side_effect=requests.Timeout("test timeout"))
        result = verify_incident(
            [np.zeros((24, 24, 3), dtype=np.uint8)],
            [],
            config=IncidentVerificationConfig(api_key="test-key"),
            post=post,
        )

        self.assertEqual(result["verdict"], "uncertain")
        self.assertEqual(result["recommended_action"], "human_review")
        self.assertIn("Timeout", result["reasoning_summary"])

    def test_primary_incident_result_fallback_is_uncertain(self):
        self.assertEqual(_empty_result("test reason")["severity"], "unknown")

    def test_hazard_evidence_cannot_be_returned_as_false_positive(self):
        result = valid_result()
        result["verdict"] = "likely_false_positive"
        result["incident_types"] = ["fire_or_explosion"]
        result["hazards_detected"] = ["Visible flames"]

        guarded = _apply_hazard_safety_guard(result)

        self.assertEqual(guarded["verdict"], "likely_fire_or_hazard")
        self.assertEqual(guarded["recommended_action"], "urgent_alert_review")


if __name__ == "__main__":
    unittest.main()