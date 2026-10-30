import type { RichContent } from "./question-content";
import type { DesktopPolicy } from "./desktop-policy";
export type Role = "ADMIN" | "TEACHER" | "STUDENT" | "EXAM_OFFICER";
export type User = {
  id: string;
  username: string;
  email?: string | null;
  name: string;
  role: Role | "REVIEWER";
  roles?: Role[];
  requested_role?: string | null;
};
export const roleLabels: Record<Role, string> = {
  ADMIN: "Quản trị viên",
  EXAM_OFFICER: "Khảo thí",
  TEACHER: "Giảng viên",
  STUDENT: "Sinh viên",
};
export function userRoles(user: User): Role[] {
  return (user.roles ?? [user.role]).filter((r): r is Role => r in roleLabels);
}
export function hasRole(user: User, ...allowed: Role[]): boolean {
  const roles = userRoles(user);
  return (
    roles.includes("ADMIN") || roles.some((role) => allowed.includes(role))
  );
}
export function roleNames(user: User): string {
  return userRoles(user)
    .map((role) => roleLabels[role])
    .join(" · ");
}
export type Course = {
  department_id?: string | null;
  id: string;
  code: string;
  name: string;
  description: string;
  status: string;
};
export type Outcome = {
  id: string;
  code: string;
  description: string;
  weight: number;
};
export type Topic = {
  id: string;
  name: string;
  description: string;
  learning_outcome_id: string;
  learning_outcome_ids: string[];
  chapter_ids: string[];
  document_ids: string[];
};
export type Criterion = {
  name: string;
  description: string;
  max_score: number;
  weight: number;
};
export type Rubric = {
  id: string;
  name: string;
  version: number;
  criteria: Criterion[];
};
export type Blueprint = { topic_id: string; difficulty: string; count: number };
export type Exam = {
  category?: string;
  imported?: boolean;
  workflow?: boolean;
  max_attempts: number | null;
  id: string;
  name: string;
  status: string;
  time_limit: number;
  blueprint: Blueprint[];
  rubric_id: string;
  questions?: {
    preparation_seconds?: number;
    recording_seconds?: number;
    text: string;
    rich_content?: RichContent | null;
    english_terms: { term: string; meaning: string }[];
  }[];
};
export type Doc = {
  id: string;
  filename: string;
  status: string;
  error: string | null;
  topic_id: string | null;
  kind: "TEXTBOOK" | "SUPPLEMENT";
  page_count: number | null;
};
export type Chapter = {
  id: string;
  document_id: string;
  title: string;
  level: number;
  start_page: number;
  end_page: number;
  source: string;
};
export type SpeechPolicy = {
  desktop_download_allowed?: boolean;
  desktop_model?: "whisper-small";
  hotwords?: string[];
  provider: "local" | "google" | "gemini" | "local_server";
  preprocessing: "off" | "denoise";
  language: "vi" | "en";
};
export type Workspace = {
  chapters: Chapter[];
  outcomes: Outcome[];
  topics: Topic[];
  documents: Doc[];
  rubrics: Rubric[];
  exams: Exam[];
};
export type Sitting = {
  id: string;
  attempt_number: number;
  status: string;
  created_at: number;
  started_at: number | null;
  completed_at: number | null;
  final_score: number | null;
};
export type ProcessingSummary = {
  status: string;
  total: number;
  transcribed: number;
  completed: number;
  failed: number;
};
export type AnswerProcessing = {
  status: string;
  stage: string;
  updated_at: number;
  runs: number;
  provider: string;
  error: string | null;
  confidence_source?: string;
};
export type Result = {
  ai_score?: number | null;
  low_score?: boolean;
  manual_review?: {
    score: number;
    reason: string;
    reviewed_by: string;
    reviewed_at: number;
  } | null;
  attempt_number: number;
  created_at: number;
  started_at: number | null;
  completed_at: number | null;
  exam_id: string;
  student_id: string;
  max_attempts: number | null;
  remaining_attempts: number | null;
  id: string;
  status: string;
  exam_name: string;
  student_name: string;
  final_score: number | null;
};
export type Chunk = {
  id: string;
  content: string;
  page: number;
  document_id: string;
  heading?: string | null;
};
export type Assessment = {
  score: number | null;
  confidence: number | null;
  status?: "COMPLETED" | "FAILED" | "NOT_GRADED";
  error?: string;
  error_code?: string;
  grading_exam_id?: string;
  review_required: boolean;
  reasoning_summary: string;
  model: string;
  criteria?: { name: string; score: number; comment: string }[];
  retrieved_chunks?: Chunk[];
  pronunciation?: {
    status: "COMPLETED" | "FAILED";
    applied_criteria?: string[];
    model: string;
    message?: string;
    scores?: {
      accuracy: number;
      completeness: number;
      fluency: number;
      prosody: number;
      total: number;
    };
    segments?: number;
    phones?: number;
  };
};
export type ScoreSummary = {
  total_score: number | null;
  question_count: number;
  graded_question_count: number;
  question_scores: { sequence: number; score: number | null }[];
};
export type Review = Result & {
  processing?: ProcessingSummary | null;
  media_removed_at?: number | null;
  proctoring_events?: {
    id: string;
    created_at: number;
    details: { type: string };
  }[];
  score_summary?: ScoreSummary | null;
  history: Sitting[];
  snapshot: {
    rubric_version: number;
    knowledge_version: string;
    llm_model: string;
    ai_provider: string;
  };
  attempts: {
    id: string;
    sequence: number;
    status: string;
    question: { text: string; rich_content?: RichContent | null };
    transcript: string | null;
    stt_confidence: number | null;
    assessment: Assessment | null;
    processing?: AnswerProcessing | null;
    grading_targets?: { id: string; name: string; model: string }[];
    evidence: { id: string; kind: string; created_at?: number }[];
    reviews: {
      id: string;
      policy?: { provider: string };
      status: string;
      reason: string;
      created_at: number;
      error: string | null;
      original: { transcript: string; assessment: Assessment | null };
      result: {
        transcript: string;
        stt_confidence: number;
        confidence_source?: string;
        assessment: Assessment;
        preprocessing: string;
      } | null;
    }[];
  }[];
};
export type StudentExam = {
  opens_at?: number | null;
  closes_at?: number | null;
  server_time?: number;
  workflow?: boolean;
  attempt_count: number;
  remaining_attempts: number | null;
  can_start_new: boolean;
  history: Omit<Sitting, "final_score">[];
  course_id?: string;
  course_name?: string;
  practice?: boolean;
  id: string;
  name: string;
  time_limit: number;
  question_count: number;
  session_id: string | null;
  status: string;
};
export type ExamSession = {
  desktop_policy?: DesktopPolicy;
  timed_questions?: boolean;
  server_processing?: boolean;
  screen_required?: boolean;
  screen_attempt_id?: string | null;
  attempt_number: number;
  practice?: boolean;
  id: string;
  exam_name: string;
  status: string;
  started_at: number | null;
  time_limit: number;
  server_time: number;
  question_count: number;
  answered_count: number;
  current_attempt: {
    id: string;
    sequence: number;
    preparation_seconds?: number;
    recording_seconds?: number;
    prompt_image?: string | null;
    text: string;
    rich_content?: RichContent | null;
    status: string;
  } | null;
};

