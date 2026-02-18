import io


class TestDocuments:
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

    def test_upload_document(self, client, tmp_vault):
        token = self._setup_and_unlock(client, tmp_vault)
        job_id = self._create_job(client, token)

        r = client.post(
            f"/api/v1/jobs/{job_id}/documents",
            files={"file": ("resume.pdf", b"fake pdf content", "application/pdf")},
            data={"doc_type": "cv", "version_label": "v1"},
            headers=self._auth(token),
        )
        assert r.status_code == 201
        data = r.json()
        assert data["doc_type"] == "cv"
        assert data["original_filename"] == "resume.pdf"
        assert len(data["file_hash"]) == 64  # SHA-256 hex

    def test_duplicate_document_rejected(self, client, tmp_vault):
        token = self._setup_and_unlock(client, tmp_vault)
        job_id = self._create_job(client, token)
        h = self._auth(token)

        content = b"identical content"
        client.post(
            f"/api/v1/jobs/{job_id}/documents",
            files={"file": ("resume.pdf", content, "application/pdf")},
            data={"doc_type": "cv"},
            headers=h,
        )
        r = client.post(
            f"/api/v1/jobs/{job_id}/documents",
            files={"file": ("resume_v2.pdf", content, "application/pdf")},
            data={"doc_type": "cv"},
            headers=h,
        )
        assert r.status_code == 409

    def test_list_documents(self, client, tmp_vault):
        token = self._setup_and_unlock(client, tmp_vault)
        job_id = self._create_job(client, token)
        h = self._auth(token)

        client.post(
            f"/api/v1/jobs/{job_id}/documents",
            files={"file": ("resume.pdf", b"content 1", "application/pdf")},
            data={"doc_type": "cv"},
            headers=h,
        )
        client.post(
            f"/api/v1/jobs/{job_id}/documents",
            files={"file": ("cover.pdf", b"content 2", "application/pdf")},
            data={"doc_type": "cover_letter"},
            headers=h,
        )

        r = client.get(f"/api/v1/jobs/{job_id}/documents", headers=h)
        assert r.status_code == 200
        assert len(r.json()) == 2

    def test_download_document(self, client, tmp_vault):
        token = self._setup_and_unlock(client, tmp_vault)
        job_id = self._create_job(client, token)
        h = self._auth(token)

        original_content = b"my resume content here"
        upload_r = client.post(
            f"/api/v1/jobs/{job_id}/documents",
            files={"file": ("resume.pdf", original_content, "application/pdf")},
            data={"doc_type": "cv"},
            headers=h,
        )
        doc_id = upload_r.json()["id"]

        r = client.get(f"/api/v1/jobs/{job_id}/documents/{doc_id}/download", headers=h)
        assert r.status_code == 200
        assert r.content == original_content

    # --- P1: Submitted document linking ---

    def test_document_initially_not_submitted(self, client, tmp_vault):
        token = self._setup_and_unlock(client, tmp_vault)
        job_id = self._create_job(client, token)
        h = self._auth(token)

        r = client.post(
            f"/api/v1/jobs/{job_id}/documents",
            files={"file": ("cv.pdf", b"cv content", "application/pdf")},
            data={"doc_type": "cv"},
            headers=h,
        )
        assert r.json()["submitted_at"] is None

    def test_mark_document_submitted(self, client, tmp_vault):
        token = self._setup_and_unlock(client, tmp_vault)
        job_id = self._create_job(client, token)
        h = self._auth(token)

        upload_r = client.post(
            f"/api/v1/jobs/{job_id}/documents",
            files={"file": ("cv.pdf", b"cv content", "application/pdf")},
            data={"doc_type": "cv"},
            headers=h,
        )
        doc_id = upload_r.json()["id"]

        r = client.put(f"/api/v1/jobs/{job_id}/documents/{doc_id}/submit", headers=h)
        assert r.status_code == 200
        assert r.json()["submitted_at"] is not None

    def test_unmark_document_submitted(self, client, tmp_vault):
        token = self._setup_and_unlock(client, tmp_vault)
        job_id = self._create_job(client, token)
        h = self._auth(token)

        upload_r = client.post(
            f"/api/v1/jobs/{job_id}/documents",
            files={"file": ("cv.pdf", b"cv content", "application/pdf")},
            data={"doc_type": "cv"},
            headers=h,
        )
        doc_id = upload_r.json()["id"]

        client.put(f"/api/v1/jobs/{job_id}/documents/{doc_id}/submit", headers=h)
        r = client.delete(f"/api/v1/jobs/{job_id}/documents/{doc_id}/submit", headers=h)
        assert r.status_code == 200
        assert r.json()["submitted_at"] is None

    def test_verify_document_intact(self, client, tmp_vault):
        token = self._setup_and_unlock(client, tmp_vault)
        job_id = self._create_job(client, token)
        h = self._auth(token)

        upload_r = client.post(
            f"/api/v1/jobs/{job_id}/documents",
            files={"file": ("cv.pdf", b"cv content", "application/pdf")},
            data={"doc_type": "cv"},
            headers=h,
        )
        doc_id = upload_r.json()["id"]

        r = client.get(f"/api/v1/jobs/{job_id}/documents/{doc_id}/verify", headers=h)
        assert r.status_code == 200
        assert r.json()["verified"] is True

    # --- P4: CV-to-job keyword match score ---

    def test_match_with_capture_returns_score(self, client, tmp_vault):
        token = self._setup_and_unlock(client, tmp_vault)
        h = self._auth(token)
        job_r = client.post("/api/v1/jobs", json={"title": "Python Developer"}, headers=h)
        job_id = job_r.json()["id"]

        # Add a capture with job description keywords
        client.post(f"/api/v1/jobs/{job_id}/captures", json={
            "text_snapshot": "python django postgresql kubernetes devops agile scrum",
            "capture_method": "manual_paste",
        }, headers=h)

        # Upload a "CV" with overlapping keywords
        cv_content = b"python developer django experience kubernetes deployment agile"
        upload_r = client.post(
            f"/api/v1/jobs/{job_id}/documents",
            files={"file": ("cv.txt", cv_content, "text/plain")},
            data={"doc_type": "cv"},
            headers=h,
        )
        doc_id = upload_r.json()["id"]

        r = client.get(f"/api/v1/jobs/{job_id}/documents/{doc_id}/match", headers=h)
        assert r.status_code == 200
        data = r.json()
        assert "score" in data
        assert "matched" in data
        assert "missing" in data
        assert data["score"] > 0

    def test_match_with_no_captures_returns_zero(self, client, tmp_vault):
        token = self._setup_and_unlock(client, tmp_vault)
        h = self._auth(token)
        job_r = client.post("/api/v1/jobs", json={"title": "Empty Job"}, headers=h)
        job_id = job_r.json()["id"]

        upload_r = client.post(
            f"/api/v1/jobs/{job_id}/documents",
            files={"file": ("cv.txt", b"python developer", "text/plain")},
            data={"doc_type": "cv"},
            headers=h,
        )
        doc_id = upload_r.json()["id"]

        r = client.get(f"/api/v1/jobs/{job_id}/documents/{doc_id}/match", headers=h)
        assert r.status_code == 200
        assert r.json()["score"] == 0
