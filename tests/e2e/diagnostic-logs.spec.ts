import { test, expect } from "@playwright/test";
import {
  installResultRoster,
  selectResultExam,
} from "./helpers/results-roster";

for (const width of [1440, 768]) {
  test(`admin filters, expands and paginates diagnostic logs at ${width}px`, async ({
    page,
  }) => {
    await page.setViewportSize({ width, height: 1000 });
    const queries: URLSearchParams[] = [];
    const telemetry: Record<string, unknown>[] = [];
    await page.route("**/api/**", (route) => {
      const url = new URL(route.request().url());
      if (url.pathname === "/api/auth/me")
        return route.fulfill({
          json: {
            id: "admin",
            name: "Admin",
            roles: ["STUDENT", "ADMIN"],
            role: "STUDENT",
          },
        });
      if (url.pathname === "/api/diagnostics/client") {
        telemetry.push(route.request().postDataJSON());
        return route.fulfill({ status: 204 });
      }
      if (url.pathname === "/api/admin/diagnostics") {
        queries.push(url.searchParams);
        const older = url.searchParams.has("before");
        return route.fulfill({
          json: {
            items: [
              {
                id: older ? 1 : 2,
                created_at: Date.now() / 1000,
                source: "AI",
                level: "WARNING",
                event: older ? "operation_started" : "operation_failed",
                details: {
                  stage: "ollama.chat",
                  model: "qwen2.5:3b",
                  exception_type: "ReadTimeout",
                  session_id: "sitting",
                  elapsed_seconds: 600,
                },
              },
            ],
            next_cursor: older ? null : 2,
            max_events: 10000,
            retention_days: 7,
          },
        });
      }
      return route.fulfill({
        json: url.pathname.endsWith("dashboard")
          ? { courses: 0, documents: 0, exams: 0, sessions: 0 }
          : [],
      });
    });
    await page.goto("/");
    await page
      .getByRole("button", { name: "Log hệ thống", exact: true })
      .click();
    await expect(page.locator(".log-event")).toHaveCount(1);
    expect(queries[0].has("since")).toBe(true);
    await page.getByLabel("Nguồn log", { exact: true }).selectOption("AI");
    await page.getByLabel("Mức log", { exact: true }).selectOption("WARNING");
    await page.getByLabel("Mã request / tác vụ / lượt thi").fill("sitting");
    await page.getByLabel("Model (tên chính xác)").fill("qwen2.5:3b");
    await page.getByRole("button", { name: "Lọc log", exact: true }).click();
    await expect.poll(() => queries.at(-1)?.get("correlation")).toBe("sitting");
    expect(queries.at(-1)?.get("source")).toBe("AI");
    expect(queries.at(-1)?.get("model")).toBe("qwen2.5:3b");
    await page.locator(".log-event summary").click();
    await expect(page.getByText("ReadTimeout", { exact: true })).toBeVisible();
    await page.getByRole("button", { name: "Xem log cũ hơn" }).click();
    await expect(page.locator(".log-event")).toHaveCount(2);
    expect(queries.at(-1)?.get("before")).toBe("2");
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth > innerWidth,
      ),
    ).toBe(false);
    await page.evaluate(() =>
      window.dispatchEvent(
        new ErrorEvent("error", {
          error: new TypeError("private student data"),
          message: "private student data",
        }),
      ),
    );
    await expect.poll(() => telemetry.length).toBe(1);
    expect(telemetry[0]).toMatchObject({
      event: "client_error",
      view: "logs",
      exception_type: "TypeError",
    });
    expect(JSON.stringify(telemetry)).not.toContain("private");
  });
}

test("review selects one answer at a time and links its logs; teachers cannot see logs", async ({
  page,
}) => {
  let admin = true;
  let correlation = "";
  const review = {
    id: "sitting",
    exam_name: "English",
    student_name: "An",
    status: "COMPLETED",
    final_score: 8,
    snapshot: {
      rubric_version: 1,
      knowledge_version: "test",
      ai_provider: "demo",
    },
    attempts: [1, 2].map((sequence) => ({
      id: `a${sequence}`,
      sequence,
      status: "GRADED",
      question: { text: `Question ${sequence}` },
      transcript: `Answer ${sequence}`,
      stt_confidence: 0.95,
      assessment: null,
      evidence: [],
      reviews: [],
    })),
  };
  await page.route("**/api/**", (route) => {
    const url = new URL(route.request().url());
    if (url.pathname === "/api/auth/me")
      return route.fulfill({
        json: { id: "staff", name: "Staff", role: admin ? "ADMIN" : "TEACHER" },
      });
    if (url.pathname === "/api/admin/results/sitting")
      return route.fulfill({ json: review });
    if (url.pathname === "/api/admin/diagnostics") {
      correlation = url.searchParams.get("correlation") || "";
      return route.fulfill({
        json: {
          items: [],
          next_cursor: null,
          max_events: 10000,
          retention_days: 7,
        },
      });
    }
    return route.fulfill({
      json: url.pathname.endsWith("dashboard")
        ? { courses: 1, documents: 0, exams: 1, sessions: 1 }
        : [],
    });
  });
  await installResultRoster(page, review);
  async function openReview() {
    await page.goto("/");
    await page
      .getByRole("button", { name: "Kết quả & xem lại", exact: true })
      .click();
    await selectResultExam(page);
    await page.getByRole("button", { name: "Xem bài →" }).click();
  }
  await openReview();
  await expect(
    page.getByRole("button", { name: "Tổng quan & điểm" }),
  ).toHaveAttribute("aria-pressed", "true");
  await page.getByRole("button", { name: /^Câu trả lời/ }).click();
  await expect(page.getByText("Answer 1", { exact: true })).toBeVisible();
  await expect(page.getByText("Answer 2", { exact: true })).toHaveCount(0);
  await page.getByLabel("Chọn câu trả lời", { exact: true }).selectOption("a2");
  await expect(page.getByText("Answer 2", { exact: true })).toBeVisible();
  await expect(page.getByText("Answer 1", { exact: true })).toHaveCount(0);
  await page.getByRole("button", { name: "Log xử lý", exact: true }).click();
  await expect.poll(() => correlation).toBe("sitting");
  await expect(
    page.getByText("Chưa có log phù hợp.", { exact: true }),
  ).toBeVisible();
  admin = false;
  await openReview();
  await expect(
    page.getByRole("button", { name: "Log xử lý", exact: true }),
  ).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: "Log hệ thống", exact: true }),
  ).toHaveCount(0);
});
