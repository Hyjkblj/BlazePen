# Review Archive Convention

后续 review 统一存放在 `docs/reviews/` 目录。

命名规则：

- `YYYY-MM-DD_主题_review.txt`
- 主题优先使用本轮 PR 编号或前后端任务编号，例如：
  - `2026-03-19_PR-BE-04_FE-03_review.txt`
  - `2026-03-20_FE-04_review.txt`

内容要求：

- 使用 BlazePen review 标准格式输出：
  - `## 前端 Findings`
  - `## 后端 Findings`
  - `## Open Questions`
  - `## 测试缺口`
  - `## Review Summary`

执行约定：

- 后续 review 在输出给用户的同时，默认同步保存一份 `.txt` 到该目录。
- 若用户未指定文件名，则按当天日期和本轮 review 主题自动命名。
