import {
  installResultRoster,
  selectResultExam,
} from "./helpers/results-roster";
import { test, expect } from "@playwright/test";

for (const provider of ["local", "gemini", "google"]) {
  test(`admin selects ${provider} for audio review`, async ({ page }) => {
    const writes: string[] = [];
    const review = {
      id: "result",
      exam_name: "Cloud review",
      student_name: "Student",
      status: "REVIEW_REQUIRED",
      final_score: null,
      snapshot: {
        rubric_version: 1,
        knowledge_version: "test",
        ai_provider: "local",
        llm_model: "qwen3:8b",
      },
      attempts: [
        {
          id: "attempt",
          sequence: 1,
          status: "GRADED",
          question: { text: "Question" },
          transcript: "original local text",
          stt_confidence: 0.9,
          assessment: null,
          evidence: [],
          reviews: [],
        },
      ],
    };
    await page.route("**/api/**", async (route) => {
      const path = new URL(route.request().url()).pathname;
      if (path === "/api/auth/me")
        return route.fulfill({
          json: { id: "admin", role: "ADMIN", name: "Admin" },
        });
      if (path === "/api/admin/results")
        return route.fulfill({ json: [review] });
      if (path === "/api/admin/results/result")
        return route.fulfill({ json: review });
      if (path.endsWith("-review")) {
        writes.push(path);
        expect(route.request().postDataJSON()).toEqual({
          reason: "Check original audio",
        });
        return route.fulfill({
          status: 202,
          json: { id: "job", status: "PENDING" },
        });
      }
      return route.fulfill({
        json: path.endsWith("dashboard")
          ? {
              courses: 0,
              documents: 0,
              exams: 0,
              sessions: 1,
              ai_provider: "local",
            }
          : [],
      });
    });
    await installResultRoster(page, review);
    await page.goto("/");
    await page
      .getByRole("button", { name: "Kết quả & xem lại", exact: true })
      .click();
    await selectResultExam(page);
    await page.getByRole("button", { name: "Xem bài →" }).click();
    await page.getByRole("button", { name: /^Câu trả lời/ }).click();
    await page
      .getByText("Nhận dạng, chấm lại AI & lịch sử", { exact: true })
      .click();
    await page.getByText("Nhận dạng lại & chấm lại", { exact: true }).click();
    await page.getByLabel("Nhà cung cấp nhận dạng lại").selectOption(provider);
    await page
      .getByLabel("Lý do nhận dạng / chấm lại")
      .fill("Check original audio");
    await page
      .getByRole("button", { name: "Chấm lại toàn bộ từ audio", exact: true })
      .click();
    await expect
      .poll(() => writes)
      .toEqual([`/api/admin/attempts/attempt/${provider}-review`]);
    await expect(
      page.getByText("original local text", { exact: true }),
    ).toBeVisible();
  });
}

test("admin uploads Google JSON without changing the STT draft, then selects either cloud provider", async ({
  page,
}) => {
  let speech = {
    provider: "local",
    language: "vi",
    preprocessing: "off",
    server_model: "base",
    gemini_configured: true,
    gemini_model: "gemini-2.5-flash",
    google_configured: false,
    google_credentials: { status: "missing", source: "none", project_id: "" },
  };
  const writes: unknown[] = [];
  await page.route("**/api/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path === "/api/auth/me")
      return route.fulfill({
        json: { id: "admin", role: "ADMIN", name: "Admin" },
      });
    if (path === "/api/admin/settings/platform")
      return route.fulfill({
        json: {
          ai_config_source: "env",
          ai_provider: "local",
          llm_model: "qwen3:8b",
        },
      });
    if (path.endsWith("google-credentials")) {
      expect(route.request().postDataBuffer()?.toString()).toContain(
        "synthetic-json",
      );
      speech = {
        ...speech,
        google_configured: true,
        google_credentials: {
          status: "ready",
          source: "upload",
          project_id: "synthetic-project",
        },
      };
      return route.fulfill({ json: speech });
    }
    if (path === "/api/admin/settings/speech") {
      if (route.request().method() === "PUT") {
        writes.push(route.request().postDataJSON());
        speech = { ...speech, ...route.request().postDataJSON() };
      }
      return route.fulfill({ json: speech });
    }
    return route.fulfill({
      json: path.endsWith("dashboard")
        ? { courses: 0, documents: 0, exams: 0, sessions: 0 }
        : [],
    });
  });
  await page.goto("/");
  await page
    .getByRole("button", { name: "Cấu hình hệ thống", exact: true })
    .click();
  await page
    .getByRole("button", { name: "STT & giọng nói", exact: true })
    .click();
  await page.getByLabel("Nhà cung cấp STT").selectOption("google");
  await page
    .getByText("Google Cloud STT — cấu hình JSON service account", {
      exact: true,
    })
    .click();
  await page
    .getByLabel("File JSON service account Google (tối đa 64 KB)")
    .setInputFiles({
      name: "test.json",
      mimeType: "application/json",
      buffer: Buffer.from('{"test":"synthetic-json"}'),
    });
  await page
    .getByRole("button", { name: "Upload JSON Google STT", exact: true })
    .click();
  await expect(page.getByText(/Đã lưu JSON Google/)).toBeVisible();
  await expect(page.getByLabel("Nhà cung cấp STT")).toHaveValue("google");
  expect(writes).toEqual([]);
  for (const provider of ["google", "gemini"]) {
    await page.getByLabel("Nhà cung cấp STT").selectOption(provider);
    await page
      .getByRole("button", { name: "Lưu cấu hình STT", exact: true })
      .click();
    await expect(
      page.getByText("Đã lưu cấu hình STT.", { exact: true }),
    ).toBeVisible();
  }
  expect(writes).toEqual(
    ["google", "gemini"].map((provider) => ({
      provider,
      language: "vi",
      preprocessing: "off",
      desktop_download_allowed: false,
    })),
  );
});
