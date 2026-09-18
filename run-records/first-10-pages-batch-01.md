# 三个政策来源前 10 页批量采集记录

## 基本信息

- 运行日期：2026-09-18
- 运行方式：统一采集引擎，按来源分别执行
- 请求间隔：0.2 秒
- 并发数：1
- 采集内容：公开列表、公开详情 HTML 和纯文本正文
- 附件下载：否
- 图片识别：否
- 登录系统访问：否
- 原始响应目录：`local-artifacts/`，由 Git 忽略

## 执行命令

```bash
python3 scripts/crawl_policy_source.py --source sc-jxt
python3 scripts/crawl_policy_source.py --source sc-kjt
python3 scripts/crawl_policy_source.py --source most-service
```

实际运行发生在统一入口合并前，分别使用三个兼容入口完成；统一入口与兼容入口调用同一采集引擎，输出目录和数据结构保持一致。

## 运行结果

| 来源 ID | 列表页 | 列表条目 | 详情成功 | 详情失败 |
| --- | ---: | ---: | ---: | ---: |
| `sc-jxt-notices` | 10 | 150 | 150 | 0 |
| `sc-kjt-notices` | 10 | 150 | 150 | 0 |
| `most-service-notices` | 10 | 100 | 100 | 0 |
| **合计** | **30** | **400** | **400** | **0** |

每个来源的机器可读汇总位于：

- `local-artifacts/sc-jxt-notices/first-10-pages/summary.json`
- `local-artifacts/sc-kjt-notices/first-10-pages/summary.json`
- `local-artifacts/most-service-notices/first-10-pages/summary.json`

## 页面模板记录

- 四川省经信厅前 10 页详情均由现有 `#zoomtitl/#zoomcon` 规则解析。
- 四川省科技厅首次有 8 条链接进入 `xzgfxwj` 或 `qtwj` 页面，使用 `.articlebox/.contText`，与普通通知 `.newsTex/.newsCon` 不同；增加政策文件模板和通用兜底后，利用本地 HTML 重新解析为 150/150 成功。
- 国家科技管理信息系统直接采集公开 iframe 列表；登录后的申报指南未访问。

## 证据边界

- 本轮没有逐请求记录 HTTP 状态、响应大小和响应哈希；完整 HTML 仅保存在忽略目录。
- 本轮没有下载公开附件文件，结构化结果只保留已公开的附件名称或链接。
- 0.2 秒间隔不满足任务书规定的“请求间隔不少于 60 秒”，因此本记录只证明批量采集代码和解析覆盖，不作为第二次低频合规验证。
- 本轮没有生成新增、重复、更新和失效对比，不能据此声称来源长期稳定。