export let clientBackend: {
  mode: "local" | "online";
  urls: { local: string; online: string };
} | null = null;
export function configureClientBackend(
  value: NonNullable<typeof clientBackend>,
) {
  clientBackend = value;
}
function backendHeaders(): Record<string, string> {
  return clientBackend ? { "X-Oral-Backend": clientBackend.mode } : {};
}
let refreshing: Promise<Response> | null = null;
export class ApiError extends Error {
  status: number;
  code?: string;
  requestId?: string;
  constructor(
    message: string,
    status: number,
    code?: string,
    requestId?: string,
  ) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.requestId = requestId;
  }
}

let clientLogWindow = 0;
let clientLogCount = 0;
export function reportWebEvent(
  event: "request_failed" | "client_error" | "unhandled_rejection",
  path = "/",
  method = "GET",
  http_status?: number,
  request_id?: string,
  view = "unknown",
  exception_type?: string,
) {
  if (
    typeof window === "undefined" ||
    path.includes("diagnostics") ||
    path.startsWith("/auth/")
  )
    return;
  const now = Date.now();
  if (now - clientLogWindow > 60000) {
    clientLogWindow = now;
    clientLogCount = 0;
  }
  if (clientLogCount++ >= 10) return;
  // A separate best-effort request never recursively reports telemetry errors.
  void fetch("/api/diagnostics/client", {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json", ...backendHeaders() },
    body: JSON.stringify({
      event,
      view: [
        "dashboard",
        "courses",
        "exams",
        "results",
        "users",
        "settings",
        "storage",
        "logs",
        "academic",
        "classes",
        "departments",
        "examination",
        "student",
      ].includes(view)
        ? view
        : "unknown",
      exception_type: exception_type
        ? [
            "Error",
            "TypeError",
            "RangeError",
            "ReferenceError",
            "SyntaxError",
            "URIError",
            "EvalError",
          ].includes(exception_type)
          ? exception_type
          : "UnknownError"
        : undefined,
      path: path.split("?")[0].split("#")[0],
      method,
      http_status,
      ...(/^[a-fA-F0-9-]{36}$/.test(request_id || "") ? { request_id } : {}),
    }),
  }).catch(() => {});
}

