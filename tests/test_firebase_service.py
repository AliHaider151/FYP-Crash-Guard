import unittest
from unittest.mock import Mock, patch

from app.services.firebase_service import is_stale_fcm_token_error, save_verification_to_firestore


class FirebaseServiceTests(unittest.TestCase):
    def test_detects_unregistered_device_error(self):
        self.assertTrue(is_stale_fcm_token_error(Exception("Device unregistered.")))
        self.assertTrue(is_stale_fcm_token_error(Exception("Registration token is not registered")))
        self.assertFalse(is_stale_fcm_token_error(Exception("other network issue")))

    def test_saves_verification_as_firestore_merge(self):
        document = Mock()
        collection = Mock()
        collection.document.return_value = document
        db = Mock()
        db.collection.return_value = collection
        result = {"verdict": "uncertain", "confidence": 0}

        with patch("app.services.firebase_service.get_db", return_value=db):
            save_verification_to_firestore(123, result)

        db.collection.assert_called_once_with("accidents")
        collection.document.assert_called_once_with("123")
        document.set.assert_called_once_with({"verification": result}, merge=True)


if __name__ == "__main__":
    unittest.main()
