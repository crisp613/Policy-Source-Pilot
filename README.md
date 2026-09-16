# Policy Source Pilot

政策信息源采集的本地证据收集工作区。

当前阶段只进行公开来源的低频访问验证、结构化样本整理、最小 HTML 夹具制作和解析测试，不接入生产数据库、正式采集器、定时任务、搜索、阅读端或推送链路。

## 目录

- `docs/technical-plan.md`：技术方案。
- `docs/validation-report.md`：第一批三个来源的验证结果与接入建议。
- `docs/source-cards/`：各官网来源卡。
- `samples/`：匿名化结构化样本。
- `scripts/`：可手动执行的验证探针。
- `tests/fixtures/policy-sources/`：最小公开 HTML 测试夹具。
- `run-records/`：两次真实运行的结果摘要。
- `evidence/`：响应哈希等可复核证据。
- `local-artifacts/`：不提交 Git 的临时原始响应。

最终连接器方案确定后，应在正式后端仓库中新建实现分支，只迁移经过审核的解析逻辑、字段定义和测试夹具，不直接合并整个验证工作区。

## 本地验证

运行固定 HTML 夹具测试，不访问互联网：

```bash
python3 -m unittest discover -s tests -v
```

使用已经保存在 `local-artifacts/` 中的响应做本地回归：

```bash
python3 scripts/sc_jxt_parser.py list \
  local-artifacts/sc-jxt-notices/list-run-01.html \
  --url 'https://jxt.sc.gov.cn/scjxt/wjfb/common_list.shtml' \
  --limit 10
```

解析器只读取本地 HTML，不发起网络请求。
