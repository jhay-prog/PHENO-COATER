import json
import tempfile
import unittest
from pathlib import Path

from GUI.auth import (
    AdminCredentials,
    AdminSession,
    AuthStorageError,
)


class AdminCredentialsTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.credential_path = Path(self.temp_dir.name) / "admin.json"
        self.credentials = AdminCredentials(self.credential_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_initial_setup_and_password_login(self):
        self.assertFalse(self.credentials.is_configured())
        password = "cacao-inspection-admin"
        self.credentials.create_initial_admin(password, password)

        self.assertTrue(self.credentials.is_configured())
        self.assertTrue(self.credentials.verify_password(password))
        self.assertFalse(self.credentials.verify_password("incorrect-password"))
        stored = json.loads(self.credential_path.read_text(encoding="utf-8"))
        self.assertNotIn(password, self.credential_path.read_text(encoding="utf-8"))
        self.assertEqual(stored["algorithm"], "pbkdf2_hmac")
        self.assertEqual(len(bytes.fromhex(stored["salt"])), 32)

    def test_setup_accepts_short_nonempty_password_and_rejects_empty_or_mismatch(self):
        self.credentials.create_initial_admin("short", "short")
        self.assertTrue(self.credentials.verify_password("short"))

        self.credential_path.unlink()
        with self.assertRaises(ValueError):
            self.credentials.create_initial_admin(
                "",
                "",
            )
        with self.assertRaises(ValueError):
            self.credentials.create_initial_admin(
                "short",
                "other",
            )
        self.assertFalse(self.credentials.is_configured())

    def test_admin_creation_and_password_reset_accept_short_passwords(self):
        self.credentials.ensure_default_super_admin()
        self.credentials.create_account("Operator", "operator", "short")
        self.assertTrue(self.credentials.verify_password("short", "operator"))

        self.credentials.reset_password("operator", "new")
        self.assertTrue(self.credentials.verify_password("new", "operator"))

        with self.assertRaisesRegex(ValueError, "provide a password"):
            self.credentials.reset_password("operator", "")

    def test_initial_setup_cannot_replace_existing_credentials(self):
        self.credentials.create_initial_admin(
            "cacao-inspection-admin",
            "cacao-inspection-admin",
        )
        with self.assertRaises(ValueError):
            self.credentials.create_initial_admin(
                "another-valid-password",
                "another-valid-password",
            )

    def test_corrupt_credentials_fail_explicitly(self):
        self.credential_path.write_text("{invalid", encoding="utf-8")
        with self.assertRaises(AuthStorageError):
            self.credentials.verify_password("any-password")


class AdminSessionTests(unittest.TestCase):
    def test_verified_login_grants_access_and_logout_revokes_it(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            credentials = AdminCredentials(Path(temp_dir) / "admin.json")
            password = "cacao-inspection-admin"
            credentials.create_initial_admin(password, password)
            session = AdminSession()

            if credentials.verify_password(password):
                session.grant_admin()
            session.require_admin()

            session.revoke()
            with self.assertRaises(PermissionError):
                session.require_admin()

    def test_login_logout_and_permission_revocation(self):
        session = AdminSession()
        self.assertFalse(session.is_admin)
        with self.assertRaises(PermissionError):
            session.require_admin()

        session.grant_admin()
        self.assertTrue(session.is_admin)
        session.require_admin()

        session.revoke()
        self.assertFalse(session.is_admin)
        with self.assertRaises(PermissionError):
            session.require_admin()


if __name__ == "__main__":
    unittest.main()
