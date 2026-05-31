# Nguyên tắc kỹ thuật — Scriba

Scriba là một **Python library + CLI** (`.tex → .html` renderer, package đơn,
chạy 1 process). Không phải frontend app, không phải microservices. Vì vậy chỉ
áp dụng nhánh **Backend (per-service nội bộ)**, bỏ frontend và microservices.

## 1. Library / CLI (renderer core)

### Bắt buộc

- **SOLID** — đủ 5, đặc biệt **SRP** (module nhỏ theo domain: `tex/`, `animation/`, `core/`, `sanitize/`).
- **Clean Architecture** — domain core (`tex/`, `animation/`) ← framework/CLI (`render.py`). Core không được biết HTML template, CLI args, hay output format.
- **Dependency injection** — constructor inject (`TexRenderer(worker_pool=...)`, `Pipeline([renderers])`). Không singleton ngầm.
- **KISS, YAGNI, DRY** — extract hook/util khi lặp 3+ lần (rule of three). Không build prop/param "phòng hờ".
- **Immutability** — DTO / value object immutable (`@dataclass(frozen=True)` cho token, shape).
- **Fail loudly** — không `except: pass`. Lỗi phát ra mã (E-code: E1115, E1500…) kèm context, không nuốt im lặng.
- **Input validation tại boundary** — boundary = tex parser. Validate trước khi xử lý, fail nhanh với thông báo rõ.
- **Debug-friendly** — structured warning có mã + context, dev-only verbose log.

### Bổ sung khuyến nghị

- **OOP — polymorphism qua Protocol** — duck typing (`typing.Protocol`), inheritance hạn chế.
- **DDD nhẹ** — value object (frozen dataclass) OK. Bỏ aggregate / bounded-context (overkill cho renderer).
- **Abstraction cho I/O** — `resource_resolver`, worker pool tách phần phụ thuộc ngoài khỏi domain (tương đương repository pattern khi không có DB).

### Scriba-specific (quan trọng nhất — bản chất renderer)

- **Determinism** — cùng `.tex` → byte-identical `.html`. Khóa bằng golden test `tests/golden/examples/`. Refactor không được phá output.
- **Output security** — sinh HTML phải: escape XSS, chặn path-traversal trên `-o` (guard H1), escape filename (guard C2). `sanitize/` là tuyến cuối.
- **Process isolation** — chống global-state leak giữa các lần render bằng subprocess / worker pool. Render độc lập, không chia sẻ trạng thái.
- **Test coverage** — giữ ≥ ngưỡng `fail_under = 75` (pyproject). Golden regression bắt buộc cho thay đổi rendering.

### Không áp dụng

- **Atomic Design, CDD, FSD** — frontend-only.
- **Toàn bộ Microservices** — bounded context, database-per-service, async messaging, idempotency key, circuit breaker, HMAC queue auth, health/readiness endpoint, distributed trace. Scriba là 1 process → vô nghĩa.
- **Frontend concerns** — state separation (TanStack/Zustand/URL), design token, a11y, Core Web Vitals, anti-template. Không có UI app.
