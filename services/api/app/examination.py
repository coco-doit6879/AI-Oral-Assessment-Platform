"""Examination office workflow; generation, approval, scheduling and roster operations."""
import secrets
import time

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import ai
from .db import get_db
from .exam_generation import build_snapshot
from .examination_schemas import (
    CommissionIn,
    DraftReviewIn,
    HotwordsIn,
    ManualGradeIn,
    ManualStudentIn,
    RosterSelectionIn,
    ScheduleIn,
    TeacherIn,
)
from .excel import parse_roster, template_bytes, workbook_bytes
from .models import (
    Assignment,
    Attempt,
    Audit,
    ClassStudent,
    Course,
    CourseEnrollment,
    Exam,
    ExamSession,
    ProcessingJob,
    ReviewJob,
    Rubric,
    TeachingClass,
    User,
    uid,
)
from .permissions import has_role, role_filter, teacher_scope
from .runtime_settings import settings
from .schemas import ReviewIn, RubricIn
from .security import (
    by_id,
    course_access,
    current_user,
    editor,
    exam_access,
    exam_officer,
    fail,
    hasher,
    staff,
    visible_exams,
)

router = APIRouter()
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def audit(db, user, event, **details):
    db.add(Audit(user_id=user.id, event=event, details=details))


def scoped_exam(db, key, user):
    exam = by_id(db, Exam, key, lock=True)
    exam_access(db, exam, user)
    return exam


def schedule_for(db, exam, student_id):
    return db.scalar(select(Assignment).where(Assignment.exam_id == exam.id, Assignment.student_id == student_id))


def check_schedule(db, exam, user):
    if not exam.workflow:
        return
    row = schedule_for(db, exam, user.id)
    if not has_role(user, "STUDENT") or not row:
        fail(403, "NOT_ASSIGNED", "Bạn không có tên trong danh sách kỳ thi")
    now = time.time()
    if exam.status != "PUBLISHED" or row.opens_at is None or row.closes_at is None or not row.opens_at <= now < row.closes_at:
        fail(409, "OUTSIDE_SCHEDULE", "Chưa đến giờ thi hoặc đã hết thời gian vào thi")


@router.post("/auth/request-exam-officer")
def request_role(db: Session = Depends(get_db), user=Depends(current_user)):
    if not has_role(user, "STUDENT") or has_role(user, "EXAM_OFFICER"):
        fail(409, "INVALID_ROLE", "Chỉ sinh viên chưa có quyền khảo thí gửi yêu cầu bổ sung vai trò")
    user.requested_role = "EXAM_OFFICER"
    audit(db, user, "EXAM_OFFICER_REQUESTED")
    db.commit()
    return {"status": "PENDING", "message": "Đã gửi yêu cầu cho admin duyệt"}


@router.get("/admin/examination/teachers")
def teachers(db: Session = Depends(get_db), user=Depends(exam_officer)):
    return [{"id": u.id, "name": u.name, "email": u.email} for u in db.scalars(
        select(User).where(role_filter("TEACHER"), User.status == "ACTIVE").order_by(User.name)
    )]


def assign_teacher(db, course, teacher_id):
    teacher = by_id(db, User, teacher_id)
    if not has_role(teacher, "TEACHER") or teacher.status != "ACTIVE":
        fail(422, "NOT_TEACHER", "Chọn giảng viên đang hoạt động do admin phân quyền")
    course.owner_id = teacher.id


@router.put("/admin/courses/{key}/teacher")
def teacher_assignment(key: str, body: TeacherIn, db: Session = Depends(get_db), user=Depends(exam_officer)):
    course = by_id(db, Course, key, lock=True)
    before = course.owner_id
    assign_teacher(db, course, body.teacher_id)
    audit(db, user, "COURSE_TEACHER_ASSIGNED", course_id=key, before=before, teacher_id=body.teacher_id)
    db.commit()
    return {"ok": True}


@router.get("/admin/courses/{key}/hotwords")
def course_hotwords(key: str, db: Session = Depends(get_db), user=Depends(staff)):
    return {"hotwords": course_access(db, key, user).hotwords}


