class TestCalendar:
    def _setup_and_unlock(self, client, tmp_vault):
        client.post("/api/v1/vault/setup", json={
            "passphrase": "test-passphrase-123",
            "vault_path": str(tmp_vault),
        })
        r = client.post("/api/v1/vault/unlock", json={"passphrase": "test-passphrase-123"})
        return r.json()["token"]

    def _auth(self, token):
        return {"Authorization": f"Bearer {token}"}

    def _create_job_with_deadline(self, client, h, title="Test Job", deadline="2026-12-31"):
        r = client.post("/api/v1/jobs", json={
            "title": title,
            "organisation": "Test Corp",
            "deadline_date": deadline,
            "deadline_type": "fixed",
        }, headers=h)
        return r.json()["id"]

    def test_job_calendar_returns_ics(self, client, tmp_vault):
        token = self._setup_and_unlock(client, tmp_vault)
        h = self._auth(token)
        job_id = self._create_job_with_deadline(client, h, "Software Engineer")

        r = client.get(f"/api/v1/jobs/{job_id}/calendar", headers=h)
        assert r.status_code == 200
        assert "text/calendar" in r.headers["content-type"]
        content = r.content.decode()
        assert "BEGIN:VCALENDAR" in content
        assert "END:VCALENDAR" in content
        assert "BEGIN:VEVENT" in content
        assert "END:VEVENT" in content

    def test_job_calendar_summary_includes_title_and_org(self, client, tmp_vault):
        token = self._setup_and_unlock(client, tmp_vault)
        h = self._auth(token)
        job_id = self._create_job_with_deadline(client, h, "ML Engineer")

        r = client.get(f"/api/v1/jobs/{job_id}/calendar", headers=h)
        content = r.content.decode()
        assert "ML Engineer" in content
        assert "Test Corp" in content

    def test_job_calendar_contains_deadline_date(self, client, tmp_vault):
        token = self._setup_and_unlock(client, tmp_vault)
        h = self._auth(token)
        job_id = self._create_job_with_deadline(client, h, deadline="2026-09-15")

        r = client.get(f"/api/v1/jobs/{job_id}/calendar", headers=h)
        content = r.content.decode()
        # iCalendar date format is YYYYMMDD
        assert "20260915" in content

    def test_job_calendar_has_three_reminders(self, client, tmp_vault):
        token = self._setup_and_unlock(client, tmp_vault)
        h = self._auth(token)
        job_id = self._create_job_with_deadline(client, h)

        r = client.get(f"/api/v1/jobs/{job_id}/calendar", headers=h)
        content = r.content.decode()
        # Three VALARM components: 7 days, 2 days, and morning of deadline
        assert content.count("BEGIN:VALARM") == 3
        assert content.count("END:VALARM") == 3
        assert content.count("ACTION:DISPLAY") == 3

    def test_job_calendar_without_deadline_returns_400(self, client, tmp_vault):
        token = self._setup_and_unlock(client, tmp_vault)
        h = self._auth(token)
        job_r = client.post("/api/v1/jobs", json={"title": "No Deadline Job"}, headers=h)
        job_id = job_r.json()["id"]

        r = client.get(f"/api/v1/jobs/{job_id}/calendar", headers=h)
        assert r.status_code == 400

    def test_job_calendar_not_found_returns_404(self, client, tmp_vault):
        token = self._setup_and_unlock(client, tmp_vault)
        h = self._auth(token)

        r = client.get("/api/v1/jobs/nonexistent-id/calendar", headers=h)
        assert r.status_code == 404

    def test_all_deadlines_returns_ics(self, client, tmp_vault):
        token = self._setup_and_unlock(client, tmp_vault)
        h = self._auth(token)
        self._create_job_with_deadline(client, h, "Job A", "2026-09-01")
        self._create_job_with_deadline(client, h, "Job B", "2026-10-01")

        r = client.get("/api/v1/calendar/deadlines", headers=h)
        assert r.status_code == 200
        assert "text/calendar" in r.headers["content-type"]
        content = r.content.decode()
        assert "BEGIN:VCALENDAR" in content
        # Both jobs should have VEVENTs
        assert content.count("BEGIN:VEVENT") == 2

    def test_all_deadlines_excludes_rejected_jobs(self, client, tmp_vault):
        token = self._setup_and_unlock(client, tmp_vault)
        h = self._auth(token)
        job_id = self._create_job_with_deadline(client, h, "Rejected Job")
        # Move job to REJECTED status
        client.post(f"/api/v1/jobs/{job_id}/events", json={"event_type": "REJECTED"}, headers=h)

        r = client.get("/api/v1/calendar/deadlines", headers=h)
        # No active jobs with deadlines remain
        assert r.status_code == 404

    def test_all_deadlines_excludes_withdrawn_jobs(self, client, tmp_vault):
        token = self._setup_and_unlock(client, tmp_vault)
        h = self._auth(token)
        job_id = self._create_job_with_deadline(client, h, "Withdrawn Job")
        client.post(f"/api/v1/jobs/{job_id}/events", json={"event_type": "WITHDRAWN"}, headers=h)

        r = client.get("/api/v1/calendar/deadlines", headers=h)
        assert r.status_code == 404

    def test_all_deadlines_no_jobs_returns_404(self, client, tmp_vault):
        token = self._setup_and_unlock(client, tmp_vault)
        h = self._auth(token)
        # No jobs created at all
        r = client.get("/api/v1/calendar/deadlines", headers=h)
        assert r.status_code == 404

    def test_calendar_requires_auth(self, client, tmp_vault):
        token = self._setup_and_unlock(client, tmp_vault)
        h = self._auth(token)
        job_id = self._create_job_with_deadline(client, h)

        r = client.get(f"/api/v1/jobs/{job_id}/calendar", headers={"Authorization": "Bearer invalid_token"})
        assert r.status_code == 401

    def test_ics_content_disposition_header(self, client, tmp_vault):
        token = self._setup_and_unlock(client, tmp_vault)
        h = self._auth(token)
        job_id = self._create_job_with_deadline(client, h)

        r = client.get(f"/api/v1/jobs/{job_id}/calendar", headers=h)
        assert "content-disposition" in r.headers
        assert ".ics" in r.headers["content-disposition"]
