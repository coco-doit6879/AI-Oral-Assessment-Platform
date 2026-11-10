import time

from sqlalchemy import select
from test_examination import approve_and_schedule, import_roster, setup_workflow
from test_mvp import ok

from app.models import Assignment, Exam, ExamSession, User


def test_published_roster_manual_excel_and_schedule_preserve_existing(env):
    clients, factory, key, _ = setup_workflow(env)
    office = clients["reviewer"]
    ok(import_roster(office, key))
    approve_and_schedule(clients, key)
    sitting = ok(clients["student"].post("/exam-sessions", json={"exam_id": key}))
    before = ok(office.get(f"/admin/exams/{key}/roster"))[0]
    with factory() as db:
        snapshot = db.get(Exam, key).snapshot
    body = {"student_number": "NEW01", "email": "NEW@example.edu.vn", "name": "New learner", "password": ""}
    endpoint = f"/admin/exams/{key}/students"
    assert clients["teacher"].post(endpoint, json=body).status_code == 403
    assert clients["student"].post(endpoint, json=body).status_code == 403
    added = ok(office.post(endpoint, json=body))
    assert added == {"rows": 1, "added": 1, "accounts_created": 1}
    assert ok(office.post(endpoint, json=body))["added"] == 0
    assert office.post(endpoint, json=body | {"email": "bad"}).status_code == 422
    assert office.post(endpoint, json=body | {"password": "short"}).status_code == 422
    assert office.post(endpoint, json=body | {"email": "other@example.edu.vn"}).status_code == 422
    ok(import_roster(office, key, [["NEW02", "excel@example.edu.vn", "Excel learner", ""]]))
    rows = ok(office.get(f"/admin/exams/{key}/roster"))
    original = next(row for row in rows if row["student_id"] == before["student_id"])
    assert original == before
    assert original["sessions"][0]["id"] == sitting["id"]
    new = next(row for row in rows if row["email"] == "new@example.edu.vn")
    assert new["opens_at"] is None and new["sessions"] == []
    schedule = {"student_ids": [new["student_id"]], "opens_at": time.time() + 60, "closes_at": time.time() + 3600}
    ok(office.put(f"/admin/exams/{key}/schedule", json=schedule))
    schedule["student_ids"].append(before["student_id"])
    assert office.put(f"/admin/exams/{key}/schedule", json=schedule).status_code == 409
    with factory() as db:
        assert db.get(Exam, key).snapshot == snapshot
        assert db.get(Exam, key).status == "PUBLISHED"
        assert db.scalar(select(User).where(User.email == "other@example.edu.vn")) is None
        assignment = db.scalar(select(Assignment).where(
            Assignment.exam_id == key, Assignment.student_id == before["student_id"],
        ))
        assert assignment.opens_at == before["opens_at"]


def test_roster_results_hide_deleted_sessions_and_respect_permissions(env):
    clients, factory, key, _ = setup_workflow(env)
    ok(import_roster(clients["reviewer"], key))
    approve_and_schedule(clients, key)
    sitting = ok(clients["student"].post("/exam-sessions", json={"exam_id": key}))
    endpoint = f"/admin/exams/{key}/roster"
    with factory() as db:
        session = db.get(ExamSession, sitting["id"])
        session.status, session.final_score = "COMPLETED", 8
        db.commit()
    row = ok(clients["teacher"].get(endpoint))[0]
    assert row["sessions"][0]["final_score"] == 8
    assert clients["outsider"].get(endpoint).status_code == 403
    with factory() as db:
        db.get(ExamSession, sitting["id"]).deleted_at = time.time()
        db.commit()
    assert ok(clients["admin"].get(endpoint))[0]["sessions"] == []


def test_exam_list_counts_participants_and_real_non_deleted_sittings(env):
    clients, factory, key, _ = setup_workflow(env)
    ok(import_roster(clients["reviewer"], key))
    approve_and_schedule(clients, key)
    sitting = ok(clients["student"].post("/exam-sessions", json={"exam_id": key}))

    def counts():
        return next(row for row in ok(clients["teacher"].get("/admin/examination/exams")) if row["id"] == key)

    assert counts()["participant_count"] == 1
    assert counts()["sitting_count"] == 0  # Device check isn't an exam sitting yet.
    with factory() as db:
        row = db.get(ExamSession, sitting["id"])
        row.status = "COMPLETED"
        db.add(ExamSession(exam_id=key, student_id=row.student_id, status="IN_PROGRESS", attempt_number=2))
        db.commit()
    assert counts()["sitting_count"] == 2
    assert len(ok(clients["teacher"].get(f"/admin/exams/{key}/roster"))[0]["sessions"]) == 2
    with factory() as db:
        db.get(ExamSession, sitting["id"]).deleted_at = time.time()
        db.commit()
    assert counts()["sitting_count"] == 1
    assert clients["student"].get("/admin/examination/exams").status_code == 403
