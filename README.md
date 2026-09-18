# Policy Source Pilot

三个公开政策信息源的采集可行性验证工作区。项目用于确认公开列表、详情正文和附件信息能否取得，并为后续正式连接器设计提供解析逻辑、测试夹具和运行证据。

当前不接入生产数据库、定时任务、搜索、阅读端或推送链路，也不访问登录后的申报系统。

## 当前状态

截至 2026-09-18，三个来源均已完成首轮低频验证，并额外完成前 10 页纯文本批量采集：

| 来源 | 列表页 | 去重详情 | 详情成功 | 失败 | 采集方式 |
| --- | ---: | ---: | ---: | ---: | --- |
| 四川省经济和信息化厅 | 10 | 150 | 150 | 0 | HTTP 直采 |
| 四川省科学技术厅 | 10 | 150 | 150 | 0 | HTTP 直采，多详情模板适配 |
| 国家科技管理信息系统 | 10 | 100 | 100 | 0 | HTTP 直采公开 iframe |
| **合计** | **30** | **400** | **400** | **0** | 纯文本正文 |

批量结果位于被 Git 忽略的 `local-artifacts/<source-id>/first-10-pages/`。本轮没有下载附件文件，也没有识别图片正文。

> 任务书要求正式验证请求间隔不少于 60 秒。上述批量采集按后续开发要求使用了 0.2 秒间隔，只能作为功能与解析覆盖证据，不能替代任务书要求的低频第二次真实运行。

## 代码结构

- `scripts/policy_source_crawler.py`：公共 HTTP 请求、限速、分页、断点续传、落盘和错误记录。
- `scripts/crawl_policy_source.py`：三个来源的统一命令入口。
- `scripts/crawl_sc_jxt.py`、`crawl_sc_kjt.py`、`crawl_most_service.py`：兼容入口和各来源分页配置。
- `scripts/*_parser.py`：各来源列表和详情解析器。
- `tests/fixtures/policy-sources/`：不访问网络的最小 HTML 夹具。
- `docs/source-cards/`：来源访问证据、字段结论和正式接入建议。
- `samples/`：首轮验证的匿名化结构化样本。
- `run-records/`：真实运行范围、结果和证据边界。
- `evidence/response-hashes.jsonl`：首轮验证响应哈希。
- `local-artifacts/`：完整原始响应与批量结果，不提交 Git。

## 统一采集命令

```bash
python3 scripts/crawl_policy_source.py --source sc-jxt
python3 scripts/crawl_policy_source.py --source sc-kjt
python3 scripts/crawl_policy_source.py --source most-service
```

可选来源：

- `sc-jxt`：四川省经济和信息化厅；
- `sc-kjt`：四川省科学技术厅；
- `most-service`：国家科技管理信息系统公共服务平台。

默认参数为前 10 页、单线程、0.2 秒请求间隔和断点续传。执行任务书规定的低频验证时必须显式使用：

```bash
python3 scripts/crawl_policy_source.py --source sc-jxt --pages 1 --delay 60
```

原来的三个独立命令继续可用：

```bash
python3 scripts/crawl_sc_jxt.py
python3 scripts/crawl_sc_kjt.py
python3 scripts/crawl_most_service.py
```

## 输出目录

每个来源的输出结构一致：

```text
local-artifacts/<source-id>/first-10-pages/
├── lists/             # 原始列表 HTML
├── details-html/      # 原始详情 HTML，以 URL 的 SHA-256 命名
├── lists.json         # 去重后的列表记录
├── details.json       # 统一 RawFeedItem 兼容结构的详情记录
└── summary.json       # 成功、失败和运行参数汇总
```

脚本默认复用已经保存的 HTML 和成功详情。使用 `--no-resume` 才会忽略本地缓存重新请求。

三个来源的 `details.json` 使用相同的顶层字段：

```json
{
  "external_id": "来源 ID 与原文 URL 生成的稳定标识",
  "title": "官方原标题",
  "url": "官方详情页地址",
  "published_at": "带 +08:00 时区的 ISO 8601 时间",
  "content": "纯文本正文",
  "metadata": {
    "source_id": "来源 ID",
    "source_name": "来源名称",
    "source_level": "国家或四川省",
    "department_line": "科技或经信",
    "column_name": "公开栏目名称",
    "publisher": "四川省科学技术厅",
    "publisher_evidence": "正文落款：四川省科学技术厅",
    "publisher_source": "issuer",
    "publisher_status": "provided",
    "issuer": null,
    "publishing_unit": null,
    "info_source": null,
    "document_number": null,
    "information_type": "申报通知",
    "information_type_evidence": "标题包含“申报”",
    "information_type_rule": "title_application_notice",
    "deadline": "2026-10-14T18:00:00+08:00",
    "deadline_evidence": "申报截止时间为2026年10月14日18:00",
    "deadline_status": "provided",
    "deadlines": [],
    "attachments": [],
    "application_links": [],
    "collected_at": "采集时间",
    "status": "ok"
  }
}
```

来源未明确提供的单值字段写为 `null`，列表字段写为空数组，不使用推断值补齐。发布主体优先采用正文落款，其次采用页面发布单位；只有明确的完整机构名称才能从信息来源提升为发布主体，内部处室仍保留在 `info_source`。信息类型只根据标题或正文中的明确关键词划分为申报通知、公示、政策文件、征集或事务通知，同时保存命中证据和规则；无法确认时保持 `null`。截止日期只从截止、申报、受理、报送、推荐或公示期等明确上下文提取；`deadline` 用于列表展示，`deadlines` 保留全部时间节点，`deadline_status` 区分 `provided`、`not_provided` 和 `parse_failed`。`lists.json` 也统一包含来源、标题、详情地址、发布日期及证据、采集时间、页码和发布单位字段。已有旧版 `details.json` 在断点续传时会自动转换为新结构，不需要重新请求网页。

## 本地测试

固定夹具测试不会访问互联网：

```bash
python3 -m unittest discover -s tests -v
```

当前结果为 45 项测试全部通过，覆盖统一输出结构、发布主体优先级、内部处室排除、五类信息分类及优先级、截止日期和时间区间、资格日期排除、列表解析、相对链接、正文清洗、空字段、附件、登录边界、科技厅政策文件模板和未知模板兜底。

## 已知边界

- 当前批量输出已转换为 `RawFeedItem` 兼容结构，但仍未注册为正式连接器。
- 当前不下载附件文件，不执行图片 OCR。
- 国家科技管理信息系统登录后的申报指南不在采集范围内。
- 三个来源尚未全部完成任务书要求的第二次低频真实运行与增量对比。
- 出现验证码、403、412、429 或登录挑战时不得尝试绕过访问控制。

来源通过负责人审核后，应在正式后端仓库的新分支中选择性迁移解析逻辑、字段定义和测试夹具，不直接把本验证工作区作为生产采集器启用。