function canRetry(path: string, init: RequestInit) {
  const method = (init.method || "GET").toUpperCase();
  if (method === "GET") return true;
  if (method === "PUT" && /^\/uploads\/[^/]+\/chunks\/\d+$/.test(path))
    return true;
  if (method !== "POST") return false;
  if (/^\/question-attempts\/[^/]+\/submit$/.test(path))
    return !!new Headers(init.headers).get("Idempotency-Key");
  return (
    path === "/uploads/init" ||
    /^\/uploads\/[^/]+\/complete$/.test(path) ||
    /^\/exam-sessions\/[^/]+\/finish$/.test(path)
  );
}

export async function api<T>(
  path: string,
  init: RequestInit = {},
  retry = true,
): Promise<T> {
  for (let attempt = 0; ; attempt++) {
    try {
      return await requestJSON<T>(path, init, retry);
    } catch (error) {
      const transient =
        error instanceof TypeError ||
        (error instanceof ApiError &&
          [502, 503, 504, 520, 521, 522, 523, 524].includes(error.status));
      if (
        !transient ||
        init.signal?.aborted ||
        !canRetry(path, init) ||
        attempt >= 2
      ) {
        if (!init.signal?.aborted)
          reportWebEvent(
            "request_failed",
            path,
            (init.method || "GET").toUpperCase(),
            error instanceof ApiError ? error.status : 0,
            error instanceof ApiError ? error.requestId : undefined,
          );
        if (error instanceof TypeError)
          throw new Error(
            `Kết nối bị gián đoạn khi gửi ${(init.method || "GET").toUpperCase()} ${path}. Kiểm tra mạng rồi thử lại.`,
          );
        throw error;
      }
      await new Promise((resolve) => setTimeout(resolve, 500 * 2 ** attempt));
    }
  }
}

async function requestJSON<T>(
  path: string,
  init: RequestInit = {},
  retry = true,
): Promise<T> {
  const response = await fetch(`/api${path}`, {
    ...init,
    credentials: "include",
    headers: {
      ...(init.body && typeof init.body === "string"
        ? { "Content-Type": "application/json" }
        : {}),
      ...init.headers,
      ...backendHeaders(),
    },
  });
  if (response.status === 401 && retry && !path.startsWith("/auth/")) {
    refreshing ||= fetch("/api/auth/refresh", {
      method: "POST",
      credentials: "include",
      headers: backendHeaders(),
    }).finally(() => {
      refreshing = null;
    });
    if ((await refreshing).ok) return requestJSON<T>(path, init, false);
  }
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const fields = body?.error?.details?.fields
      ?.map(
        (f: { field: string; message: string }) => `${f.field}: ${f.message}`,
      )
      .join("; ");
    const requestId =
      response.headers.get("x-request-id") || body?.error?.details?.request_id;
    const code = body?.error?.code;
    const detail = [code, requestId ? `mã tra cứu ${requestId}` : ""]
      .filter(Boolean)
      .join(" · ");
    throw new ApiError(
      `${fields || body?.error?.message || `Lỗi kết nối (${response.status})`}` +
        ` [${(init.method || "GET").toUpperCase()} ${path} · HTTP ${response.status}${detail ? ` · ${detail}` : ""}]`,
      response.status,
      code,
      requestId,
    );
  }
  return response.json();
}
export function send<T>(
  path: string,
  body?: unknown,
  method = "POST",
): Promise<T> {
  return api<T>(path, {
    method,
    ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
  });
}
export const errorText = (e: unknown) =>
  e instanceof Error ? e.message : "Có lỗi, vui lòng thử lại";
