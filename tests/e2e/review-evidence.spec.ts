import {
  installResultRoster,
  selectResultExam,
} from "./helpers/results-roster";
import { test, expect } from "@playwright/test";

for (const width of [1440, 768]) {
  test(`review separates screen segments from answer recordings at ${width}px`, async ({
    page,
  }) => {
    await page.setViewportSize({ width, height: 1000 });
    const review = {
      id: "result",
      exam_name: "English",
      student_name: "Student",
      status: "REVIEW_REQUIRED",
      final_score: null,
      snapshot: {
        rubric_version: 1,
        knowledge_version: "test",
        ai_provider: "demo",
      },
      attempts: [
        {
          id: "answer",
          sequence: 1,
          status: "GRADED",
          question: { text: "Introduce yourself" },
          transcript: "My answer",
          stt_confidence: 0.9,
          assessment: null,
          reviews: [],
          evidence: [
            { id: "camera", kind: "VIDEO", created_at: 2 },
            { id: "audio", kind: "AUDIO", created_at: 2 },
            { id: "screen-two", kind: "SCREEN", created_at: 3 },
            { id: "screen-one", kind: "SCREEN", created_at: 1 },
            { id: "legacy-camera", kind: "VIDEO", created_at: 4 },
          ],
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
      if (path.startsWith("/api/evidence/"))
        return route.fulfill({ status: 204 });
      return route.fulfill({
        json: path.endsWith("dashboard")
          ? { courses: 0, documents: 0, exams: 0, sessions: 1 }
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
    await expect(page.locator("video, audio")).toHaveCount(0);
    await page
      .getByRole("button", { name: "Màn hình & giám sát", exact: true })
      .click();
    const screen = page.locator(
      "video[aria-label='Bản ghi màn hình toàn bài']",
    );
    await expect(screen).toHaveCount(1);
    await expect(screen).toHaveAttribute(
      "src",
      "/api/evidence/screen-one/content",
    );
    await page
      .getByRole("combobox", { name: /Bản ghi màn hình toàn bài/ })
      .selectOption("screen-two");
    await expect(screen).toHaveAttribute(
      "src",
      "/api/evidence/screen-two/content",
    );
    await page.getByRole("button", { name: /^Câu trả lời/ }).click();
    await expect(screen).toHaveCount(0);
    const answer = page
      .locator("section.panel")
      .filter({
        has: page.getByRole("heading", { name: "Câu 1", exact: true }),
      });
    await expect(answer.locator("video")).toHaveCount(1);
    await expect(answer.locator("audio")).toHaveCount(1);
    await expect(answer).not.toContainText("Bản ghi màn hình");
    await answer
      .getByRole("combobox", { name: /Camera câu trả lời/ })
      .selectOption("legacy-camera");
    await expect(answer.locator("video")).toHaveAttribute(
      "src",
      "/api/evidence/legacy-camera/content",
    );
    const geometry = await answer.evaluate((section) => {
      const media = section.querySelector("video")!.getBoundingClientRect();
      const column = section
        .querySelector(".review-grid > div")!
        .getBoundingClientRect();
      const assessment = section
        .querySelector(".assessment")!
        .getBoundingClientRect();
      return {
        fits: media.left >= column.left && media.right <= column.right + 1,
        overlaps:
          media.right > assessment.left &&
          media.bottom > assessment.top &&
          media.top < assessment.bottom,
        overflow: document.documentElement.scrollWidth > innerWidth,
      };
    });
    expect(geometry).toEqual({ fits: true, overlaps: false, overflow: false });
  });
}
