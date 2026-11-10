"use client";
import { hasRole, roleNames } from "../components/api";
import { useEffect, useState } from "react";
import {
  AudioLines,
  ArrowRight,
  BookOpen,
  LayoutDashboard,
  LogOut,
  Users,
  ClipboardCheck,
  GraduationCap,
  ShieldCheck,
} from "lucide-react";
import { api, send, User } from "../components/api";
import { Action, Form, Field } from "../components/shared";
import Academic from "../components/academic";
import DiagnosticLogs from "../components/diagnostic-logs";
import { reportWebEvent } from "../components/api";
import Admin from "../components/admin";
import Student from "../components/student";
import GoogleLogin from "../components/google-login";
import Examination from "../components/examination";
import StorageManager from "../components/storage-manager";
import { DesktopPolicySummary } from "../components/desktop-policy";
import DesktopExit from "../components/desktop-exit";

export default function Home() {
  const [user, setUser] = useState<User | null>(null),
    [loading, setLoading] = useState(true),
    [page, setPage] = useState("dashboard"),
    [navigationVersion, setNavigationVersion] = useState(0);
  useEffect(() => {
    if (!user) return;
    const error = (event: ErrorEvent) =>
      reportWebEvent(
        "client_error",
        "/",
        "GET",
        undefined,
        undefined,
        page,
        event.error?.name || "UnknownError",
      );
    const rejection = (event: PromiseRejectionEvent) =>
      reportWebEvent(
        "unhandled_rejection",
        "/",
        "GET",
        undefined,
        undefined,
        page,
        event.reason?.name || "UnknownError",
      );
    window.addEventListener("error", error);
    window.addEventListener("unhandledrejection", rejection);
    return () => {
      window.removeEventListener("error", error);
      window.removeEventListener("unhandledrejection", rejection);
    };
  }, [user, page]);
  const navigate = (destination: string) => {
    setPage(destination);
    // A menu click always opens its root, including the currently active menu.
    setNavigationVersion((version) => version + 1);
  };
  useEffect(() => {
    api<User>("/auth/me")
      .then(setUser)
      .catch(async () => {
        try {
          const r = await send<{ user: User }>("/auth/refresh");
          setUser(r.user);
        } catch {}
      })
      .finally(() => setLoading(false));
  }, []);
  if (loading)
    return (
      <div className="loading">
        <AudioLines size={40} />
        <p>Đang mở không gian học tập…</p>
        <DesktopExit />
      </div>
    );
  if (!user)
    return (
      <main className="login-shell">
        <section className="login-story">
          <div className="brand">
            <AudioLines />
            OralAI<span>ASSESSMENT PLATFORM</span>
          </div>
          <div className="story-main">
            <span className="eyebrow">HIỂU KIẾN THỨC. LẮNG NGHE TƯ DUY.</span>
            <h1>
              Mỗi câu trả lời,
              <br />
              một góc nhìn
              <br />
              <em>sâu sắc hơn.</em>
            </h1>
            <p>
              Không gian thi vấn đáp kết nối sinh viên, giảng viên và AI — với
              tiêu chí rõ ràng và minh chứng có thể kiểm tra.
            </p>
            <div className="wave">
              {Array.from({ length: 36 }, (_, i) => (
                <i
                  key={i}
                  style={{
                    height: `${20 + Math.abs(Math.sin(i * 0.7)) * 70}px`,
                  }}
                />
              ))}
            </div>
          </div>
          <div className="story-foot">
            <ShieldCheck size={17} />
            Transcript · Rubric · Tài liệu môn học
          </div>
        </section>
        <section className="login-form">
          <DesktopExit />
          <button
            className="text-button"
            onClick={() => void window.oralDesktop?.settings?.()}
            hidden={
              typeof window === "undefined" || !window.oralDesktop?.settings
            }
          >
            Cấu hình máy chủ
          </button>
          <span className="eyebrow">CHÀO MỪNG TRỞ LẠI</span>
          <h2>Đăng nhập</h2>
          <p className="muted">
            Tiếp tục hành trình đánh giá và học tập của bạn.
          </p>
          <Form
            label="Vào không gian làm việc →"
            onSubmit={async (d) => {
              const result = await send<{ user: User }>("/auth/login", {
                username: d.get("username"),
                password: d.get("password"),
              });
              setUser(result.user);
            }}
          >
            <Field
              label="Email hoặc tên đăng nhập"
              name="username"
              placeholder="Email sinh viên hoặc tên đăng nhập được cấp"
            />
            <Field label="Mật khẩu" name="password" type="password" />
          </Form>
          <GoogleLogin onLogin={setUser} />
          {typeof window !== "undefined" && window.oralDesktop && (
            <DesktopPolicySummary />
          )}
          <p className="login-note">
            Web dành cho admin, khảo thí và giáo viên. Sinh viên sử dụng OralAI
            Desktop.
            <br />
            Liên hệ giảng viên nếu bạn cần hỗ trợ truy cập.
          </p>
          <span className="version">
            GIAI ĐOẠN 01 <b>•</b> MVP
          </span>
        </section>
      </main>
    );
  const desktop = !!window.oralDesktop;
  const isStudent = desktop && hasRole(user, "STUDENT");
  const logout = async () => {
    await send("/auth/logout");
    setUser(null);
  };
  if (!desktop && !hasRole(user, "ADMIN", "EXAM_OFFICER", "TEACHER"))
    return (
      <main className="main">
        <h1>Vui lòng sử dụng OralAI Desktop</h1>
        <p>Web chỉ dành cho admin, khảo thí và giáo viên.</p>
        <button className="button" onClick={() => void logout()}>
          Đăng xuất
        </button>
      </main>
    );
  if (desktop)
    return (
      <main className="main desktop-main">
        <header className="topbar">
          <strong>OralAI · {user.name}</strong>
          <DesktopExit />
          <button
            className="text-button"
            onClick={() => {
              if (
                window.dispatchEvent(
                  new Event("oral:backend-switch", { cancelable: true }),
                )
              )
                void logout();
            }}
          >
            Đăng xuất
          </button>
        </header>
        {isStudent ? (
          <Student />
        ) : (
          <section className="panel">
            <h1>Quản trị trên web</h1>
            <p>
              Đăng nhập website OralAI bằng tài khoản này để quản lý môn học,
              sinh viên và kỳ thi. Desktop dành cho sinh viên làm bài.
            </p>
          </section>
        )}
      </main>
    );
  const links = isStudent
    ? [{ id: "student", label: "Bài thi của tôi", icon: GraduationCap }]
    : [
        { id: "dashboard", label: "Tổng quan", icon: LayoutDashboard },
        { id: "courses", label: "Môn học", icon: BookOpen },
        { id: "exams", label: "Ngân hàng đề thi", icon: ClipboardCheck },
        ...(hasRole(user, "ADMIN", "EXAM_OFFICER")
          ? [{ id: "departments", label: "Bộ môn", icon: BookOpen }]
          : []),
        {
          id: "classes",
          label: hasRole(user, "ADMIN", "EXAM_OFFICER")
            ? "Lớp học"
            : "Lớp được phân công",
          icon: GraduationCap,
        },
        ...(hasRole(user, "ADMIN", "EXAM_OFFICER", "TEACHER")
          ? [
              {
                id: "examination",
                label: "Điều phối kỳ thi",
                icon: ClipboardCheck,
              },
            ]
          : []),
        { id: "users", label: "Người dùng", icon: Users },
        { id: "results", label: "Kết quả & xem lại", icon: ClipboardCheck },
        ...(hasRole(user, "ADMIN")
          ? [
              {
                id: "storage",
                label: "Lần thi & dung lượng",
                icon: ShieldCheck,
              },
              { id: "settings", label: "Cấu hình hệ thống", icon: AudioLines },
              { id: "logs", label: "Log hệ thống", icon: ShieldCheck },
            ]
          : []),
      ];
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <AudioLines />
          OralAI
        </div>
        <div className="workspace-label">
          KHÔNG GIAN {isStudent ? "SINH VIÊN" : "QUẢN LÝ"}
        </div>
        <nav>
          {links.map((item) => (
            <button
              key={item.id}
              className={
                page === item.id || isStudent ? "nav-item active" : "nav-item"
              }
              onClick={() => navigate(item.id)}
            >
              <item.icon size={19} />
              {item.label}
              {(page === item.id || isStudent) && <ArrowRight size={15} />}
            </button>
          ))}
        </nav>
        <div className="sidebar-note">
          <span className="status-dot" />
          Đánh giá có căn cứ
          <p>Điểm dựa trên transcript, rubric và tài liệu môn học.</p>
        </div>
        <div className="profile">
          <span className="avatar">{user.name.slice(0, 1)}</span>
          <div>
            <strong>{user.name}</strong>
            <small>{roleNames(user)}</small>
          </div>
          <button
            className="icon-button"
            aria-label="Đăng xuất"
            onClick={async () => {
              await send("/auth/logout");
              setUser(null);
            }}
          >
            <LogOut size={18} />
          </button>
        </div>
      </aside>
      <main className="main">
        <header className="topbar">
          <span>
            Nền tảng thi vấn đáp{" "}
            <span className="muted">
              / {isStudent ? "Sinh viên" : "Quản trị"}
            </span>
          </span>
          <DesktopExit />
          <span className="pill">MVP · Giai đoạn 1</span>
        </header>
        <div className="content" key={`${page}:${navigationVersion}`}>
          {isStudent && (
            <details className="role-request">
              <summary>Yêu cầu quyền khảo thí</summary>
              <p>
                Admin kiểm tra và duyệt trước khi tài khoản có quyền tổ chức kỳ
                thi.
              </p>
              <Action
                disabled={user.requested_role === "EXAM_OFFICER"}
                action={async () => {
                  await send("/auth/request-exam-officer");
                  setUser(await api<User>("/auth/me"));
                }}
              >
                {user.requested_role === "EXAM_OFFICER"
                  ? "Đang chờ admin duyệt"
                  : "Gửi yêu cầu làm khảo thí"}
              </Action>
            </details>
          )}
          {["classes", "departments"].includes(page) ? (
            <Academic key={page} user={user} page={page} />
          ) : page === "logs" && hasRole(user, "ADMIN") ? (
            <DiagnosticLogs />
          ) : page === "storage" && hasRole(user, "ADMIN") ? (
            <StorageManager />
          ) : page === "examination" && !isStudent ? (
            <Examination user={user} navigate={navigate} />
          ) : isStudent ? (
            <Student />
          ) : (
            <Admin key={page} user={user} page={page} navigate={navigate} />
          )}
        </div>
        <footer>
          OralAI <span>Học sâu hơn. Đánh giá rõ ràng hơn.</span>
        </footer>
      </main>
    </div>
  );
}
