"use client";
import { hasRole } from "./api";
import styles from "./examination.module.css";
import { useCallback, useEffect, useState } from "react";
import { api, send, errorText, Course, User, Review } from "./api";
import { ReviewPage } from "./admin";
import { Action, Badge, Empty, Field, Form } from "./shared";
import ExcelImport from "./excel-import";
import ExamDraftReview from "./exam-draft-review";
import ExamRosterPicker from "./exam-roster-picker";

type ExamRow = {
  participant_count?: number;
  sitting_count?: number;
  imported?: boolean;
  id: string;
  name: string;
  status: string;
  course_id: string;
  course_name: string;
  teacher_id: string;
  time_limit: number;
};
type Candidate = {
  student_id: string;
  student_number: string;
  name: string;
  email: string;
  opens_at: number | null;
  closes_at: number | null;
  sessions: {
    id: string;
    status: string;
    attempt_number: number;
    final_score: number | null;
  }[];
};
type Teacher = { id: string; name: string };
const date = (value: number | null) =>
  value ? new Date(value * 1000).toLocaleString("vi-VN") : "Chưa xếp lịch";

export default function Examination({
  user,
  navigate,
}: {
  user: User;
  navigate: (page: string) => void;
}) {
  const [exams, setExams] = useState<ExamRow[]>([]);
  const [courses, setCourses] = useState<Course[]>([]);
  const [teachers, setTeachers] = useState<Teacher[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [initialPanel, setInitialPanel] = useState<"content" | "roster">(
    "content",
  );
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("");
  const officer = hasRole(user, "ADMIN", "EXAM_OFFICER");
  const load = useCallback(async () => {
    const [list, c, t] = await Promise.all([
      api<ExamRow[]>("/admin/examination/exams"),
      api<Course[]>("/admin/courses"),
      officer
        ? api<Teacher[]>("/admin/examination/teachers")
        : Promise.resolve([]),
    ]);
    setExams(list);
    setCourses(c);
    setTeachers(t);
    setError("");
  }, [officer]);
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- Updates follow completed API requests.
    void load()
      .catch((e) => setError(errorText(e)))
      .finally(() => setLoading(false));
  }, [load]);
  const exam = exams.find((e) => e.id === selected);
  const visible = exams.filter(
    (e) =>
      (!status || e.status === status) &&
      `${e.name} ${e.course_name}`
        .toLocaleLowerCase("vi")
        .includes(query.toLocaleLowerCase("vi")),
  );
  return (
    <div className={styles.workspace}>
      <div className="page-heading">
        <div>
          <h1>Điều phối kỳ thi</h1>
          <p>Quản lý đề, danh sách sinh viên và lịch thi trong một nơi.</p>
        </div>
      </div>
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      {exam ? (
        <>
          <button className="text-button" onClick={() => setSelected(null)}>
            ← Tất cả kỳ thi
          </button>
          <ExamOperations
            key={exam.id}
            exam={exam}
            initialPanel={initialPanel}
            courses={courses}
            officer={officer}
            editable={hasRole(user, "ADMIN", "TEACHER")}
            admin={hasRole(user, "ADMIN")}
            refresh={load}
            navigate={navigate}
          />
        </>
      ) : (
        <>
          <div className={styles.tools}>
            {officer && (
              <details className="panel">
                <summary>Tạo kỳ thi & giao giảng viên</summary>
                <p>
                  Mỗi môn có một giảng viên phụ trách. Phân công ở đây áp dụng
                  cho toàn bộ đề và bài chấm của môn đó.
                </p>
                {!teachers.length && (
                  <p>
                    Cấp vai trò giảng viên trong Người dùng để thêm người phụ
                    trách.
                  </p>
                )}
                <Form
                  className={`form ${styles.createForm}`}
                  label="Tạo kỳ thi"
                  onSubmit={async (d) => {
                    const created = await send<{ id: string }>(
                      "/admin/examination/exams",
                      {
                        course_id: d.get("course_id"),
                        teacher_id: d.get("teacher_id"),
                        name: d.get("name"),
                        time_limit: Number(d.get("minutes")) * 60,
                      },
                    );
                    await load();
                    setInitialPanel("content");
                    setSelected(created.id);
                  }}
                >
                  <Field label="Tên kỳ thi" name="name" />
                  <label>
                    Môn học
                    <select name="course_id" required defaultValue="">
                      <option value="" disabled>
                        Chọn môn học
                      </option>
                      {courses
                        .filter((c) => c.status === "ACTIVE")
                        .map((c) => (
                          <option value={c.id} key={c.id}>
                            {c.code} · {c.name}
                          </option>
                        ))}
                    </select>
                  </label>
                  <label>
                    Giảng viên
                    <select name="teacher_id" required defaultValue="">
                      <option value="" disabled>
                        Chọn giảng viên
                      </option>
                      {teachers.map((t) => (
                        <option value={t.id} key={t.id}>
                          {t.name}
                        </option>
                      ))}
                    </select>
                  </label>
                  <Field
                    label="Thời lượng (phút)"
                    name="minutes"
                    type="number"
                    min={1}
                    max={180}
                    defaultValue={15}
                  />
                </Form>
              </details>
            )}
            <ExcelImport kind="exams" saved={load} />
          </div>
          <section aria-label="Danh sách kỳ thi" className={styles.examList}>
            <div className={styles.listHeading}>
              <h2>
                Kỳ thi <span className="muted">({exams.length})</span>
              </h2>
              <small>{visible.length} kết quả</small>
            </div>
            <div className={styles.filters}>
              <label>
                Tìm kỳ thi
                <input
                  type="search"
                  placeholder="Tên kỳ thi hoặc môn học…"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                />
              </label>
              <label>
                Trạng thái
                <select
                  value={status}
                  onChange={(e) => setStatus(e.target.value)}
                >
                  <option value="">Tất cả trạng thái</option>
                  <option value="DRAFT">Bản nháp</option>
                  <option value="GENERATED">Chờ giảng viên duyệt</option>
                  <option value="TEACHER_APPROVED">
                    Chờ khảo thí kiểm tra
                  </option>
                  <option value="PUBLISHED">Đã công bố</option>
                </select>
              </label>
            </div>
            {loading ? (
              <Empty>Đang tải kỳ thi…</Empty>
            ) : (
              <div className={styles.examGrid}>
                {visible.map((e) => (
                  <article className={`panel ${styles.examCard}`} key={e.id}>
                    <div className={styles.cardMeta}>
                      <Badge status={e.status} />
                      <span>{e.time_limit / 60} phút</span>
                    </div>
                    <h3>{e.name}</h3>
                    <p>{e.course_name}</p>
                    <p>
                      {e.participant_count ?? 0} sinh viên ·{" "}
                      {e.sitting_count ?? 0} lượt thi
                    </p>
                    <button
                      className="button secondary"
                      aria-label={`Danh sách thí sinh ${e.name}`}
                      onClick={() => {
                        setInitialPanel("roster");
                        setSelected(e.id);
                      }}
                    >
                      Danh sách thí sinh →
                    </button>
                    <button
                      className="button secondary"
                      onClick={() => {
                        setInitialPanel("content");
                        setSelected(e.id);
                      }}
                      aria-label={`Mở kỳ thi ${e.name}`}
                    >
                      Mở kỳ thi →
                    </button>
                  </article>
                ))}
              </div>
            )}
            {!loading && !visible.length && (
              <Empty>
                {exams.length
                  ? "Không có kỳ thi phù hợp với bộ lọc."
                  : "Chưa có kỳ thi được giao."}
              </Empty>
            )}
          </section>
        </>
      )}
    </div>
  );
}

