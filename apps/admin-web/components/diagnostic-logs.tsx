"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { api, errorText } from "./api";
import { Empty } from "./shared";

type LogRow = {
  id: number;
  created_at: number;
  source: string;
  level: string;
  event: string;
  details: Record<string, string | number | boolean | string[] | null>;
};
type LogPage = {
  items: LogRow[];
  next_cursor: number | null;
  retention_days: number;
  max_events: number;
};
const eventLabels: Record<string, string> = {
  operation_started: "Bắt đầu",
  operation_completed: "Hoàn tất",
  operation_failed: "Thất bại",
  request_finished: "HTTP",
  request_failed: "Request lỗi",
  client_error: "Lỗi JavaScript",
  unhandled_rejection: "Promise lỗi",
  submission_started: "Bắt đầu xử lý bài",
  submission_finished: "Kết thúc xử lý bài",
  review_started: "Bắt đầu chấm lại",
  review_finished: "Kết thúc chấm lại",
};
export default function DiagnosticLogs({
  correlation = "",
  compact = false,
}: {
  correlation?: string;
  compact?: boolean;
}) {
  const [source, setSource] = useState("");
  const [level, setLevel] = useState("");
  const [key, setKey] = useState(correlation);
  const [model, setModel] = useState("");
  const [period, setPeriod] = useState("24");
  const [auto, setAuto] = useState(false);
  const [data, setData] = useState<LogPage | null>(null);
  const [query, setQuery] = useState(() =>
    new URLSearchParams({
      ...(correlation ? { correlation } : {}),
      since: String(Date.now() / 1000 - 86400),
    }).toString(),
  );
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const pending = useRef<AbortController | null>(null);
  const load = useCallback(
    async (before?: number) => {
      pending.current?.abort();
      const controller = new AbortController();
      pending.current = controller;
      setBusy(true);
      try {
        const rows = await api<LogPage>(
          `/admin/diagnostics?${query}${before ? `&before=${before}` : ""}`,
          { signal: controller.signal },
        );
        if (controller.signal.aborted) return;
        setData((previous) =>
          before && previous
            ? { ...rows, items: [...previous.items, ...rows.items] }
            : rows,
        );
        setError("");
      } catch (e) {
        if (!controller.signal.aborted) setError(errorText(e));
      } finally {
        if (!controller.signal.aborted) setBusy(false);
      }
    },
    [query],
  );
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- Loading state belongs to the request lifecycle.
    void load();
    return () => pending.current?.abort();
  }, [load]);
  useEffect(() => {
    if (!auto) return;
    const timer = setInterval(() => {
      if (!document.hidden) void load();
    }, 10000);
    return () => clearInterval(timer);
  }, [auto, load]);
  return (
    <section className="panel diagnostic-logs">
      <div className="section-title">
        <h2>{compact ? "Log xử lý lượt thi" : "Log hệ thống"}</h2>
        <button
          type="button"
          className="button secondary"
          disabled={busy}
          onClick={() => void load()}
        >
          Làm mới log
        </button>
      </div>
      <p className="muted">
        Log API, lỗi giao diện và tác vụ AI từ khi triển khai chức năng. Giữ tối
        đa 7 ngày hoặc 10.000 sự kiện gần nhất. Không lưu khóa API, nội dung bài
        làm hay prompt.
      </p>
      <form
        className="log-filters"
        onSubmit={(e) => {
          e.preventDefault();
          const values = new URLSearchParams();
          if (source) values.set("source", source);
          if (level) values.set("level", level);
          if (key.trim()) values.set("correlation", key.trim());
          if (model.trim()) values.set("model", model.trim());
          if (period)
            values.set(
              "since",
              String(Date.now() / 1000 - Number(period) * 3600),
            );
          const next = values.toString();
          if (next === query) void load();
          else setQuery(next);
        }}
      >
        <label>
          Nguồn log
          <select
            aria-label="Nguồn log"
            value={source}
            onChange={(e) => setSource(e.target.value)}
          >
            <option value="">Tất cả</option>
            {["API", "WEB", "AI", "WORKER"].map((x) => (
              <option key={x}>{x}</option>
            ))}
          </select>
        </label>
        <label>
          Mức log
          <select
            aria-label="Mức log"
            value={level}
            onChange={(e) => setLevel(e.target.value)}
          >
            <option value="">Tất cả</option>
            {["INFO", "WARNING", "ERROR"].map((x) => (
              <option key={x}>{x}</option>
            ))}
          </select>
        </label>
        <label>
          Mã request / tác vụ / lượt thi
          <input
            value={key}
            maxLength={200}
            onChange={(e) => setKey(e.target.value)}
          />
        </label>
        <label>
          Model (tên chính xác)
          <input
            value={model}
            maxLength={200}
            onChange={(e) => setModel(e.target.value)}
          />
        </label>
        <label>
          Khoảng thời gian
          <select value={period} onChange={(e) => setPeriod(e.target.value)}>
            <option value="1">1 giờ</option>
            <option value="24">24 giờ</option>
            <option value="168">7 ngày</option>
            <option value="">Tất cả log còn lưu</option>
          </select>
        </label>
        <button className="button" disabled={busy}>
          Lọc log
        </button>
      </form>
      <label className="log-auto">
        <input
          type="checkbox"
          checked={auto}
          onChange={(e) => setAuto(e.target.checked)}
        />
        Tự làm mới mỗi 10 giây (về trang mới nhất)
      </label>
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      {busy && <p role="status">Đang tải log…</p>}
      {data && !data.items.length && <Empty>Chưa có log phù hợp.</Empty>}
      <div className="log-events">
        {data?.items.map((row) => (
          <details key={row.id} className="log-event">
            <summary>
              <time>
                {new Date(row.created_at * 1000).toLocaleString("vi-VN")}
              </time>
              <strong>
                {row.source} · {row.level}
              </strong>
              <span>
                {eventLabels[row.event] || row.event} ·{" "}
                {row.details.stage ||
                  row.details.path ||
                  row.details.status ||
                  ""}
              </span>
              <span>
                {row.details.model || ""}{" "}
                {row.details.http_status
                  ? `HTTP ${row.details.http_status}`
                  : ""}{" "}
                {row.details.elapsed_seconds != null
                  ? `${row.details.elapsed_seconds}s`
                  : ""}
              </span>
            </summary>
            <dl>
              <dt>Sự kiện</dt>
              <dd>{row.event}</dd>
              {Object.entries(row.details).map(([name, value]) => (
                <div key={name}>
                  <dt>{name}</dt>
                  <dd>
                    {Array.isArray(value)
                      ? value.join("\n")
                      : String(value ?? "—")}
                  </dd>
                </div>
              ))}
            </dl>
          </details>
        ))}
      </div>
      {data?.next_cursor && (
        <button
          type="button"
          className="button secondary"
          disabled={busy || auto}
          onClick={() => void load(data.next_cursor!)}
        >
          Xem log cũ hơn
        </button>
      )}
    </section>
  );
}
