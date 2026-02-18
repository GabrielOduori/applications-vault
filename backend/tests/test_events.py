class TestEvents:
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

    def test_add_event(self, client, tmp_vault):
        token = self._setup_and_unlock(client, tmp_vault)
        job_id = self._create_job(client, token)

        r = client.post(f"/api/v1/jobs/{job_id}/events", json={
            "event_type": "SHORTLISTED",
            "notes": "Made it to shortlist",
        }, headers=self._auth(token))
        assert r.status_code == 201
        assert r.json()["event_type"] == "SHORTLISTED"

        # Job status should be updated
        job_r = client.get(f"/api/v1/jobs/{job_id}", headers=self._auth(token))
        assert job_r.json()["status"] == "SHORTLISTED"

    def test_event_timeline(self, client, tmp_vault):
        token = self._setup_and_unlock(client, tmp_vault)
        job_id = self._create_job(client, token)
        h = self._auth(token)

        client.post(f"/api/v1/jobs/{job_id}/events", json={"event_type": "SHORTLISTED"}, headers=h)
        client.post(f"/api/v1/jobs/{job_id}/events", json={"event_type": "INTERVIEW"}, headers=h)

        r = client.get(f"/api/v1/jobs/{job_id}/events", headers=h)
        assert r.status_code == 200
        events = r.json()
        assert len(events) == 3  # SAVED (auto) + SHORTLISTED + INTERVIEW
        assert events[0]["event_type"] == "SAVED"
        assert events[2]["event_type"] == "INTERVIEW"

    def test_invalid_event_type(self, client, tmp_vault):
        token = self._setup_and_unlock(client, tmp_vault)
        job_id = self._create_job(client, token)

        r = client.post(f"/api/v1/jobs/{job_id}/events", json={
            "event_type": "INVALID",
        }, headers=self._auth(token))
        assert r.status_code == 400

    def test_upcoming_events(self, client, tmp_vault):
        token = self._setup_and_unlock(client, tmp_vault)
        job_id = self._create_job(client, token)

        client.post(f"/api/v1/jobs/{job_id}/events", json={
            "event_type": "INTERVIEW",
            "next_action_date": "2099-12-31",
        }, headers=self._auth(token))

        r = client.get("/api/v1/events/upcoming", headers=self._auth(token))
        assert r.status_code == 200
        assert len(r.json()) >= 1

    # --- P2: Auto follow-up reminders on SUBMITTED ---

    def test_submitted_event_creates_follow_up_reminders(self, client, tmp_vault):
        token = self._setup_and_unlock(client, tmp_vault)
        job_id = self._create_job(client, token)
        h = self._auth(token)

        client.post(f"/api/v1/jobs/{job_id}/events", json={
            "event_type": "SUBMITTED",
            "notes": "Applied via website",
        }, headers=h)

        r = client.get(f"/api/v1/jobs/{job_id}/events", headers=h)
        events = r.json()
        # SAVED (auto) + SUBMITTED + 2 follow-up reminders = 4 total
        assert len(events) == 4
        submitted_events = [e for e in events if e["event_type"] == "SUBMITTED"]
        assert len(submitted_events) == 3  # main + 2 reminders

    def test_submitted_reminders_have_next_action_dates(self, client, tmp_vault):
        token = self._setup_and_unlock(client, tmp_vault)
        job_id = self._create_job(client, token)
        h = self._auth(token)

        client.post(f"/api/v1/jobs/{job_id}/events", json={"event_type": "SUBMITTED"}, headers=h)

        r = client.get(f"/api/v1/jobs/{job_id}/events", headers=h)
        events = r.json()
        # Both follow-up reminders should have next_action_date set
        reminders = [e for e in events if e["event_type"] == "SUBMITTED" and e["next_action_date"]]
        assert len(reminders) == 2

    def test_submitted_reminders_appear_in_upcoming(self, client, tmp_vault):
        token = self._setup_and_unlock(client, tmp_vault)
        job_id = self._create_job(client, token)
        h = self._auth(token)

        client.post(f"/api/v1/jobs/{job_id}/events", json={"event_type": "SUBMITTED"}, headers=h)

        r = client.get("/api/v1/events/upcoming", headers=h)
        assert r.status_code == 200
        upcoming = r.json()
        # At least 2 reminders should appear in upcoming events
        assert len(upcoming) >= 2

    def test_non_submitted_events_do_not_create_reminders(self, client, tmp_vault):
        token = self._setup_and_unlock(client, tmp_vault)
        job_id = self._create_job(client, token)
        h = self._auth(token)

        client.post(f"/api/v1/jobs/{job_id}/events", json={"event_type": "SHORTLISTED"}, headers=h)

        r = client.get(f"/api/v1/jobs/{job_id}/events", headers=h)
        events = r.json()
        # SAVED (auto) + SHORTLISTED only — no extras
        assert len(events) == 2
