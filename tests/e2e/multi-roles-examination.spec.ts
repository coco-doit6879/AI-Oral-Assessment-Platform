import { test, expect, Page } from "@playwright/test";

async function mockWorkspace(page: Page, roles = ["TEACHER", "EXAM_OFFICER"]) {
  let memberRoles = ["STUDENT", "TEACHER"];
  const saved: string[][] = [];
  await page.route("**/api/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    let json: unknown = [];
    if (path === "/api/auth/me")
      json = {
        id: "actor",
        username: "actor",
        name: "Nguyễn Minh",
        role: roles[0],
        roles,
      };
    if (path === "/api/admin/dashboard")
      json = { courses: 6, exams: 6, documents: 18, sessions: 0 };
    if (path === "/api/admin/courses")
      json = [
        {
          id: "course",
          code: "ENT001",
          name: "ENT001 — Speaking Test",
          status: "ACTIVE",
        },
      ];
    if (path === "/api/admin/examination/teachers")
      json = [{ id: "actor", name: "Nguyễn Minh" }];
    if (path === "/api/admin/users")
      json = [
        {
          id: "member",
          username: "member",
          name: "Sinh viên An",
          role: "TEACHER",
          roles: memberRoles,
        },
      ];
    if (path === "/api/admin/users/member/roles") {
      memberRoles = route.request().postDataJSON().roles;
      saved.push(memberRoles);
      json = { id: "member", role: memberRoles[0], roles: memberRoles };
    }
    if (path === "/api/admin/examination/exams")
      json = ["ENT001", "ENT104", "ENT203", "ENT303", "ENT403", "ENT503"].map(
        (code, i) => ({
          id: code,
          name: `${code} — Speaking Test Sample — Activities and introductions`,
          status: i === 1 ? "PUBLISHED" : "GENERATED",
          course_id: "course",
          course_name: `${code} — Speaking Test`,
          teacher_id: "actor",
          time_limit: 600,
        }),
      );
    if (path.endsWith("/roster"))
      json = [
        {
          student_id: "member",
          student_number: "SE123",
          name: "Sinh viên An",
          email: "very.long.student.address@example.test",
          opens_at: null,
          closes_at: null,
        },
      ];
    if (path.endsWith("/draft"))
      json = {
        status: "GENERATED",
        snapshot: {
          questions: [
            {
              text: "Describe your typical day, give details and examples.",
              difficulty: "MEDIUM",
              expected_concepts: ["Relevant details"],
              reference_chunk_ids: ["a".repeat(180)],
              english_terms: [],
              preparation_seconds: 120,
              recording_seconds: 180,
            },
          ],
          criteria: [
            {
              name: "Ideas",
              description: "Relevant and well developed ideas.",
              max_score: 2,
              weight: 1,
            },
          ],
        },
      };
    await route.fulfill({ json });
  });
  return saved;
}

for (const width of [1440, 390]) {
  test(`examination layout and combined teacher/officer controls at ${width}px`, async ({
    page,
  }) => {
    await page.setViewportSize({ width, height: 1000 });
    await mockWorkspace(page);
    await page.goto("/");
    await page
      .getByRole("button", { name: "Điều phối kỳ thi", exact: true })
      .click();
    await expect(page.getByRole("article")).toHaveCount(6);
    await page
      .getByText("Tạo kỳ thi & giao giảng viên", { exact: true })
      .click();
    await expect(page.getByLabel("Tên kỳ thi", { exact: true })).toBeVisible();
    await page.getByLabel("Tìm kỳ thi", { exact: true }).fill("ENT001");
    await expect(page.getByRole("article")).toHaveCount(1);
    await page.screenshot({
      path: `test-results/examination-${width}-list.png`,
      fullPage: true,
    });
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth + 1,
      ),
    ).toBeTruthy();
    await page.getByRole("button", { name: /^Mở kỳ thi ENT001/ }).click();
    await page.getByRole("button", { name: "Sửa câu 1", exact: true }).click();
    await expect(page.getByLabel("Nội dung câu hỏi")).toBeEditable();
    await expect(
      page.getByRole("button", {
        name: "Duyệt đề & gửi khảo thí",
        exact: true,
      }),
    ).toBeVisible();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth + 1,
      ),
    ).toBeTruthy();
    await page.screenshot({
      path: `test-results/examination-${width}-detail.png`,
      fullPage: true,
    });
    await page.getByRole("button", { name: /Sinh viên & lịch thi/ }).click();
    await expect(
      page.getByRole("link", { name: "Tải template Excel" }),
    ).toBeVisible();
    await page
      .getByLabel("Chọn tất cả sinh viên chưa tạo phiên thi", { exact: true })
      .check();
    await expect(
      page.getByLabel("Chọn Sinh viên An", { exact: true }),
    ).toBeChecked();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth + 1,
      ),
    ).toBeTruthy();
  });
}

test("admin edits multiple roles without losing existing membership and can filter secondary roles", async ({
  page,
}) => {
  const saved = await mockWorkspace(page, ["ADMIN"]);
  await page.goto("/");
  await page.getByRole("button", { name: "Người dùng", exact: true }).click();
  await page.getByLabel("Lọc vai trò").selectOption("STUDENT");
  const row = page.getByRole("row").filter({ hasText: "Sinh viên An" });
  await expect(row).toBeVisible();
  await row.locator("summary").click();
  await row.getByLabel("Khảo thí", { exact: true }).check();
  await expect(row.getByLabel("Sinh viên", { exact: true })).toBeChecked();
  await expect(row.getByLabel("Giảng viên", { exact: true })).toBeChecked();
  await row.getByRole("button", { name: "Lưu quyền", exact: true }).click();
  await expect.poll(() => saved.length).toBe(1);
  expect(saved[0].sort()).toEqual(["EXAM_OFFICER", "STUDENT", "TEACHER"]);
});
