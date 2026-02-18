class TestSearch:
    def _setup_and_unlock(self, client, tmp_vault):
        client.post("/api/v1/vault/setup", json={
            "passphrase": "test-passphrase-123",
            "vault_path": str(tmp_vault),
        })
        r = client.post("/api/v1/vault/unlock", json={"passphrase": "test-passphrase-123"})
        return r.json()["token"]

    def _auth(self, token):
        return {"Authorization": f"Bearer {token}"}

    def test_search_by_job_title(self, client, tmp_vault):
        token = self._setup_and_unlock(client, tmp_vault)
        h = self._auth(token)
        client.post("/api/v1/jobs", json={
            "title": "Quantum Engineer",
            "organisation": "FutureLabs",
        }, headers=h)

        r = client.get("/api/v1/search?q=Quantum", headers=h)
        assert r.status_code == 200
        data = r.json()
        assert data["query"] == "Quantum"
        assert data["total"] >= 1
        assert any("Quantum" in res["job_title"] for res in data["results"])

    def test_search_by_organisation(self, client, tmp_vault):
        token = self._setup_and_unlock(client, tmp_vault)
        h = self._auth(token)
        client.post("/api/v1/jobs", json={
            "title": "Researcher",
            "organisation": "UniqueOrg",
        }, headers=h)

        r = client.get("/api/v1/search?q=UniqueOrg", headers=h)
        assert r.status_code == 200
        data = r.json()
        assert data["total"] >= 1
        assert any(res["organisation"] == "UniqueOrg" for res in data["results"])

    def test_search_in_captures(self, client, tmp_vault):
        token = self._setup_and_unlock(client, tmp_vault)
        h = self._auth(token)
        job_r = client.post("/api/v1/jobs", json={"title": "Developer Job"}, headers=h)
        job_id = job_r.json()["id"]
        client.post(f"/api/v1/jobs/{job_id}/captures", json={
            "text_snapshot": "Must have experience with distributed systems and microservices",
            "capture_method": "manual_paste",
        }, headers=h)

        r = client.get("/api/v1/search?q=microservices&scope=captures", headers=h)
        assert r.status_code == 200
        data = r.json()
        assert data["total"] >= 1
        assert all(res["source"] == "capture" for res in data["results"])
        assert any(res["job_id"] == job_id for res in data["results"])

    def test_search_scope_jobs_only(self, client, tmp_vault):
        token = self._setup_and_unlock(client, tmp_vault)
        h = self._auth(token)
        client.post("/api/v1/jobs", json={"title": "Backend Engineer"}, headers=h)

        r = client.get("/api/v1/search?q=Backend&scope=jobs", headers=h)
        assert r.status_code == 200
        data = r.json()
        assert data["total"] >= 1
        assert all(res["source"] == "job" for res in data["results"])

    def test_search_scope_all_includes_both_sources(self, client, tmp_vault):
        token = self._setup_and_unlock(client, tmp_vault)
        h = self._auth(token)
        job_r = client.post("/api/v1/jobs", json={
            "title": "FullStack Developer",
            "notes": "Fullstack role",
        }, headers=h)
        job_id = job_r.json()["id"]
        client.post(f"/api/v1/jobs/{job_id}/captures", json={
            "text_snapshot": "FullStack experience required",
            "capture_method": "manual_paste",
        }, headers=h)

        r = client.get("/api/v1/search?q=FullStack&scope=all", headers=h)
        assert r.status_code == 200
        data = r.json()
        sources = {res["source"] for res in data["results"]}
        assert "job" in sources
        assert "capture" in sources

    def test_search_no_match_returns_empty(self, client, tmp_vault):
        token = self._setup_and_unlock(client, tmp_vault)
        h = self._auth(token)

        r = client.get("/api/v1/search?q=xyznonexistentterm99999", headers=h)
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 0
        assert data["results"] == []

    def test_search_result_has_snippet(self, client, tmp_vault):
        token = self._setup_and_unlock(client, tmp_vault)
        h = self._auth(token)
        client.post("/api/v1/jobs", json={"title": "DataScientist"}, headers=h)

        r = client.get("/api/v1/search?q=DataScientist", headers=h)
        assert r.status_code == 200
        results = r.json()["results"]
        assert len(results) >= 1
        assert results[0]["snippet"] != ""
        assert "job_id" in results[0]
        assert "job_title" in results[0]

    def test_search_requires_auth(self, client, tmp_vault):
        self._setup_and_unlock(client, tmp_vault)
        r = client.get("/api/v1/search?q=anything", headers={"Authorization": "Bearer invalid_token"})
        assert r.status_code == 401

    def test_search_empty_query_rejected(self, client, tmp_vault):
        token = self._setup_and_unlock(client, tmp_vault)
        r = client.get("/api/v1/search?q=", headers=self._auth(token))
        assert r.status_code == 422

    def test_search_invalid_scope_rejected(self, client, tmp_vault):
        token = self._setup_and_unlock(client, tmp_vault)
        r = client.get("/api/v1/search?q=test&scope=invalid", headers=self._auth(token))
        assert r.status_code == 422
