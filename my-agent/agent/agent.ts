// Cấu hình agent — runtime-agnostic (Claude Agent SDK / OpenAI AgentKit đều đọc được shape này).
// ponytail: config tối thiểu; tools/channels/schedules thêm khi có runtime thật cần đến.

export default {
  name: "traning-ai-builder",
  description:
    "Agent xây dựng hệ thống phân tích video + highlight AI from-scratch (luận án). " +
    "Luôn làm việc theo instructions.md + skill khớp task; không bịa endpoint/schema.",

  // Model mặc định cho task thường; task nhỏ cơ học có thể hạ xuống model rẻ hơn
  // vì instructions + skills đã thiết kế cho context nhỏ.
  model: "claude-sonnet-5",

  instructions: "./instructions.md",

  // Mỗi skill = 1 loại task, tự chứa đủ ngữ cảnh (READ-list, steps, DoD, DO-NOT).
  skills: {
    dir: "./skills/",
    routing: {
      "train/eval model AI":        "ai_training_task.md",
      "endpoint backend Go":        "backend_endpoint.md",
      "màn hình CMS React":         "cms_screen.md",
      "màn hình Client Next.js":    "client_screen.md",
      "đối chiếu UI với thiết kế":  "ui_design_review.md",
      "thêm bảng/cột/collection":   "db_migration.md",
    },
  },

  // Giới hạn an toàn cho model yếu chạy tự động.
  guardrails: {
    changeOnlyWithinTaskScope: true,
    forbidNewDependencies: true,
    forbidNewEndpoints: true,
    stopWhenContractFieldMissing: true,
  },
} as const;
