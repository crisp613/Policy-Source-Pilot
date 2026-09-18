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
├── details.json       # 标题、日期、主体、正文和公开链接
└── summary.json       # 成功、失败和运行参数汇总
```

脚本默认复用已经保存的 HTML 和成功详情。使用 `--no-resume` 才会忽略本地缓存重新请求。

## 本地测试

固定夹具测试不会访问互联网：

```bash
python3 -m unittest discover -s tests -v
```

当前结果为 17 项测试全部通过，覆盖列表解析、相对链接、正文清洗、空字段、附件、登录边界、科技厅政策文件模板和未知模板兜底。

## 已知边界

- 当前批量输出仍是验证结构，尚未完全转换为正式 `RawFeedItem` 契约。
- 当前不下载附件文件，不执行图片 OCR。
- 国家科技管理信息系统登录后的申报指南不在采集范围内。
- 三个来源尚未全部完成任务书要求的第二次低频真实运行与增量对比。
- 出现验证码、403、412、429 或登录挑战时不得尝试绕过访问控制。

来源通过负责人审核后，应在正式后端仓库的新分支中选择性迁移解析逻辑、字段定义和测试夹具，不直接把本验证工作区作为生产采集器启用。