@router.put("/admin/courses/{key}/hotwords")
def save_hotwords(key: str, body: HotwordsIn, db: Session = Depends(get_db), user=Depends(editor)):
    course = course_access(db, key, user)
    course.hotwords = body.hotwords
    audit(db, user, "COURSE_HOTWORDS_UPDATED", course_id=key, count=len(body.hotwords))
    db.commit()
    return body.model_dump()


@router.get("/admin/examination/exams")
def exam_list(db: Session = Depends(get_db), user=Depends(staff)):
    query = select(Exam, Course).join(Course).where(Exam.workflow.is_(True), Exam.class_id.is_(None))
    if teacher_scope(user):
        query = query.where(visible_exams(user))
    rows = db.execute(query.order_by(Exam.created_at.desc())).all()
    ids = [e.id for e, _ in rows]
    participants = dict(db.execute(select(Assignment.exam_id, func.count(Assignment.id)).where(
        Assignment.exam_id.in_(ids)).group_by(Assignment.exam_id)).all())
    sittings = dict(db.execute(select(ExamSession.exam_id, func.count(ExamSession.id)).where(
        ExamSession.exam_id.in_(ids), ExamSession.deleted_at.is_(None),
        ExamSession.status != "DEVICE_CHECK").group_by(ExamSession.exam_id)).all())
    return [{"id": e.id, "name": e.name, "status": e.status, "course_id": c.id,
             "course_name": c.name, "teacher_id": c.owner_id, "imported": bool(e.imported_questions), "time_limit": e.time_limit,
             "participant_count": participants.get(e.id, 0), "sitting_count": sittings.get(e.id, 0)}
            for e, c in rows]


@router.post("/admin/examination/exams", status_code=201)
def commission(body: CommissionIn, db: Session = Depends(get_db), user=Depends(exam_officer)):
    course = by_id(db, Course, body.course_id, lock=True)
    if course.status != "ACTIVE":
        fail(409, "ARCHIVED", "Môn học đã lưu trữ")
    assign_teacher(db, course, body.teacher_id)
    rubric = Rubric(course_id=course.id, name=f"Rubric — {body.name}"[:200], criteria=[
        {"name": "Kiến thức", "description": "Cần giảng viên cấu hình hoặc sinh rubric trước khi duyệt", "max_score": 10, "weight": 1}
    ])
    db.add(rubric)
    db.flush()
    exam = Exam(course_id=course.id, rubric_id=rubric.id, name=body.name, time_limit=body.time_limit,
                blueprint=[], workflow=True)
    db.add(exam)
    db.flush()
    audit(db, user, "EXAM_COMMISSIONED", exam_id=exam.id, teacher_id=body.teacher_id)
    db.commit()
    return {"id": exam.id, "status": exam.status}


@router.get("/admin/examination/template.xlsx")
def template(user=Depends(exam_officer)):
    return Response(template_bytes(), media_type=XLSX, headers={"Content-Disposition": 'attachment; filename="students-template.xlsx"'})


@router.get("/admin/exams/{key}/roster")
def roster(key: str, db: Session = Depends(get_db), user=Depends(staff)):
    scoped_exam(db, key, user)
    sessions = {}
    for sitting in db.scalars(select(ExamSession).where(
        ExamSession.exam_id == key, ExamSession.deleted_at.is_(None),
    ).order_by(ExamSession.created_at.desc(), ExamSession.id)):
        sessions.setdefault(sitting.student_id, []).append({
            "id": sitting.id, "status": sitting.status, "attempt_number": sitting.attempt_number,
            "created_at": sitting.created_at, "final_score": sitting.final_score,
        })
    return [{"student_id": u.id, "student_number": a.student_number, "name": u.name, "email": u.email,
             "opens_at": a.opens_at, "closes_at": a.closes_at, "sessions": sessions.get(u.id, [])}
            for a, u in db.execute(select(Assignment, User).join(User).where(Assignment.exam_id == key).order_by(User.name))]


