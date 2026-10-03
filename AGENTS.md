# AGENTS.md · adsproject 仓库约定

本文件只覆盖 `nothing793/adsproject` 这个仓库的行为约定，已纳入 git 追踪，改动需要 admin 评审（见根目录 `CODEOWNERS`）。通用约定（WSL/Linux 环境、git 与安装操作需先获同意、文档同步、隐藏内容审计等）见上级 `~/AGENTS.md`；两者冲突时按更严格的一条执行，并立即向用户说明冲突点。

## 0. 阅读顺序

动手前按顺序读完：根目录 `readme.md` → 目标 `prN/readme.md` → 相关目录的 `README.md`（如 `prN/code/README.md`）。根 `readme.md` 是本仓库的最高公约，本文件只做补充。

## 1. 身份与权限

- admin：nothing793（陈昱年）——可修改本仓库任何文件。
- collaborator：believeSong55（宋诗雨）、uwindow（王宇轩）——只能修改 `prN/` 下的文件，以及根 `readme.md` 第 1 节项目索引。
- 遇到「仅 admin 可做」的操作（修改根 `readme.md`、`AGENTS.md`、`CODEOWNERS`、`.gitignore` 白名单，裁决 readme 冲突条款）：先停下，请用户提供 GitHub 账户名；确认是 `nothing793` 后才继续。若用户不是 `nothing793`，提醒其联系 admin，不要代为执行。
- 权限不明确时一律先问，不得自行放宽或「顺手」代执行。

## 2. 工作流程

1. **只读先行**：先读完相关文档与代码，再提方案。
2. **先方案后动手**：列出要改的文件、改动内容、影响与验证方式，等用户明确批准后再执行。
3. **执行后回报**：给出改动文件清单与验证结果（编译输出、测试结果），不得只写「已完成」。
4. **git 与安装**：任何 git 操作（含 `status`、`diff`、`log` 等只读命令）与任何安装类操作，都必须先说明目的与影响并取得同意；`git push` 时必须逐条说明改动了什么。

## 3. 文件与提交规范

- 目录结构、`code` / `documentation` / `testresult` / `readme` 的要求，以及追踪（上传）范围，以根 `readme.md` 第 3、4 节为准，本文件不重复。
- 拉取范围见根 `readme.md` 第 5 节：默认只同步 `code/`、`documentation/`、`prN/readme.md` 与仓库级公约文件，`testresult/` 按需拉取。
- readme 未规定的产物：放 `prN/testresult/`，并在提交说明中注明。
- 新建文件夹必须同时创建 `README.md`；文件夹内容变化后同步更新；新增或修改文档一律使用中文。

## 4. 测试与验证

- 本仓库没有 npm 工程（无 `package.json`），上级约定中的 `npm test` / `npm run lint` 在此不适用；等价要求是：改动 C 代码后按 gcc 标准（`-std=c99 -O2 -Wall -Wextra -Wpedantic`）零告警编译，并重跑对应测试。
- pr1 验证入口在 `pr1/code/tests/`：`run_extended.py`（全集建索引、独立对拍、查询与边界回归）、`run_bonus.py`（Bonus 压力实验）、`sweep.py`（θ / τ 敏感性表）。首次全集建索引需要数分钟。
- 改动 `pr1/code/index.h`（索引格式、加载校验、落盘）后，必须重跑编解码往返 `cmp` 与独立对拍 `brute_check.py`。
- 汇报时区分「已实测」与「估算 / 未验证」，不把估算写成实测结论。

## 5. 文档同步

- 改动 code 的设计或行为后，同步 `prN/readme.md`、`prN/code/README.md` 与报告 Chapter 2；测试完成后补充 Chapter 3。
- 修改公共工具行为时，同步 `docs/` 目录（如存在）中的相关文档。
