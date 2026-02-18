import pytest


class TestVaultStatus:
    def test_status_before_setup(self, client):
        # DB already created by fixture, so initialized is True
        r = client.get("/api/v1/vault/status")
        assert r.status_code == 200
        data = r.json()
        assert data["locked"] is True

    def test_health(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"


class TestVaultSetup:
    def test_setup_creates_vault(self, client, tmp_vault):
        r = client.post("/api/v1/vault/setup", json={
            "passphrase": "test-passphrase-123",
            "vault_path": str(tmp_vault),
        })
        assert r.status_code == 200
        data = r.json()
        assert "recovery_key" in data
        assert len(data["recovery_key"]) > 20
        assert "vault_path" in data

    def test_setup_rejects_short_passphrase(self, client):
        r = client.post("/api/v1/vault/setup", json={"passphrase": "short"})
        assert r.status_code == 400

    def test_setup_rejects_duplicate(self, client, tmp_vault):
        client.post("/api/v1/vault/setup", json={
            "passphrase": "test-passphrase-123",
            "vault_path": str(tmp_vault),
        })
        r = client.post("/api/v1/vault/setup", json={
            "passphrase": "another-passphrase",
        })
        assert r.status_code == 409


class TestVaultUnlockLock:
    def _setup_vault(self, client, tmp_vault):
        r = client.post("/api/v1/vault/setup", json={
            "passphrase": "test-passphrase-123",
            "vault_path": str(tmp_vault),
        })
        return r.json()

    def test_unlock_with_passphrase(self, client, tmp_vault):
        self._setup_vault(client, tmp_vault)
        r = client.post("/api/v1/vault/unlock", json={
            "passphrase": "test-passphrase-123",
        })
        assert r.status_code == 200
        data = r.json()
        assert "token" in data
        assert len(data["token"]) == 64  # 32 bytes hex

    def test_unlock_with_recovery_key(self, client, tmp_vault):
        setup_data = self._setup_vault(client, tmp_vault)
        r = client.post("/api/v1/vault/unlock", json={
            "recovery_key": setup_data["recovery_key"],
        })
        assert r.status_code == 200
        assert "token" in r.json()

    def test_unlock_wrong_passphrase(self, client, tmp_vault):
        self._setup_vault(client, tmp_vault)
        r = client.post("/api/v1/vault/unlock", json={
            "passphrase": "wrong-passphrase",
        })
        assert r.status_code == 401

    def test_lock(self, client, tmp_vault):
        self._setup_vault(client, tmp_vault)
        unlock_r = client.post("/api/v1/vault/unlock", json={
            "passphrase": "test-passphrase-123",
        })
        token = unlock_r.json()["token"]

        # Lock
        r = client.post("/api/v1/vault/lock", headers={
            "Authorization": f"Bearer {token}",
        })
        assert r.status_code == 200

        # Verify locked
        status_r = client.get("/api/v1/vault/status")
        assert status_r.json()["locked"] is True

    def test_lock_requires_auth(self, client, tmp_vault):
        self._setup_vault(client, tmp_vault)
        r = client.post("/api/v1/vault/lock")
        assert r.status_code == 422  # missing header

    def test_lock_rejects_invalid_token(self, client, tmp_vault):
        self._setup_vault(client, tmp_vault)
        r = client.post("/api/v1/vault/lock", headers={
            "Authorization": "Bearer invalid-token",
        })
        assert r.status_code == 401


class TestVaultSettings:
    def test_update_auto_lock(self, client, tmp_vault):
        client.post("/api/v1/vault/setup", json={
            "passphrase": "test-passphrase-123",
            "vault_path": str(tmp_vault),
        })
        unlock_r = client.post("/api/v1/vault/unlock", json={
            "passphrase": "test-passphrase-123",
        })
        token = unlock_r.json()["token"]

        r = client.put("/api/v1/vault/settings", json={
            "auto_lock_seconds": 1800,
        }, headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