@router.get("/admin/courses/{course_id}/classes")
def course_classes(course_id: str, db: Session = Depends(get_db), user=Depends(staff)):
    course_access(db, course_id, user)
    return [{"id": c.id, "name": c.name, "student_count": count} for c, count in db.execute(
        select(TeachingClass, func.count(ClassStudent.id)).outerjoin(
            ClassStudent, ClassStudent.class_id == TeachingClass.id
        ).where(TeachingClass.course_id == course_id).group_by(TeachingClass.id).order_by(TeachingClass.name)
    )]


def roster_source(db, course_id, class_id, user):
    course_access(db, course_id, user)
    enrolled = select(CourseEnrollment.student_id).where(CourseEnrollment.course_id == course_id)
    members = select(ClassStudent.student_id).join(TeachingClass).where(TeachingClass.course_id == course_id)
    query = select(User).where(User.id.in_(enrolled.union(members)), role_filter("STUDENT", include_admin=False), User.status == "ACTIVE")
    if class_id:
        section = by_id(db, TeachingClass, class_id)
        if section.course_id != course_id:
            fail(422, "CLASS_COURSE", "Lớp không thuộc môn đã chọn")
        query = query.where(User.id.in_(select(ClassStudent.student_id).where(ClassStudent.class_id == class_id)))
    return query


@router.get("/admin/exams/{key}/roster-candidates")
def roster_candidates(key: str, course_id: str, class_id: str | None = None,
                      db: Session = Depends(get_db), user=Depends(exam_officer)):
    scoped_exam(db, key, user)
    assigned = set(db.scalars(select(Assignment.student_id).where(Assignment.exam_id == key)))
    return [{"id": u.id, "name": u.name, "username": u.username, "email": u.email,
             "assigned": u.id in assigned} for u in db.scalars(
        roster_source(db, course_id, class_id, user).order_by(User.name, User.id)
    )]


@router.post("/admin/exams/{key}/select-students")
def select_students(key: str, body: RosterSelectionIn, db: Session = Depends(get_db), user=Depends(exam_officer)):
    exam = scoped_exam(db, key, user)
    if not exam.workflow:
        fail(409, "ROSTER_LOCKED", "Chỉ thêm danh sách cho kỳ thi điều phối")
    ids = set(body.student_ids)
    learners = db.scalars(roster_source(db, body.course_id, body.class_id, user).where(User.id.in_(ids))).all()
    if len(learners) != len(ids):
        fail(422, "INVALID_ROSTER_SOURCE", "Học viên phải đang hoạt động và thuộc môn/lớp đã chọn")
    existing = set(db.scalars(select(Assignment.student_id).where(Assignment.exam_id == key)))
    for learner in learners:
        if learner.id not in existing:
            db.add(Assignment(exam_id=key, student_id=learner.id))
    added = len(ids - existing)
    audit(db, user, "EXAM_ROSTER_SELECTED", exam_id=key, course_id=body.course_id,
          class_id=body.class_id, student_ids=sorted(ids), added=added)
    db.commit()
    return {"added": added, "skipped": len(ids) - added}


@router.post("/admin/exams/{key}/import-students")
def import_students(key: str, file: UploadFile = File(), db: Session = Depends(get_db), user=Depends(exam_officer)):
    exam = scoped_exam(db, key, user)
    if not exam.workflow:
        fail(409, "ROSTER_LOCKED", "Chỉ nhập danh sách cho kỳ thi điều phối")
    raw = file.file.read(2 * 1024 * 1024 + 1)
    if len(raw) > 2 * 1024 * 1024:
        fail(413, "EXCEL_SIZE", "File Excel tối đa 2 MB")
    if not (file.filename or "").lower().endswith(".xlsx"):
        fail(422, "EXCEL_TYPE", "Chọn file .xlsx theo mẫu")
    rows = parse_roster(raw)
    return add_roster_rows(db, exam, rows, user, "EXAM_ROSTER_IMPORTED")


