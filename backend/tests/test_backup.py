import csv
import io
import zipfile


class TestBackup:
    def _setup_and_unlock(self, client, tmp_vault):
        client.post("/api/v1/vault/setup", json={
            "passphrase": "test-passphrase-123",
            "vault_path": str(tmp_vault),
        })
        r = client.post("/api/v1/vault/unlock", json={"passphrase": "test-passphrase-123"})
        return r.json()["token"]

    def _auth(self, token):
        return {"Authorization": f"Bearer {token}"}

    def _export_token(self, client):
        r = client.post("/api/v1/vault/export-token", json={"passphrase": "test-passphrase-123"})
        return r.json()["token"]

    def _export_auth(self, export_token):
        return {"X-Vault-Export-Token": export_token}

    def test_backup_export_is_valid_zip(self, client, tmp_vault):
        token = self._setup_and_unlock(client, tmp_vault)
        h = self._auth(token)
        export_h = self._export_auth(self._export_token(client))

        r = client.post("/api/v1/backup/export", headers={**h, **export_h})
        assert r.status_code == 200
        assert "application/zip" in r.headers["content-type"]
        assert "attachment" in r.headers.get("content-disposition", "")

        buf = io.BytesIO(r.content)
        assert zipfile.is_zipfile(buf)

    def test_backup_contains_database(self, client, tmp_vault):
        token = self._setup_and_unlock(client, tmp_vault)
        h = self._auth(token)
        export_h = self._export_auth(self._export_token(client))
        client.post("/api/v1/jobs", json={"title": "Backed Up Job"}, headers=h)

        r = client.post("/api/v1/backup/export", headers={**h, **export_h})
        buf = io.BytesIO(r.content)
        with zipfile.ZipFile(buf) as zf:
            names = zf.namelist()
        # The vault db.sqlite must be present
        assert any("db.sqlite" in name for name in names)

    def test_csv_export_returns_correct_headers(self, client, tmp_vault):
        token = self._setup_and_unlock(client, tmp_vault)
        h = self._auth(token)
        export_h = self._export_auth(self._export_token(client))

        r = client.get("/api/v1/export/csv", headers={**h, **export_h})
        assert r.status_code == 200
        assert "text/csv" in r.headers["content-type"]

        reader = csv.reader(r.text.strip().splitlines())
        rows = list(reader)
        assert rows[0] == [
            "job_id", "title", "organisation", "url", "location", "salary_range",
            "deadline_type", "deadline_date", "status", "notes", "created_at", "updated_at",
        ]

    def test_csv_export_contains_job_data(self, client, tmp_vault):
        token = self._setup_and_unlock(client, tmp_vault)
        h = self._auth(token)
        export_h = self._export_auth(self._export_token(client))
        client.post("/api/v1/jobs", json={
            "title": "CSV Job",
            "organisation": "CSVCorp",
            "location": "London",
        }, headers=h)

        r = client.get("/api/v1/export/csv", headers={**h, **export_h})
        rows = list(csv.reader(r.text.strip().splitlines()))
        assert len(rows) == 2  # header + 1 job
        data_row = rows[1]
        assert "CSV Job" in data_row
        assert "CSVCorp" in data_row
        assert "London" in data_row

    def test_csv_export_multiple_jobs(self, client, tmp_vault):
        token = self._setup_and_unlock(client, tmp_vault)
        h = self._auth(token)
        export_h = self._export_auth(self._export_token(client))
        client.post("/api/v1/jobs", json={"title": "Job One"}, headers=h)
        client.post("/api/v1/jobs", json={"title": "Job Two"}, headers=h)

        r = client.get("/api/v1/export/csv", headers={**h, **export_h})
        rows = list(csv.reader(r.text.strip().splitlines()))
        assert len(rows) == 3  # header + 2 jobs

    def test_csv_no_jobs_only_header(self, client, tmp_vault):
        token = self._setup_and_unlock(client, tmp_vault)
        h = self._auth(token)
        export_h = self._export_auth(self._export_token(client))

        r = client.get("/api/v1/export/csv", headers={**h, **export_h})
        rows = list(csv.reader(r.text.strip().splitlines()))
        assert len(rows) == 1  # header only

    def test_json_export_structure(self, client, tmp_vault):
        token = self._setup_and_unlock(client, tmp_vault)
        h = self._auth(token)
        export_h = self._export_auth(self._export_token(client))

        r = client.get("/api/v1/export/json", headers={**h, **export_h})
        assert r.status_code == 200
        data = r.json()
        assert data["version"] == "1"
        assert "jobs" in data
        assert "tags" in data
        assert isinstance(data["jobs"], list)
        assert isinstance(data["tags"], list)

    def test_json_export_includes_nested_data(self, client, tmp_vault):
        token = self._setup_and_unlock(client, tmp_vault)
        h = self._auth(token)
        export_h = self._export_auth(self._export_token(client))
        job_r = client.post("/api/v1/jobs", json={
            "title": "JSON Job",
            "organisation": "JSONCorp",
        }, headers=h)
        job_id = job_r.json()["id"]
        client.post(f"/api/v1/jobs/{job_id}/captures", json={
            "text_snapshot": "Sample capture text for export",
            "capture_method": "manual_paste",
        }, headers=h)
        client.post(f"/api/v1/jobs/{job_id}/events", json={
            "event_type": "SHORTLISTED",
            "notes": "Looks promising",
        }, headers=h)

        r = client.get("/api/v1/export/json", headers={**h, **export_h})
        data = r.json()
        assert len(data["jobs"]) == 1
        job = data["jobs"][0]
        assert job["title"] == "JSON Job"
        assert job["organisation"] == "JSONCorp"
        assert len(job["captures"]) == 1
        assert job["captures"][0]["text_snapshot"] == "Sample capture text for export"
        # Events include the auto-SAVED event plus our SHORTLISTED event
        assert len(job["events"]) >= 2

    def test_json_export_includes_tags(self, client, tmp_vault):
        token = self._setup_and_unlock(client, tmp_vault)
        h = self._auth(token)
        export_h = self._export_auth(self._export_token(client))
        job_r = client.post("/api/v1/jobs", json={"title": "Tagged Job"}, headers=h)
        job_id = job_r.json()["id"]
        client.post(f"/api/v1/jobs/{job_id}/tags", json={"name": "priority"}, headers=h)

        r = client.get("/api/v1/export/json", headers={**h, **export_h})
        data = r.json()
        job = data["jobs"][0]
        assert len(job["tags"]) == 1
        assert job["tags"][0]["name"] == "priority"
        assert len(data["tags"]) == 1

    def test_backup_requires_auth(self, client, tmp_vault):
        self._setup_and_unlock(client, tmp_vault)
        r = client.post("/api/v1/backup/export", headers={"Authorization": "Bearer invalid_token"})
        assert r.status_code == 401

    def test_csv_requires_auth(self, client, tmp_vault):
        self._setup_and_unlock(client, tmp_vault)
        r = client.get("/api/v1/export/csv", headers={"Authorization": "Bearer invalid_token"})
        assert r.status_code == 401

    def test_json_requires_auth(self, client, tmp_vault):
        self._setup_and_unlock(client, tmp_vault)
        r = client.get("/api/v1/export/json", headers={"Authorization": "Bearer invalid_token"})
        assert r.status_code == 401
