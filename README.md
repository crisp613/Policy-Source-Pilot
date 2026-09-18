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

## 四川省经信厅前 10 页正文采集

三个网站现在共用同一个采集引擎，推荐使用统一入口：

```bash
python3 scripts/crawl_policy_source.py --source sc-jxt
python3 scripts/crawl_policy_source.py --source sc-kjt
python3 scripts/crawl_policy_source.py --source most-service
```

可选来源为 `sc-jxt`、`sc-kjt` 和 `most-service`。默认均采集前 10 页、使用
`0.2` 秒请求间隔并启用断点续传。原来的三个独立命令继续保留，作为兼容入口。

采集通知列表前 10 页及对应详情页的纯文本正文：

```bash
python3 scripts/crawl_sc_jxt.py
```

默认单线程运行，相邻远程请求最小间隔为 `0.2` 秒。结果写入
`local-artifacts/sc-jxt-notices/first-10-pages/`：

- `lists/`：前 10 页原始列表 HTML；
- `details-html/`：详情页原始 HTML；
- `lists.json`：去重后的列表记录；
- `details.json`：标题、日期、发布主体、纯文本正文、附件链接等解析结果；
- `summary.json`：成功和失败数量汇总。

脚本默认启用断点续传，已成功保存的页面和详情不会重复请求。当前不下载附件，
不识别正文图片，也不进行 OCR。

## 四川省科技厅前 10 页正文采集

采集通知列表前 10 页及对应详情页的纯文本正文：

```bash
python3 scripts/crawl_sc_kjt.py
```

默认使用 `0.2` 秒请求间隔并启用断点续传，结果写入
`local-artifacts/sc-kjt-notices/first-10-pages/`。其中 `details.json` 保存详情页
解析结果，`summary.json` 保存成功和失败数量汇总。当前不下载附件，不识别正文图片，
也不进行 OCR。

## 国家科技管理信息系统前 10 页正文采集

直接采集公开 iframe 列表前 10 页及对应详情页的纯文本正文：

```bash
python3 scripts/crawl_most_service.py
```

默认使用 `0.2` 秒请求间隔并启用断点续传，结果写入
`local-artifacts/most-service-notices/first-10-pages/`。其中 `details.json` 保存详情页
解析结果，`summary.json` 保存成功和失败数量汇总。当前不下载附件，不处理图片，
也不访问登录后的申报指南内容。