@router.post("/admin/exams/{key}/students")
def manual_student(key: str, body: ManualStudentIn, db: Session = Depends(get_db), user=Depends(exam_officer)):
    exam = scoped_exam(db, key, user)
    if not exam.workflow:
        fail(409, "ROSTER_LOCKED", "Chỉ thêm danh sách cho kỳ thi điều phối")
    return add_roster_rows(db, exam, [body.model_dump()], user, "EXAM_ROSTER_MANUAL")


def add_roster_rows(db, exam, rows, user, event):
    key = exam.id
    created, added = 0, 0
    for row in rows:
        matches = db.scalars(select(User).where(func.lower(User.email) == row["email"])).all()
        if len(matches) > 1 or (matches and (not has_role(matches[0], "STUDENT") or matches[0].status != "ACTIVE")):
            fail(422, "EMAIL_CONFLICT", f"Email {row['email']} không thuộc duy nhất một sinh viên hoạt động")
        learner = matches[0] if matches else None
        if not learner:
            learner = User(username=f"sv-{uid()}", email=row["email"], name=row["name"], role="STUDENT",
                           password_hash=hasher.hash(row["password"] or secrets.token_urlsafe(32)))
            db.add(learner)
            db.flush()
            created += 1
        existing = schedule_for(db, exam, learner.id)
        duplicate = db.scalar(select(Assignment).where(Assignment.exam_id == key,
            Assignment.student_number == row["student_number"], Assignment.student_id != learner.id))
        if duplicate or (existing and existing.student_number and existing.student_number != row["student_number"]):
            fail(422, "STUDENT_NUMBER_CONFLICT", f"MSSV {row['student_number']} không khớp danh sách đã nhập")
        if not existing:
            db.add(Assignment(exam_id=key, student_id=learner.id, student_number=row["student_number"]))
            added += 1
        else:
            existing.student_number = row["student_number"]
    audit(db, user, event, exam_id=key, added=added, created=created)
    db.commit()
    return {"rows": len(rows), "added": added, "accounts_created": created}


@router.get("/admin/exams/{key}/draft")
def draft(key: str, db: Session = Depends(get_db), user=Depends(staff)):
    exam = scoped_exam(db, key, user)
    return {"id": exam.id, "status": exam.status, "snapshot": exam.snapshot}


@router.post("/admin/exams/{key}/generate")
def generate(key: str, db: Session = Depends(get_db), user=Depends(editor)):
    exam = scoped_exam(db, key, user)
    if exam.status not in {"DRAFT", "GENERATED"}:
        fail(409, "DRAFT_REQUIRED", "Trả về bản nháp trước khi sinh lại đề")
    if not exam.blueprint:
        fail(422, "BLUEPRINT_REQUIRED", "Cấu hình chủ đề, số câu và độ khó trong Ngân hàng đề thi")
    snapshot = build_snapshot(db, exam)
    if exam.imported_questions:
        criteria = snapshot["criteria"]
    elif settings().ai_provider == "demo":
        criteria = [
            {"name": "Kiến thức chính xác", "description": "Giải thích đúng các khái niệm và bám tài liệu môn học", "max_score": 10, "weight": 6},
            {"name": "Lập luận và ví dụ", "description": "Lập luận rõ ràng, ví dụ phù hợp với câu hỏi", "max_score": 10, "weight": 4},
        ]
    else:
        criteria = ai.structured(
            "Draft an assessment rubric appropriate to the supplied questions and expected concepts. "
            "Define observable criteria with bounded scores and weights; teacher approval is required.",
            {"questions": snapshot["questions"]}, RubricIn,
        ).model_dump()["criteria"]
    snapshot["criteria"] = criteria
    snapshot.pop("published_at", None)
    snapshot["generated_at"] = time.time()
    exam.snapshot, exam.status, exam.workflow = snapshot, "GENERATED", True
    audit(db, user, "EXAM_DRAFT_GENERATED", exam_id=key)
    db.commit()
    return {"status": exam.status, "snapshot": exam.snapshot}


