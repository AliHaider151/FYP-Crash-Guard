import unittest
from unittest.mock import Mock, patch

from app.services.firebase_service import get_db, is_stale_fcm_token_error, save_verification_to_firestore


class FirebaseServiceTests(unittest.TestCase):
    def setUp(self):
        import app.services.firebase_service as firebase_service

        self.firebase_service = firebase_service
        self.previous_db = firebase_service._db
        firebase_service._db = None

    def tearDown(self):
        self.firebase_service._db = self.previous_db

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

    def test_get_db_loads_credentials_from_json_environment_config(self):
        config = Mock(firebase_credentials_json='{"type":"service_account"}')
        db = Mock()

        with (
            patch("app.services.firebase_service.get_config", return_value=config),
            patch(
                "app.services.firebase_service.credentials.Certificate",
                return_value="credential",
            ) as certificate,
            patch("app.services.firebase_service.firebase_admin.initialize_app") as initialize,
            patch("app.services.firebase_service.firestore.client", return_value=db),
        ):
            result = get_db()

        certificate.assert_called_once_with({"type": "service_account"})
        initialize.assert_called_once_with("credential")
        self.assertIs(result, db)

    def test_get_db_rejects_invalid_credentials_json(self):
        config = Mock(firebase_credentials_json="not-json")

        with (
            patch("app.services.firebase_service.get_config", return_value=config),
            self.assertRaisesRegex(ValueError, "enclose the complete JSON object"),
        ):
            get_db()

    def test_get_db_requires_service_account_json(self):
        config = Mock(firebase_credentials_json="")

        with (
            patch("app.services.firebase_service.get_config", return_value=config),
            self.assertRaisesRegex(ValueError, "FIREBASE_SERVICE_ACCOUNT_JSON is required"),
        ):
            get_db()


if __name__ == "__main__":
    unittest.main()
