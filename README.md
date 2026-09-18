# Policy Source Pilot

三个公开政策信息源的采集可行性验证工作区。项目用于确认公开列表、详情正文和附件信息能否取得，并为后续正式连接器设计提供解析逻辑、测试夹具和运行证据。

当前不接入生产数据库、定时任务、正式阅读端或推送链路，也不访问登录后的申报系统。

## 当前状态

截至 2026-09-18，三个来源均已完成首轮低频验证，并额外完成前 10 页纯文本批量采集：

| 来源 | 列表页 | 去重详情 | 详情成功 | 失败 | 采集方式 |
| --- | ---: | ---: | ---: | ---: | --- |
| 四川省经济和信息化厅 | 10 | 150 | 150 | 0 | HTTP 直采 |
| 四川省科学技术厅 | 10 | 150 | 150 | 0 | HTTP 直采，多详情模板适配 |
| 国家科技管理信息系统 | 10 | 100 | 100 | 0 | HTTP 直采公开 iframe |
| **合计** | **30** | **400** | **400** | **0** | 纯文本正文 |

批量结果位于被 Git 忽略的 `local-artifacts/<source-id>/first-10-pages/`。附件始终只保留官方链接，不下载也不解析；正文图片可按需临时 OCR，不保存图片文件。

> 任务书要求正式验证请求间隔不少于 60 秒。上述批量采集按后续开发要求使用了 0.2 秒间隔，只能作为功能与解析覆盖证据，不能替代任务书要求的低频第二次真实运行。

## 代码结构

- `scripts/policy_source_crawler.py`：公共 HTTP 请求、限速、分页、断点续传、落盘和错误记录。
- `scripts/source_status.py`：生成信息源导航页使用的来源级运行状态。
- `scripts/search_product_data.py`：对导出的产品数据进行关键词检索、筛选、排序、分页和详情读取。
- `scripts/export_product_data.py`：聚合三个来源，生成搜索、详情和信息源导航数据。
- `scripts/serve_product_api.py`：以本地只读 HTTP 接口提供列表、详情和信息源导航数据。
- `scripts/image_ocr.py`：对公开正文图片执行临时 OCR，不落盘图片。
- `scripts/run_comparison.py`：比较两次采集，输出新增、重复、更新、失效和失败。
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

已有完整缓存时，可使用 `--offline` 只执行解析和字段迁移。该模式不会访问网络，任一缓存缺失都会立即停止：

```bash
python3 scripts/crawl_policy_source.py --source sc-jxt --offline
```

需要识别公开正文图片时，追加 `--image-ocr`。脚本通过本机 `tesseract` 的标准输入处理图片，不保存图片文件；未安装该工具时，记录 `unavailable` 状态而不影响纯文本正文采集：

```bash
python3 scripts/crawl_policy_source.py --source sc-jxt --image-ocr
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
├── summary.json       # 成功、失败和运行参数汇总
├── source-status.json # 来源级运行状态和最近成功时间
└── run-comparison.json # 与上次详情结果的新增、重复、更新、失效和失败对比
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
    "document_number": "川经信办函〔2026〕321号",
    "document_number_evidence": "正文开头文号：川经信办函〔2026〕321号",
    "document_number_source": "body_opening",
    "document_number_status": "provided",
    "information_type": "申报通知",
    "information_type_evidence": "标题包含“申报”",
    "information_type_rule": "title_application_notice",
    "deadline": "2026-10-14T18:00:00+08:00",
    "deadline_evidence": "申报截止时间为2026年10月14日18:00",
    "deadline_status": "provided",
    "deadlines": [],
    "attachments": [{"name": "官方附件", "url": "https://...", "file_type": "pdf", "access": "public_link", "downloaded": false, "content_indexed": false}],
    "images": [{"url": "https://...", "alt": "正文图片", "ocr_status": "processed", "ocr_text": "图片识别结果"}],
    "image_ocr_status": "processed",
    "application_links": [],
    "collected_at": "采集时间",
    "status": "ok"
  }
}
```

来源未明确提供的单值字段写为 `null`，列表字段写为空数组，不使用推断值补齐。发布主体优先采用正文落款，其次采用页面发布单位；只有明确的完整机构名称才能从信息来源提升为发布主体，内部处室仍保留在 `info_source`。文号优先采用页面文号字段，其次采用标题文号；正文只接受开头出现的标准文号，避免把引用文件文号误认为当前文件文号。信息类型只根据标题或正文中的明确关键词划分为申报通知、公示、政策文件、征集或事务通知，同时保存命中证据和规则；无法确认时保持 `null`。截止日期只从截止、申报、受理、报送、推荐或公示期等明确上下文提取；`deadline` 用于列表展示，`deadlines` 保留全部时间节点，`deadline_status` 区分 `provided`、`not_provided` 和 `parse_failed`。`lists.json` 也统一包含来源、标题、详情地址、发布日期及证据、采集时间、页码和发布单位字段。已有旧版 `details.json` 在断点续传时会自动转换为新结构，不需要重新请求网页。

