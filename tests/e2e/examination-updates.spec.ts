import { test, expect } from "@playwright/test";

test("published exam supports manual and Excel additions and opens completed attempts", async ({
  page,
}) => {
  const writes: { path: string; body: unknown }[] = [];
  const exam = {
    id: "exam",
    name: "English final",
    status: "PUBLISHED",
    course_id: "course",
    course_name: "English",
    teacher_id: "teacher",
    time_limit: 900,
    participant_count: 2,
    sitting_count: 1,
  };
  const roster = [
    {
      student_id: "student",
      name: "Nguyễn An",
      email: "an@example.edu",
      student_number: "SV01",
      opens_at: 1,
      closes_at: 9999999999,
      sessions: [
        {
          id: "result",
          status: "COMPLETED",
          attempt_number: 1,
          final_score: 8,
        },
      ],
    },
    {
      student_id: "waiting",
      name: "Chưa thi",
      email: "waiting@example.edu",
      student_number: "SV02",
      opens_at: null,
      closes_at: null,
      sessions: [],
    },
  ];
  const assessment = {
    score: 8,
    confidence: 0.95,
    model: "local-model",
    review_required: true,
    reasoning_summary: "Đánh giá bài nói",
    criteria: [],
    pronunciation: {
      status: "COMPLETED",
      model: "gopt-librispeech",
      applied_criteria: ["Phát âm"],
      scores: {
        total: 8,
        accuracy: 8,
        completeness: 8,
        fluency: 8,
        prosody: 8,
      },
    },
  };
  const review = {
    id: "result",
    exam_name: exam.name,
    student_name: "Nguyễn An",
    status: "COMPLETED",
    final_score: 8,
    snapshot: {
      rubric_version: 1,
      knowledge_version: "test",
      ai_provider: "local",
      llm_model: "local-model",
    },
    attempts: [
      {
        id: "attempt",
        sequence: 1,
        status: "GRADED",
        question: { text: "Describe a useful skill." },
        transcript: "My original answer",
        stt_confidence: 0.95,
        assessment,
        evidence: [],
        reviews: [],
      },
    ],
  };
  await page.route("**/api/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    let json: unknown = [];
    if (path.endsWith("/auth/me"))
      json = { id: "admin", name: "Admin", role: "ADMIN" };
    else if (path.endsWith("/dashboard"))
      json = { courses: 1, documents: 0, exams: 1, sessions: 1 };
    else if (path === "/api/admin/courses")
      json = [{ id: "course", code: "ENG", name: "English", status: "ACTIVE" }];
    else if (path === "/api/admin/examination/exams") json = [exam];
    else if (path.endsWith("/roster")) json = roster;
    else if (path.endsWith("/draft"))
      json = { status: "PUBLISHED", snapshot: { questions: [], criteria: [] } };
    else if (path === "/api/admin/results/result") json = review;
    else if (path.endsWith("/students") || path.endsWith("/import-students")) {
      writes.push({
        path,
        body: path.endsWith("/students")
          ? route.request().postDataJSON()
          : route.request().postData(),
      });
      json = { added: 1, accounts_created: 1 };
    }
    await route.fulfill({ json });
  });
  await page.goto("/");
  await page
    .getByRole("button", { name: "Điều phối kỳ thi", exact: true })
    .click();
  await page
    .getByRole("button", {
      name: "Danh sách thí sinh English final",
      exact: true,
    })
    .click();
  await expect(
    page.getByRole("button", { name: /^Sinh viên & lịch thi/ }),
  ).toHaveAttribute("aria-pressed", "true");
  await expect(
    page.getByRole("combobox", { name: "Lớp học phần", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Nhập danh sách Excel", exact: true }),
  ).toBeVisible();
  await page.getByText("Thêm sinh viên thủ công", { exact: true }).click();
  await page.getByLabel("MSSV", { exact: true }).fill("NEW01");
  await page.getByLabel("Họ tên", { exact: true }).fill("New learner");
  await page.getByLabel("Email", { exact: true }).fill("new@example.edu");
  await page
    .getByRole("button", { name: "Thêm sinh viên", exact: true })
    .click();
  await expect.poll(() => writes.length).toBe(1);
  expect(writes[0]).toEqual({
    path: "/api/admin/exams/exam/students",
    body: {
      student_number: "NEW01",
      name: "New learner",
      email: "new@example.edu",
      password: "",
    },
  });
  await page.getByLabel("File danh sách", { exact: true }).setInputFiles({
    name: "students.xlsx",
    mimeType:
      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    buffer: Buffer.from("test workbook"),
  });
  await page
    .getByRole("button", { name: "Nhập danh sách Excel", exact: true })
    .click();
  await expect.poll(() => writes.length).toBe(2);
  expect(writes[1].path).toBe("/api/admin/exams/exam/import-students");
  expect(writes[1].body).toContain('filename="students.xlsx"');
  await expect(
    page.getByLabel("Chọn Nguyễn An", { exact: true }),
  ).toBeDisabled();
  await expect(
    page.getByRole("columnheader", { name: "Số lượt thi" }),
  ).toBeVisible();
  await page.getByLabel("Tìm sinh viên theo tên, MSSV hoặc email").fill("SV01");
  await expect(
    page.getByText("waiting@example.edu", { exact: true }),
  ).toHaveCount(0);
  await page.getByLabel("Tìm sinh viên theo tên, MSSV hoặc email").fill("");
  await page.getByLabel(/Chỉ sinh viên đã nộp bài/).check();
  await expect(
    page.getByText("waiting@example.edu", { exact: true }),
  ).toHaveCount(0);
  await page.getByRole("button", { name: "Nguyễn An", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "English final · Lần 1" }),
  ).toBeVisible();
  await page.getByRole("button", { name: /^Câu trả lời/ }).click();
  await expect(
    page.getByText("My original answer", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText(/Đã tính theo trọng số rubric: Phát âm/),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Danh sách sinh viên", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Danh sách sinh viên (2)" }),
  ).toBeVisible();
  await expect(page.getByLabel(/Chỉ sinh viên đã nộp bài/)).toBeChecked();
});
