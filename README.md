# Policy Source Pilot

政策信息源采集的本地证据收集工作区。

当前阶段只进行公开来源的低频访问验证、结构化样本整理、最小 HTML 夹具制作和解析测试，不接入生产数据库、正式采集器、定时任务、搜索、阅读端或推送链路。

## 目录

- `docs/technical-plan.md`：技术方案。
- `docs/source-cards/`：各官网来源卡。
- `samples/`：匿名化结构化样本。
- `scripts/`：可手动执行的验证探针。
- `tests/fixtures/policy-sources/`：最小公开 HTML 测试夹具。
- `run-records/`：两次真实运行的结果摘要。
- `evidence/`：响应哈希等可复核证据。
- `local-artifacts/`：不提交 Git 的临时原始响应。

最终连接器方案确定后，应在正式后端仓库中新建实现分支，只迁移经过审核的解析逻辑、字段定义和测试夹具，不直接合并整个验证工作区。
