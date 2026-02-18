class TestCaptures:
    def _setup_and_unlock(self, client, tmp_vault):
        client.post("/api/v1/vault/setup", json={
            "passphrase": "test-passphrase-123",
            "vault_path": str(tmp_vault),
        })
        r = client.post("/api/v1/vault/unlock", json={"passphrase": "test-passphrase-123"})
        return r.json()["token"]

    def _auth(self, token):
        return {"Authorization": f"Bearer {token}"}

    def _create_job(self, client, token):
        r = client.post("/api/v1/jobs", json={"title": "Test Job"}, headers=self._auth(token))
        return r.json()["id"]

    def test_create_capture(self, client, tmp_vault):
        token = self._setup_and_unlock(client, tmp_vault)
        job_id = self._create_job(client, token)

        r = client.post(f"/api/v1/jobs/{job_id}/captures", json={
            "url": "https://example.com/job/123",
            "page_title": "Software Engineer at Acme",
            "text_snapshot": "We are looking for a software engineer...",
            "capture_method": "generic_html",
        }, headers=self._auth(token))
        assert r.status_code == 201
        data = r.json()
        assert data["text_snapshot"] == "We are looking for a software engineer..."

    def test_create_capture_with_html(self, client, tmp_vault):
        token = self._setup_and_unlock(client, tmp_vault)
        job_id = self._create_job(client, token)

        r = client.post(f"/api/v1/jobs/{job_id}/captures", json={
            "text_snapshot": "Job description text",
            "html_content": "<html><body><h1>Job</h1></body></html>",
            "capture_method": "generic_html",
        }, headers=self._auth(token))
        assert r.status_code == 201
        assert r.json()["html_path"] is not None

    def test_list_captures(self, client, tmp_vault):
        token = self._setup_and_unlock(client, tmp_vault)
        job_id = self._create_job(client, token)
        h = self._auth(token)

        client.post(f"/api/v1/jobs/{job_id}/captures", json={
            "text_snapshot": "Capture 1",
            "capture_method": "manual_paste",
        }, headers=h)

        r = client.get(f"/api/v1/jobs/{job_id}/captures", headers=h)
        assert r.status_code == 200
        assert len(r.json()) == 1

    def test_quick_capture(self, client, tmp_vault):
        token = self._setup_and_unlock(client, tmp_vault)

        r = client.post("/api/v1/captures/quick", json={
            "url": "https://example.com/job/456",
            "page_title": "Data Scientist at BigCo",
            "text_snapshot": "Seeking a data scientist...",
            "capture_method": "generic_html",
            "title": "Data Scientist",
            "organisation": "BigCo",
        }, headers=self._auth(token))
        assert r.status_code == 201
        data = r.json()
        assert data["job"]["title"] == "Data Scientist"
        assert data["capture"]["text_snapshot"] == "Seeking a data scientist..."