@router.put("/admin/exams/{key}/draft")
def edit_draft(key: str, body: DraftReviewIn, db: Session = Depends(get_db), user=Depends(staff)):
    exam = scoped_exam(db, key, user)
    if exam.status != "GENERATED" or not exam.snapshot:
        fail(409, "DRAFT_REQUIRED", "Chỉ sửa nội dung đề đã sinh và chưa duyệt")
    original = exam.snapshot["questions"]
    if len(body.questions) != len(original):
        fail(422, "QUESTION_COUNT", "Số câu phải khớp blueprint; trả về bản nháp để cấu hình lại")
    questions = []
    for old, question in zip(original, body.questions):
        allowed = set(exam.snapshot["topic_chunk_ids"].get(old["topic_id"], []))
        if not set(question.reference_chunk_ids) <= allowed:
            fail(422, "INVALID_EVIDENCE", "Nguồn tham chiếu phải thuộc phạm vi tài liệu của câu hỏi")
        questions.append(old | question.model_dump())
    exam.snapshot = exam.snapshot | {"questions": questions, "criteria": [c.model_dump() for c in body.criteria]}
    audit(db, user, "EXAM_DRAFT_EDITED", exam_id=key)
    db.commit()
    return {"status": exam.status}


@router.post("/admin/exams/{key}/teacher-approve")
def teacher_approve(key: str, db: Session = Depends(get_db), user=Depends(editor)):
    exam = scoped_exam(db, key, user)
    if exam.status != "GENERATED":
        fail(409, "DRAFT_REQUIRED", "Sinh và kiểm tra câu hỏi/rubric trước khi duyệt")
    exam.snapshot = exam.snapshot | {"teacher_approved_by": user.id, "teacher_approved_at": time.time()}
    exam.status = "TEACHER_APPROVED"
    audit(db, user, "EXAM_TEACHER_APPROVED", exam_id=key)
    db.commit()
    return {"status": exam.status}


@router.post("/admin/exams/{key}/return-draft")
def return_draft(key: str, body: ReviewIn, db: Session = Depends(get_db), user=Depends(staff)):
    exam = scoped_exam(db, key, user)
    if exam.status not in {"GENERATED", "TEACHER_APPROVED"}:
        fail(409, "INVALID_STATE", "Không thể trả đề về bản nháp")
    exam.status, exam.snapshot = "DRAFT", None
    audit(db, user, "EXAM_RETURNED", exam_id=key, reason=body.reason)
    db.commit()
    return {"status": exam.status}


@router.put("/admin/exams/{key}/schedule")
def schedule(key: str, body: ScheduleIn, db: Session = Depends(get_db), user=Depends(exam_officer)):
    exam = scoped_exam(db, key, user)
    if exam.status not in {"TEACHER_APPROVED", "PUBLISHED"}:
        fail(409, "APPROVAL_REQUIRED", "Xếp lịch sau khi giảng viên duyệt đề")
    if body.closes_at - body.opens_at < exam.time_limit or body.closes_at <= time.time():
        fail(422, "SCHEDULE_LENGTH", "Khoảng thi phải đủ thời lượng bài thi và chưa kết thúc")
    ids = set(body.student_ids)
    rows = db.scalars(select(Assignment).where(Assignment.exam_id == key, Assignment.student_id.in_(ids))).all()
    if len(rows) != len(ids):
        fail(422, "NOT_ASSIGNED", "Sinh viên chưa có trong danh sách kỳ thi")
    if db.scalar(select(ExamSession.id).where(
        ExamSession.exam_id == key, ExamSession.student_id.in_(ids), ExamSession.deleted_at.is_(None),
    ).limit(1)):
        fail(409, "SCHEDULE_LOCKED", "Không đổi lịch sinh viên đã tạo phiên thi; chỉ chọn sinh viên chưa thi")
    for row in rows:
        row.opens_at, row.closes_at = body.opens_at, body.closes_at
    audit(db, user, "EXAM_SCHEDULED", exam_id=key, student_ids=sorted(ids), opens_at=body.opens_at, closes_at=body.closes_at)
    db.commit()
    return {"updated": len(rows)}


