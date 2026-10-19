import hashlib
import hmac
import json
import os
import secrets
from datetime import datetime, timezone
from pathlib import Path

HASH_NAME = 'sha256'
HASH_ITERATIONS = 600_000
SALT_BYTES = 32
CONFIG_VERSION = 1
SUPER_ADMIN_USERNAME = 'admin'
SUPER_ADMIN_DEFAULT_PASSWORD = 'admin123'
SUPER_ADMIN_ROLE = 'super_admin'
ADMIN_ROLE = 'admin'

class AuthStorageError(Exception):
    pass


class AdminCredentials:
    def __init__(self, path=None):
        if path is None:
            root = Path(os.environ.get('APPDATA', Path.home()))
            path = root / 'PhenoCoater' / 'admin_credentials.json'
        self.path = Path(path)
        self._ensure_parent_dir()

    def _ensure_parent_dir(self):
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise AuthStorageError(f'Could not prepare administrator credential storage: {exc}') from exc

    def is_configured(self):
        try:
            store = self._read_store()
        except AuthStorageError:
            return False
        return bool(store.get('accounts'))

    def ensure_default_super_admin(self):
        try:
            store = self._read_store()
        except AuthStorageError:
            store = {'accounts': []}

        existing = self._find_account(store, SUPER_ADMIN_USERNAME)
        if existing is not None:
            if existing.get('role') is None:
                existing['role'] = SUPER_ADMIN_ROLE
            if existing.get('is_active') is None:
                existing['is_active'] = True
            if not existing.get('name'):
                existing['name'] = 'Super Admin'
            self._persist_store(store)
            return existing

        account = self._build_account(
            name='Super Admin',
            username=SUPER_ADMIN_USERNAME,
            password=SUPER_ADMIN_DEFAULT_PASSWORD,
            role=SUPER_ADMIN_ROLE,
        )
        store.setdefault('accounts', []).append(account)
        store['super_admin_username'] = SUPER_ADMIN_USERNAME
        store['algorithm'] = 'pbkdf2_hmac'
        store['hash'] = HASH_NAME
        store['iterations'] = HASH_ITERATIONS
        store['salt'] = account['salt']
        store['password_hash'] = account['password_hash']
        self._persist_store(store)
        return account

    def create_initial_admin(self, secret, confirmation):
        if not secret:
            raise ValueError('Please provide a password.')
        if secret != confirmation:
            raise ValueError('The passwords do not match.')

        try:
            store = self._read_store()
        except AuthStorageError:
            store = {'accounts': []}

        if store.get('accounts'):
            raise ValueError('An administrator is already configured.')

        account = self._build_account(
            name='Super Admin',
            username=SUPER_ADMIN_USERNAME,
            password=secret,
            role=SUPER_ADMIN_ROLE,
        )
        payload = {
            'version': CONFIG_VERSION,
            'algorithm': 'pbkdf2_hmac',
            'hash': HASH_NAME,
            'iterations': HASH_ITERATIONS,
            'salt': account['salt'],
            'password_hash': account['password_hash'],
            'accounts': [account],
            'super_admin_username': SUPER_ADMIN_USERNAME,
        }
        self._persist_store(payload)
        return self._public_account(account)

    def authenticate(self, username, secret):
        if not username or not isinstance(username, str):
            return None
        account = self._read_account(username)
        if account is None:
            return None
        if not account.get('is_active', True):
            return None
        if not self._verify_hash(
            secret,
            account.get('salt'),
            account.get('password_hash'),
            account.get('iterations', HASH_ITERATIONS),
        ):
            return None
        return self._public_account(account)

    def verify_password(self, secret, username=SUPER_ADMIN_USERNAME):
        account = self._read_account(username)
        if account is None:
            legacy = self._read_legacy_credentials()
            if legacy is None:
                return False
            return self._verify_legacy_password(secret, legacy)
        return self._verify_hash(
            secret,
            account.get('salt'),
            account.get('password_hash'),
            account.get('iterations', HASH_ITERATIONS),
        )

    def verify_login(self, username, secret):
        return self.authenticate(username, secret) is not None

    def list_accounts(self):
        store = self._read_store()
        accounts = []
        for account in store.get('accounts', []):
            accounts.append(self._public_account(account))
        return sorted(accounts, key=lambda item: item['username'].lower())

    def create_account(self, name, username, secret, role=ADMIN_ROLE):
        if not name or not str(name).strip():
            raise ValueError('Please provide the administrator name.')
        username = str(username).strip()
        if not username:
            raise ValueError('Please provide a username.')
        if not secret:
            raise ValueError('Please provide a password.')
        if role not in {ADMIN_ROLE, SUPER_ADMIN_ROLE}:
            raise ValueError('Unsupported administrator role.')
        if role == SUPER_ADMIN_ROLE:
            raise ValueError('A new Super Admin account cannot be created from the application.')

        store = self._read_store()
        if self._find_account(store, username) is not None:
            raise ValueError('That username is already in use.')

        account = self._build_account(
            name=name.strip(),
            username=username,
            password=secret,
            role=role,
        )
        store.setdefault('accounts', []).append(account)
        self._persist_store(store)
        return self._public_account(account)

    def update_account(self, username, *, name=None, role=None):
        store = self._read_store()
        account = self._find_account(store, username)
        if account is None:
            raise ValueError('Administrator account not found.')
        if account.get('role') == SUPER_ADMIN_ROLE:
            raise ValueError('The permanent Super Admin account cannot be modified.')
        if name is not None:
            name = str(name).strip()
            if not name:
                raise ValueError('The administrator name cannot be empty.')
            account['name'] = name
        if role is not None:
            if role == SUPER_ADMIN_ROLE:
                raise ValueError('Administrators cannot be promoted to the Super Admin role.')
            if role not in {ADMIN_ROLE, SUPER_ADMIN_ROLE}:
                raise ValueError('Unsupported administrator role.')
            account['role'] = role
        self._persist_store(store)
        return self._public_account(account)

    def reset_password(self, username, new_secret):
        store = self._read_store()
        account = self._find_account(store, username)
        if account is None:
            raise ValueError('Administrator account not found.')
        if account.get('role') == SUPER_ADMIN_ROLE:
            raise ValueError('The permanent Super Admin account cannot be reset through this interface.')
        if not new_secret:
            raise ValueError('Please provide a password.')
        account['salt'] = secrets.token_bytes(SALT_BYTES).hex()
        account['password_hash'] = self._derive(
            new_secret,
            bytes.fromhex(account['salt']),
            account.get('iterations', HASH_ITERATIONS),
        ).hex()
        account['updated_at'] = datetime.now(timezone.utc).isoformat()
        self._persist_store(store)
        return self._public_account(account)

    def disable_account(self, username, disabled=True):
        store = self._read_store()
        account = self._find_account(store, username)
        if account is None:
            raise ValueError('Administrator account not found.')
        if account.get('role') == SUPER_ADMIN_ROLE:
            raise ValueError('The permanent Super Admin account cannot be disabled.')
        account['is_active'] = not disabled
        self._persist_store(store)
        return self._public_account(account)

    def delete_account(self, username):
        store = self._read_store()
        account = self._find_account(store, username)
        if account is None:
            raise ValueError('Administrator account not found.')
        if account.get('role') == SUPER_ADMIN_ROLE:
            raise ValueError('The permanent Super Admin account cannot be deleted.')
        store['accounts'] = [
            item for item in store.get('accounts', [])
            if item['username'].lower() != username.lower()
        ]
        self._persist_store(store)
        return True

    def _read_store(self):
        try:
            if not self.path.exists():
                return {'accounts': []}
            data = self.path.read_text(encoding='utf-8')
            if not data.strip():
                return {'accounts': []}
            payload = json.loads(data)
        except FileNotFoundError:
            return {'accounts': []}
        except (OSError, json.JSONDecodeError) as exc:
            raise AuthStorageError(f'Could not read administrator credentials: {exc}') from exc

        if isinstance(payload, dict) and 'accounts' in payload:
            return payload

        if self._looks_like_legacy_payload(payload):
            return self._legacy_store(payload)

        raise AuthStorageError('Administrator credentials are corrupt or use an unsupported format.')

    @staticmethod
    def _looks_like_legacy_payload(payload):
        return (
            isinstance(payload, dict)
            and payload.get('version') == CONFIG_VERSION
            and payload.get('algorithm') == 'pbkdf2_hmac'
            and payload.get('hash') == HASH_NAME
            and payload.get('salt')
            and payload.get('password_hash')
        )

    def _legacy_store(self, payload):
        username = payload.get('username', SUPER_ADMIN_USERNAME)
        name = payload.get('name', 'Super Admin')
        account = {
            'username': username,
            'name': name,
            'role': payload.get('role', SUPER_ADMIN_ROLE),
            'is_active': payload.get('is_active', True),
            'salt': payload.get('salt'),
            'password_hash': payload.get('password_hash'),
            'iterations': payload.get('iterations', HASH_ITERATIONS),
            'created_at': payload.get('created_at') or datetime.now(timezone.utc).isoformat(),
            'updated_at': payload.get('updated_at') or datetime.now(timezone.utc).isoformat(),
        }
        return {
            'version': payload.get('version'),
            'algorithm': payload.get('algorithm'),
            'hash': payload.get('hash'),
            'iterations': payload.get('iterations', HASH_ITERATIONS),
            'super_admin_username': username,
            'accounts': [account],
        }

    def _read_legacy_credentials(self):
        try:
            if not self.path.exists():
                return None
            payload = json.loads(self.path.read_text(encoding='utf-8'))
        except (FileNotFoundError, OSError, json.JSONDecodeError):
            return None
        if self._looks_like_legacy_payload(payload):
            return payload
        return None

    def _read_account(self, username):
        if not username:
            return None
        store = self._read_store()
        return self._find_account(store, username)

    def _find_account(self, store, username):
        for account in store.get('accounts', []):
            if str(account.get('username', '')).lower() == str(username).lower():
                return account
        return None

    def _build_account(self, *, name, username, password=None, secret=None, role):
        if password is None:
            password = secret
        secret_value = password if password is not None else secret
        salt = secrets.token_bytes(SALT_BYTES)
        iterations = HASH_ITERATIONS
        return {
            'username': username.strip(),
            'name': name.strip(),
            'role': role,
            'is_active': True,
            'salt': salt.hex(),
            'password_hash': self._derive(secret_value, salt, iterations).hex(),
            'iterations': iterations,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'updated_at': datetime.now(timezone.utc).isoformat(),
        }

    def _persist_store(self, payload):
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            encoded = json.dumps(payload, separators=(',', ':'), indent=None).encode('utf-8')
            descriptor = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(descriptor, 'wb') as credential_file:
                credential_file.write(encoded)
                credential_file.flush()
                os.fsync(credential_file.fileno())
        except OSError as exc:
            raise AuthStorageError(f'Could not save administrator credentials: {exc}') from exc

    def _public_account(self, account):
        return {
            'username': account.get('username'),
            'name': account.get('name'),
            'role': account.get('role', ADMIN_ROLE),
            'is_active': account.get('is_active', True),
        }

    @staticmethod
    def _derive(secret, salt, iterations):
        return hashlib.pbkdf2_hmac(
            HASH_NAME,
            str(secret).encode('utf-8'),
            salt,
            iterations,
        )

    @staticmethod
    def _verify_hash(secret, salt_hex, password_hash_hex, iterations):
        try:
            salt = bytes.fromhex(salt_hex)
            candidate = AdminCredentials._derive(secret, salt, iterations)
            return hmac.compare_digest(candidate.hex(), password_hash_hex)
        except (TypeError, ValueError):
            return False

    @staticmethod
    def _verify_legacy_password(secret, credential):
        candidate = AdminCredentials._derive(
            secret,
            bytes.fromhex(credential['salt']),
            credential.get('iterations', HASH_ITERATIONS),
        )
        return hmac.compare_digest(candidate.hex(), credential['password_hash'])


class AdminSession:
    def __init__(self):
        self._authenticated = False
        self.username = None
        self.display_name = None
        self.role = None

    @property
    def is_admin(self):
        return self._authenticated and self.role in {ADMIN_ROLE, SUPER_ADMIN_ROLE}

    @property
    def is_super_admin(self):
        return self._authenticated and self.role == SUPER_ADMIN_ROLE

    def grant_admin(self, username=None, role=ADMIN_ROLE, display_name=None):
        self._authenticated = True
        self.username = username or SUPER_ADMIN_USERNAME
        self.role = role or ADMIN_ROLE
        self.display_name = display_name or self.username

    def revoke(self):
        self._authenticated = False
        self.username = None
        self.display_name = None
        self.role = None

    def require_admin(self):
        if not self.is_admin:
            raise PermissionError('Administrator access is required.')

    def can_manage_admin_accounts(self):
        return self.is_super_admin

    def can_create_admin_accounts(self):
        return self.is_super_admin

    def can_view_camera_and_nir(self):
        return self.is_admin

    def can_access_admin_controls(self):
        return self.is_admin
