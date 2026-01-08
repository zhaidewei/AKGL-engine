1. 锚定版本，kafka 3.7.2， Flink 2.2.0
2. 加入本地开发测试环境搭建的设计，基于docker compose，macOS
3. 加入Github 设计，几个repo，CICD到各个托管云端端设计和描述

P0（必须改，否则实现会走不通/成本判断会失真）
1) 修正 Polymarket API 端点与数据流（当前写法不准确）

问题：文档写 GET /markets/{slug} 与 GET /markets/{slug}/prices，且写“需要 API Key”，这与实际 Polymarket 的分层不一致。
修改要求：改为明确使用两套 API：Gamma（元数据）+ CLOB（价格）。

Market metadata（Gamma API）：

GET https://gamma-api.polymarket.com/markets/slug/{slug} 或

GET https://gamma-api.polymarket.com/markets?slug={slug}
从响应中提取 clobTokenIds（YES/NO token id）。

Price（CLOB API）：

推荐批量：POST https://clob.polymarket.com/prices（一次取 YES/NO）

或最小化：GET https://clob.polymarket.com/price?token_id=...&side=BUY

认证：MVP 阶段仅用 public market data endpoints，默认不依赖 API key；若未来做交易/用户数据再引入认证。
预期结果：Polymarket producer 能按 slug→token_id→price 的正确链路稳定运行。

2) 费用章节重写：不要用“Kafka $1/小时、Flink $0.50/CU/小时”这种固定数

问题：Confluent Cloud Kafka 与 Flink 的计费模型不是固定“按小时/集群”这种写法；该估算会高概率误导预算。
修改要求：把费用章节改成“计费因子 + MVP 用量假设 + 区间”。

Kafka：按 Confluent Cloud 的容量/吞吐/存储/网络计费因子描述（不写固定 $/小时）

Flink：按 CFU-minute（或平台实际计费单位）描述，不使用 CU/hour

给出区间估算，并注明以账单/定价计算器为准（按 region）。
预期结果：预算评估更可信，避免被错误高估吓退。

3) Flink Job3：把 Interval Join 改成等值 Join（window_start）

问题：当前设计写 Interval Join + ±5min 容差，但你的 price 是整点采样，RSS 也是先聚合到小时后再 join；Interval Join 增加状态复杂度且容易引入误判。
修改要求：Job3 使用等值 join：

Join key：market_slug + window_start

Join 条件：rss.signals_hourly.window_start = polymarket.price_hourly.event_time（event_time 即整点）

不再写“允许±5min”容差（除非你明确 price 可能不是整点事件）。
预期结果：逻辑更简单、状态更小、实现更直接，减少误报来源。

4) Job2（price delta）不要写成“Flink SQL + Java ProcessFunction”混合

问题：你强调“工程实现难度低”，但 Job2 引入 Java 自定义状态会显著增加部署/运维复杂度。
修改要求（任选其一，优先 A）：

A（推荐）：把 price_delta 计算放到 Polymarket Producer 侧（producer 保存上一小时值）。Flink 只做 join 与规则判断。

B（备选）：如果必须在 Flink 内计算，尽量保持纯 SQL 能实现的方式（窗口+LAG/自连接），避免 Java 自定义算子。
预期结果：MVP 部署路径更轻，不被 Java 作业打断节奏。

P1（强烈建议改，提升正确性与可扩展性）
5) RSS 去重策略：从 published_at+title 改为 link/guid 优先

问题：title 可能被编辑，published_at 也可能存在格式差异；用 published_at+title 去重容易误判重复或漏判重复。
修改要求：去重优先级改为：

item_id（若 RSS.app 提供）

link 或 guid（RSS item 常见字段）

fallback：hash(source + title + published_at)
预期结果：重复消息显著减少，同时不丢“标题被修订”的重要 breaking news。

6) Kafka topic partition key 调整（避免热点/为多市场预留）

问题：

rss.events key 用 source 只保证来源有序，不利于按 market 扩展

rss.signals_hourly key 用 window_start 会造成整点热点
修改要求：

rss.events：key 改为 market_slug（即使目前单市场，也为扩展做准备）

rss.signals_hourly：key 改为 market_slug|window_start
预期结果：后续扩展到多市场不需要重建 topic，分区更均匀。

7) Lag 规则先收敛为一个 MVP 版本（去掉 baseline 的第二套条件）

问题：当前同时写了绝对阈值与 baseline 相对阈值，会导致实现分叉与调参困难。
修改要求：MVP 只保留一个规则：

signal_delta = signal(t) - signal(t-1)

signal_delta > 1.0

abs(price_delta) < 0.02
baseline（24h 平均）留到 v4。
预期结果：实现更快，结果更可解释，调参更简单。

P2（建议改，避免后续踩坑/提升可观测性）
8) 输出/存储字段：保留 raw RSS 文本字段（title/summary）

问题：当前 rss.events schema 只保留 keywords 与 scores，后续想升级 LLM 或 debug 时缺少原始上下文。
修改要求：rss.events 增加字段：link, summary（或 content_snippet）
预期结果：更容易回溯误报原因，便于后续做语义增强。

9) Grafana SQL 修正：COUNT 按小时桶聚合

问题：GROUP BY detected_at 会按精确时间戳分组，几乎每条一组。
修改要求：改为 date_trunc('hour', detected_at) 分桶。
预期结果：Dashboard 时间序列图正常显示。