@router.post("/admin/exams/{key}/office-approve")
def office_approve(key: str, db: Session = Depends(get_db), user=Depends(exam_officer)):
    exam = scoped_exam(db, key, user)
    if exam.status != "TEACHER_APPROVED":
        fail(409, "APPROVAL_REQUIRED", "Giảng viên phải duyệt đề trước")
    rows = db.scalars(select(Assignment).where(Assignment.exam_id == key)).all()
    if not rows or any(a.opens_at is None or a.closes_at is None or a.closes_at <= time.time()
                       or a.closes_at - a.opens_at < exam.time_limit for a in rows):
        fail(409, "SCHEDULE_REQUIRED", "Nhập danh sách và xếp lịch hợp lệ cho tất cả sinh viên trước khi mở thi")
    exam.snapshot = exam.snapshot | {"office_approved_by": user.id, "published_at": time.time()}
    exam.status = "PUBLISHED"
    audit(db, user, "EXAM_OFFICE_APPROVED", exam_id=key)
    db.commit()
    return {"status": exam.status}


@router.post("/admin/results/{key}/manual-grade")
def manual_grade(key: str, body: ManualGradeIn, db: Session = Depends(get_db), user=Depends(editor)):
    session = by_id(db, ExamSession, key, lock=True)
    exam = by_id(db, Exam, session.exam_id)
    exam_access(db, exam, user)
    if session.deleted_at is not None or session.status not in {"REVIEW_REQUIRED", "COMPLETED"}:
        fail(409, "NOT_READY", "Chờ máy chủ chấm xong trước khi chấm lại")
    if db.scalar(select(ProcessingJob.id).join(Attempt).where(Attempt.session_id == key,
        ProcessingJob.status.not_in(["COMPLETED", "FAILED"]))):
        fail(409, "PROCESSING_PENDING", "Chờ hoàn tất hàng đợi STT và chấm điểm")
    if db.scalar(select(ReviewJob.id).join(Attempt).where(Attempt.session_id == key, ReviewJob.status == "PENDING")):
        fail(409, "REVIEW_PENDING", "Đang chạy nhận dạng/chấm lại AI; chờ hoàn tất")
    before = {"final_score": session.final_score, "manual_review": session.manual_review}
    session.manual_review = {"score": body.score, "reason": body.reason, "reviewed_by": user.id, "reviewed_at": time.time()}
    session.final_score, session.status = body.score, "COMPLETED"
    audit(db, user, "MANUAL_GRADE", session_id=key, before=before, after=session.manual_review)
    db.commit()
    return {"status": session.status, "final_score": session.final_score}


@router.get("/admin/exams/{key}/grades.xlsx")
def export_grades(key: str, db: Session = Depends(get_db), user=Depends(exam_officer)):
    scoped_exam(db, key, user)
    rows = []
    for assignment, learner in db.execute(select(Assignment, User).join(User).where(Assignment.exam_id == key).order_by(User.name)):
        sessions = db.scalars(select(ExamSession).where(ExamSession.exam_id == key, ExamSession.student_id == learner.id,
            ExamSession.deleted_at.is_(None)).order_by(ExamSession.attempt_number)).all()
        for session in sessions or [None]:
            rows.append([assignment.student_number, learner.email, learner.name,
                         session.attempt_number if session else None,
                         session.status if session else "NOT_STARTED",
                         session.ai_score if session else None,
                         session.final_score if session and session.status == "COMPLETED" else None,
                         (session.manual_review or {}).get("reason") if session else None])
    audit(db, user, "GRADES_EXPORTED", exam_id=key, rows=len(rows))
    db.commit()
    return Response(workbook_bytes(["student_number", "email", "full_name", "attempt", "status", "ai_score", "final_score", "review_reason"], rows, "Grades"),
                    media_type=XLSX, headers={"Content-Disposition": 'attachment; filename="exam-grades.xlsx"'})
