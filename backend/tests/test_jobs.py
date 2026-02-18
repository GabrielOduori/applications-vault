import pytest


class TestJobsCRUD:
    def _setup_and_unlock(self, client, tmp_vault):
        client.post("/api/v1/vault/setup", json={
            "passphrase": "test-passphrase-123",
            "vault_path": str(tmp_vault),
        })
        r = client.post("/api/v1/vault/unlock", json={"passphrase": "test-passphrase-123"})
        return r.json()["token"]

    def _auth(self, token):
        return {"Authorization": f"Bearer {token}"}

    def test_create_job(self, client, tmp_vault):
        token = self._setup_and_unlock(client, tmp_vault)
        r = client.post("/api/v1/jobs", json={
            "title": "Software Engineer",
            "organisation": "Acme Corp",
            "url": "https://example.com/job/123",
        }, headers=self._auth(token))
        assert r.status_code == 201
        data = r.json()
        assert data["title"] == "Software Engineer"
        assert data["organisation"] == "Acme Corp"
        assert data["status"] == "SAVED"
        assert data["event_count"] == 1  # auto SAVED event

    def test_list_jobs(self, client, tmp_vault):
        token = self._setup_and_unlock(client, tmp_vault)
        h = self._auth(token)
        client.post("/api/v1/jobs", json={"title": "Job 1"}, headers=h)
        client.post("/api/v1/jobs", json={"title": "Job 2"}, headers=h)

        r = client.get("/api/v1/jobs", headers=h)
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 2
        assert len(data["jobs"]) == 2

    def test_get_job(self, client, tmp_vault):
        token = self._setup_and_unlock(client, tmp_vault)
        h = self._auth(token)
        create_r = client.post("/api/v1/jobs", json={"title": "Test Job"}, headers=h)
        job_id = create_r.json()["id"]

        r = client.get(f"/api/v1/jobs/{job_id}", headers=h)
        assert r.status_code == 200
        assert r.json()["title"] == "Test Job"

    def test_update_job(self, client, tmp_vault):
        token = self._setup_and_unlock(client, tmp_vault)
        h = self._auth(token)
        create_r = client.post("/api/v1/jobs", json={"title": "Old Title"}, headers=h)
        job_id = create_r.json()["id"]

        r = client.put(f"/api/v1/jobs/{job_id}", json={"title": "New Title"}, headers=h)
        assert r.status_code == 200
        assert r.json()["title"] == "New Title"

    def test_delete_job(self, client, tmp_vault):
        token = self._setup_and_unlock(client, tmp_vault)
        h = self._auth(token)
        create_r = client.post("/api/v1/jobs", json={"title": "To Delete"}, headers=h)
        job_id = create_r.json()["id"]

        r = client.delete(f"/api/v1/jobs/{job_id}", headers=h)
        assert r.status_code == 200

        r = client.get(f"/api/v1/jobs/{job_id}", headers=h)
        assert r.status_code == 404

    def test_filter_by_status(self, client, tmp_vault):
        token = self._setup_and_unlock(client, tmp_vault)
        h = self._auth(token)
        client.post("/api/v1/jobs", json={"title": "Job 1"}, headers=h)

        r = client.get("/api/v1/jobs?status=SAVED", headers=h)
        assert r.json()["total"] == 1

        r = client.get("/api/v1/jobs?status=SUBMITTED", headers=h)
        assert r.json()["total"] == 0

    def test_requires_auth(self, client, tmp_vault):
        r = client.post("/api/v1/jobs", json={"title": "Test"})
        assert r.status_code == 422  # missing header
