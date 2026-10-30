import { test, expect } from "@playwright/test";
import {
  installResultRoster,
  selectResultExam,
} from "./helpers/results-roster";

test("long rubric feedback is collapsed with full text available and scores intact", async ({
  page,
}) => {
  const long =
    "Nêu đúng khái niệm nhưng ví dụ chưa thể hiện đầy đủ cách áp dụng vào tình huống thực tế. ".repeat(
      8,
    );
  const short = "Giải thích đúng, thiếu ví dụ minh họa.";
  const review = {
    id: "result",
    exam_name: "English oral",
    student_name: "Student",
    status: "COMPLETED",
    final_score: 8,
    snapshot: {
      rubric_version: 1,
      knowledge_version: "test",
      ai_provider: "gemini",
    },
    attempts: [
      {
        id: "a",
        sequence: 1,
        status: "GRADED",
        question: { text: "Question" },
        transcript: "Answer",
        stt_confidence: 0.95,
        evidence: [],
        reviews: [],
        grading_targets: [],
        assessment: {
          score: 8,
          confidence: 0.95,
          reasoning_summary: long,
          criteria: [
            { name: "Kiến thức", score: 4, comment: long },
            { name: "Vận dụng", score: 4, comment: short },
          ],
        },
      },
    ],
  };
  await page.route("**/api/**", (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path === "/api/auth/me")
      return route.fulfill({
        json: { id: "admin", name: "Admin", role: "ADMIN" },
      });
    if (path === "/api/admin/results/result")
      return route.fulfill({ json: review });
    return route.fulfill({
      json: path.endsWith("dashboard")
        ? { courses: 1, documents: 0, exams: 1, sessions: 1 }
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
  const assessment = page.locator(".assessment");
  await expect(assessment.locator(".score")).toContainText("8");
  await expect(
    assessment.getByText("Kiến thức: 4", { exact: true }),
  ).toBeVisible();
  await expect(assessment.getByText(short, { exact: true })).toBeVisible();
  const details = assessment.locator("details");
  await expect(details).toHaveCount(2);
  for (const note of await details.all()) {
    await expect(note.locator("p")).toBeHidden();
    expect((await note.locator("summary").innerText()).length).toBeLessThan(
      260,
    );
    await note.locator("summary").click();
    await expect(note.locator("p")).toBeVisible();
    await expect(note.locator("p")).toHaveText(long);
    await note.locator("summary").click();
    await expect(note.locator("p")).toBeHidden();
  }
});