`source-status.json` 独立保存产品信息源导航页所需的来源名称、栏目、官网地址、采集方式、运行状态、最近运行时间、最近成功时间、收录数量、失败数量和连续异常运行次数。全部详情成功时为 `normal`，部分详情失败时为 `partial`，列表失败或没有成功详情时为 `failed`；遇到 403、412、429 时为 `blocked` 并立即停止该来源。5xx 最多退避重试两次，超时和其他网络错误会记录失败原因。

每次运行还生成 `run-comparison.json`：`new`（新增）、`repeated`（内容未变）、`updated`（同一原文地址内容变化）、`invalid`（上次存在、本次列表缺失）和 `failed`（本次详情失败）。

## 产品数据导出

三个来源完成标准化后，运行：

```bash
python3 scripts/export_product_data.py
```

生成的本地产品数据位于被 Git 忽略的 `product-data/`：

```text
product-data/
├── policies.json  # 400条搜索列表与详情数据、摘要和筛选统计
└── sources.json   # 3个信息源的导航与运行状态
```

`policies.json` 按发布日期倒序保存标题、摘要、正文、发布主体、层级、条线、信息类型、截止日期、文号、附件及官方链接，并包含本站收录时间、采集方式、正文图片 OCR 状态和全部截止日期节点。附件不会下载或进入搜索索引。`sources.json` 汇总各来源的 `source-status.json`。

可直接用查询脚本验证原型的搜索列表和详情页数据需求：

```bash
python3 scripts/search_product_data.py --query "人工智能" --type 申报通知 --page-size 10
python3 scripts/search_product_data.py --level 四川省 --department 科技 --sort deadline_asc
python3 scripts/search_product_data.py --query "研发" --title-only --date-range 30d --sort relevance
python3 scripts/search_product_data.py --detail <记录ID>
```

列表查询支持标题、正文和文号的关键词检索，可按发布层级、部门条线、信息类型、来源和发布日期筛选，并支持近 30 天/3 个月/12 个月快捷日期、相关性/发布日期/截止日期排序与分页。`--title-only` 只匹配标题；返回的高亮字符区间由页面安全渲染。列表结果不重复输出正文；使用 `--detail` 才读取该记录的完整详情。

页面可启动只读本地接口：

```bash
python3 scripts/serve_product_api.py
```

接口为 `GET /api/policies`、`GET /api/policies/<记录ID>` 和 `GET /api/sources`；列表参数使用 `q`、`title_only`、`level`、`department`、`type`、`source`、`date_range`、`sort`、`page` 与 `page_size`。

## 本地测试

固定夹具测试不会访问互联网：

```bash
python3 -m unittest discover -s tests -v
```

当前结果为 69 项测试全部通过，覆盖产品数据聚合、统一输出结构、附件仅链接、正文图片 OCR 内存处理、图片 OCR 跳过策略、来源正常／部分异常／失败／阻止状态、403/412/429 停止、5xx 退避、关键词检索、仅标题、快捷日期、相关性、高亮区间、条件筛选、排序分页、详情与本地 API、跨次新增/重复/更新/失效/失败对比、发布主体优先级、文号字段和正文开头提取、五类信息分类及优先级、截止日期和时间区间、列表解析、相对链接、正文清洗、空字段、附件、登录边界、科技厅政策文件模板和未知模板兜底。

## 已知边界

- 当前批量输出已转换为 `RawFeedItem` 兼容结构，但仍未注册为正式连接器。
- 附件只保留官方链接，不下载、不解析且不进入搜索；正文图片 OCR 需要本机安装 `tesseract` 后显式启用 `--image-ocr`。
- 国家科技管理信息系统登录后的申报指南不在采集范围内。
- 三个来源尚未全部完成任务书要求的第二次低频真实运行；增量对比逻辑已具备，需在第二次真实运行后形成正式证据。
- 出现验证码、403、412、429 或登录挑战时不得尝试绕过访问控制。

来源通过负责人审核后，应在正式后端仓库的新分支中选择性迁移解析逻辑、字段定义和测试夹具，不直接把本验证工作区作为生产采集器启用。