function ExamOperations({
  exam,
  initialPanel,
  courses,
  officer,
  editable,
  admin,
  refresh,
  navigate,
}: {
  exam: ExamRow;
  initialPanel: "content" | "roster";
  courses: Course[];
  officer: boolean;
  editable: boolean;
  admin: boolean;
  refresh: () => Promise<unknown>;
  navigate: (page: string) => void;
}) {
  const [activePanel, setActivePanel] = useState<"content" | "roster">(
    initialPanel,
  );
  const [rosterLoading, setRosterLoading] = useState(true);
  const [roster, setRoster] = useState<Candidate[]>([]);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [selected, setSelected] = useState<string[]>([]);
  const [review, setReview] = useState<Review | null>(null);
  const [completedOnly, setCompletedOnly] = useState(false);
  const [search, setSearch] = useState("");
  const reviewId = review?.id;
  const openReview = async (id: string) => {
    setReview(await api<Review>(`/admin/results/${id}`));
  };
  useEffect(() => {
    if (!reviewId) return;
    let active = true;
    const timer = setInterval(() => {
      void api<Review>(`/admin/results/${reviewId}`)
        .then((value) => {
          if (active) setReview(value);
        })
        .catch((e) => {
          if (active) setError(errorText(e));
        });
    }, 5000);
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, [reviewId]);
  const loadRoster = useCallback(async () => {
    const rows = await api<Candidate[]>(`/admin/exams/${exam.id}/roster`);
    setRoster(rows);
    setSelected((ids) =>
      ids.filter((id) =>
        rows.some((r) => r.student_id === id && !r.sessions?.length),
      ),
    );
    setError("");
  }, [exam.id]);
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- Updates follow completed API requests.
    void loadRoster()
      .catch((e) => setError(errorText(e)))
      .finally(() => setRosterLoading(false));
  }, [loadRoster]);
  useEffect(() => {
    if (activePanel !== "roster" || reviewId) return;
    let active = true;
    let fetching = false;
    const timer = setInterval(async () => {
      if (document.hidden || fetching) return;
      fetching = true;
      try {
        const rows = await api<Candidate[]>(`/admin/exams/${exam.id}/roster`);
        if (active) {
          setRoster(rows);
          setSelected((ids) =>
            ids.filter((id) =>
              rows.some(
                (row) => row.student_id === id && !row.sessions?.length,
              ),
            ),
          );
        }
      } catch (e) {
        if (active) setError(errorText(e));
      } finally {
        fetching = false;
      }
    }, 10000);
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, [activePanel, reviewId, exam.id]);
  const completed = (row: Candidate) =>
    (row.sessions ?? []).some((sitting) =>
      ["SUBMITTED", "REVIEW_REQUIRED", "COMPLETED"].includes(sitting.status),
    );
  const visibleRoster = roster.filter(
    (row) =>
      (!completedOnly || completed(row)) &&
      `${row.name} ${row.email} ${row.student_number}`
        .toLocaleLowerCase("vi")
        .includes(search.trim().toLocaleLowerCase("vi")),
  );
  const schedulable = visibleRoster.filter(
    (row) => !(row.sessions ?? []).length,
  );
  if (review)
    return (
      <>
        {error && (
          <p role="alert" className="error">
            {error}
          </p>
        )}
        <ReviewPage
          backLabel="Danh sách sinh viên"
          review={review}
          admin={admin}
          canGrade={editable}
          back={() => {
            setReview(null);
            void loadRoster().catch((e) => setError(errorText(e)));
          }}
          refresh={() => openReview(review.id)}
          open={openReview}
        />
      </>
    );
  return (
    <div className={styles.operations}>
      <header className={`panel ${styles.summary}`}>
        <div>
          <h2>{exam.name}</h2>
          <p>
            {exam.course_name} · {exam.time_limit / 60} phút
          </p>
        </div>
        <Badge status={exam.status} />
      </header>
      <nav className={styles.tabBar} aria-label="Thao tác kỳ thi">
        <button
          type="button"
          aria-pressed={activePanel === "content"}
          onClick={() => setActivePanel("content")}
        >
          Đề thi & duyệt
        </button>
        <button
          type="button"
          aria-pressed={activePanel === "roster"}
          onClick={() => setActivePanel("roster")}
        >
          Sinh viên & lịch thi ({roster.length})
        </button>
      </nav>
      <section
        className="panel"
        hidden={activePanel !== "content"}
        aria-label="Đề thi và phê duyệt"
      >
        {error && (
          <p role="alert" className="error">
            {error}
          </p>
        )}
        {editable && exam.status === "DRAFT" && (
          <>
            <p>
              {exam.imported
                ? "Đề dùng nguyên câu hỏi và rubric đã nhập. Cần tài liệu READY cho từng chủ đề trước khi tạo bản nháp để gắn nguồn và duyệt."
                : "Mở môn học để sửa bản nháp: chủ đề, số câu hỏi và độ khó cho từng nhóm câu. Đặt số lượng = 1 để cấu hình từng câu."}
            </p>
            <button
              className="button secondary"
              onClick={() => navigate("courses")}
            >
              Cấu hình đề trong môn học
            </button>
            <Action
              action={async () => {
                await send(`/admin/exams/${exam.id}/generate`);
                await refresh();
              }}
            >
              {exam.imported
                ? "Tạo bản nháp từ câu hỏi đã nhập"
                : "Sinh câu hỏi & rubric"}
            </Action>
          </>
        )}
        {["GENERATED", "TEACHER_APPROVED", "PUBLISHED"].includes(
          exam.status,
        ) && (
          <ExamDraftReview
            key={`${exam.id}-${exam.status}`}
            examId={exam.id}
            editable={editable || officer}
            canApprove={editable}
            refresh={refresh}
          />
        )}
        {(officer || editable) &&
          ["GENERATED", "TEACHER_APPROVED"].includes(exam.status) && (
            <details>
              <summary>Trả về bản nháp để sửa cấu hình</summary>
              <Form
                label="Trả về bản nháp"
                onSubmit={async (d) => {
                  await send(`/admin/exams/${exam.id}/return-draft`, {
                    reason: d.get("reason"),
                  });
                  await refresh();
                }}
              >
                <Field label="Lý do" name="reason" />
              </Form>
            </details>
          )}
      </section>
      <section
        className="panel"
        hidden={activePanel !== "roster"}
        aria-label="Sinh viên và lịch thi"
      >
        <h2>Danh sách sinh viên ({roster.length})</h2>
        <p className="muted">
          {
            roster.filter((r) =>
              r.sessions?.some((s) => s.status === "IN_PROGRESS"),
            ).length
          }{" "}
          đang thi · {roster.filter(completed).length} đã nộp bài. Số lượt thi
          không tính phiên kiểm tra thiết bị và lượt đã xóa. Danh sách tự cập
          nhật mỗi 10 giây.
        </p>
        <label>
          Tìm sinh viên theo tên, MSSV hoặc email
          <input
            type="search"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </label>
        {officer && (
          <div className={styles.actions}>
            <a
              className="button secondary"
              href="/api/admin/examination/template.xlsx"
              download
            >
              Tải template Excel
            </a>
            <a
              className="button secondary"
              href={`/api/admin/exams/${exam.id}/grades.xlsx`}
              download
            >
              Xuất điểm Excel
            </a>
          </div>
        )}
        {officer && (
          <>
            <ExamRosterPicker
              examId={exam.id}
              courseId={exam.course_id}
              courses={courses}
              added={async (message) => {
                setMessage(message);
                await loadRoster();
              }}
            />
            <details>
              <summary>Thêm sinh viên thủ công</summary>
              <Form
                label="Thêm sinh viên"
                onSubmit={async (data) => {
                  const result = await send<{
                    added: number;
                    accounts_created: number;
                  }>(`/admin/exams/${exam.id}/students`, {
                    student_number: data.get("student_number"),
                    email: data.get("email"),
                    name: data.get("name"),
                    password: data.get("password") || "",
                  });
                  setMessage(
                    `Đã thêm ${result.added} sinh viên, tạo ${result.accounts_created} tài khoản.`,
                  );
                  await loadRoster();
                }}
              >
                <Field label="MSSV" name="student_number" maxLength={80} />
                <Field label="Họ tên" name="name" maxLength={150} />
                <Field label="Email" name="email" type="email" />
                <Field
                  label="Mật khẩu ban đầu (tùy chọn)"
                  name="password"
                  type="password"
                  required={false}
                  minLength={12}
                  maxLength={128}
                />
              </Form>
            </details>
            {exam.status === "PUBLISHED" && (
              <p>
                Sinh viên bổ sung cần được xếp lịch trước khi vào thi. Đề và kết
                quả đã có không thay đổi.
              </p>
            )}
            <p>
              Nhập .xlsx tối đa 5000 sinh viên. Mật khẩu ban đầu tùy chọn: điền
              tối thiểu 12 ký tự để đăng nhập email/mật khẩu; để trống nếu dùng
              Google với email đã nhập. Tài khoản có sẵn giữ nguyên mật khẩu.
            </p>
            <Form
              label="Nhập danh sách Excel"
              onSubmit={async (d) => {
                const result = await api<{
                  added: number;
                  accounts_created: number;
                }>(`/admin/exams/${exam.id}/import-students`, {
                  method: "POST",
                  body: d,
                });
                setMessage(
                  `Đã thêm ${result.added} sinh viên, tạo ${result.accounts_created} tài khoản.`,
                );
                await loadRoster();
              }}
            >
              <label>
                File danh sách
                <input type="file" name="file" accept=".xlsx" required />
              </label>
            </Form>
          </>
        )}
        {error && (
          <p role="alert" className="error">
            {error}
          </p>
        )}
        {message && (
          <p role="status" className={styles.notice}>
            {message}
          </p>
        )}
        {rosterLoading && <Empty>Đang tải danh sách sinh viên…</Empty>}
        {!rosterLoading && !roster.length && (
          <Empty>Chưa có sinh viên trong kỳ thi.</Empty>
        )}
        {!!roster.length && (
          <>
            <label>
              <input
                type="checkbox"
                checked={completedOnly}
                onChange={(event) => setCompletedOnly(event.target.checked)}
              />
              Chỉ sinh viên đã nộp bài ({roster.filter(completed).length})
            </label>
            <label className={styles.selectAll}>
              <input
                type="checkbox"
                checked={
                  schedulable.length > 0 &&
                  schedulable.every((row) => selected.includes(row.student_id))
                }
                onChange={(e) =>
                  setSelected(
                    e.target.checked
                      ? schedulable.map((r) => r.student_id)
                      : [],
                  )
                }
              />
              Chọn tất cả sinh viên chưa tạo phiên thi
            </label>
            {!visibleRoster.length && (
              <Empty>Không có sinh viên phù hợp với bộ lọc.</Empty>
            )}
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Chọn</th>
                    <th>MSSV</th>
                    <th>Sinh viên</th>
                    <th>Email</th>
                    <th>Mở vào thi</th>
                    <th>Đóng vào thi</th>
                    <th>Số lượt thi</th>
                    <th>Bài thi & kết quả</th>
                  </tr>
                </thead>
                <tbody>
                  {visibleRoster.map((r) => (
                    <tr key={r.student_id}>
                      <td>
                        <input
                          type="checkbox"
                          aria-label={`Chọn ${r.name}`}
                          checked={selected.includes(r.student_id)}
                          disabled={!!r.sessions?.length}
                          onChange={(e) =>
                            setSelected(
                              e.target.checked
                                ? [...selected, r.student_id]
                                : selected.filter((id) => id !== r.student_id),
                            )
                          }
                        />
                      </td>
                      <td>{r.student_number}</td>
                      <td>
                        {r.sessions?.length ? (
                          <Action action={() => openReview(r.sessions[0].id)}>
                            {r.name}
                          </Action>
                        ) : (
                          r.name
                        )}
                      </td>
                      <td>{r.email}</td>
                      <td>{date(r.opens_at)}</td>
                      <td>{date(r.closes_at)}</td>
                      <td>
                        {
                          (r.sessions ?? []).filter(
                            (s) => s.status !== "DEVICE_CHECK",
                          ).length
                        }
                      </td>
                      <td>
                        {r.sessions?.length
                          ? r.sessions.map((sitting) => (
                              <div key={sitting.id}>
                                <Action action={() => openReview(sitting.id)}>
                                  Xem bài lần {sitting.attempt_number}
                                </Action>
                                <Badge status={sitting.status} /> ·{" "}
                                {sitting.final_score ?? "Chưa xác nhận"}
                              </div>
                            ))
                          : "Chưa thi"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
        {officer && ["TEACHER_APPROVED", "PUBLISHED"].includes(exam.status) && (
          <>
            <h3>Xếp lịch cho {selected.length} sinh viên đã chọn</h3>
            <p>
              Giờ hiển thị theo múi giờ của máy. Sinh viên được bắt đầu trong
              khoảng này và có đủ thời lượng bài thi kể từ lúc bắt đầu.
            </p>
            <Form
              className={`form ${styles.createForm}`}
              label="Lưu lịch thi"
              onSubmit={async (d) => {
                if (!selected.length)
                  throw new Error("Chọn ít nhất một sinh viên");
                if (
                  new Date(String(d.get("closes_at"))) <=
                  new Date(String(d.get("opens_at")))
                )
                  throw new Error("Giờ đóng phải sau giờ mở vào thi");
                await send(
                  `/admin/exams/${exam.id}/schedule`,
                  {
                    student_ids: selected,
                    opens_at:
                      new Date(String(d.get("opens_at"))).getTime() / 1000,
                    closes_at:
                      new Date(String(d.get("closes_at"))).getTime() / 1000,
                  },
                  "PUT",
                );
                await loadRoster();
                setMessage("Đã lưu lịch thi.");
              }}
            >
              <Field
                label="Giờ mở vào thi"
                name="opens_at"
                type="datetime-local"
              />
              <Field
                label="Giờ đóng vào thi"
                name="closes_at"
                type="datetime-local"
              />
            </Form>
            {exam.status === "TEACHER_APPROVED" && (
              <Action
                action={async () => {
                  await send(`/admin/exams/${exam.id}/office-approve`);
                  await refresh();
                }}
              >
                Xác nhận đã kiểm tra đề & mở kỳ thi
              </Action>
            )}
          </>
        )}
      </section>
    </div>
  );
}
