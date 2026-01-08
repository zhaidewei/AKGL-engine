
# 项目总览

名称：MarketLag

**项目目标**：

> **利用公共高可信信息源（RSS/新闻）与 Polymarket 预测市场价格之间的时间差（information → market latency），在近实时/准实时层面识别潜在的市场低效（arbitrage / lag signals）。**

注意：

* 我们做的是 **“机会判断 / lag detection”**
* **不是自动交易系统**（这在合规、工程复杂度、产品叙事上都更合理）

---

## 一、为什么选择这个方向（而不是普通 streaming demo）

### 1️⃣ 这是一个 **streaming-only 的问题**

* Batch ETL 只能回答：

  * “过去一天发生了什么”
* 你要回答的是：

  * **“信息刚刚出现时，市场是否还没反应？”**

这正好命中 streaming 的核心价值：

* event-time
* 窗口
* 状态
* 延迟（lag）

---

### 2️⃣ 信息不对称是真实存在的

现实世界的传播顺序通常是：

```
权威信息源（官方 / 通讯社 /记者）
→ 社交/新闻扩散
→ 预测市场形成共识
```

而 **Polymarket**：

* 是概率共识的“终点”
* 但不是信息的“起点”

**中间存在可被量化的时间差**。

---

### 3️⃣ 公共数据 + 预测市场 = 低门槛 + 高价值

* 不依赖：

  * 私有数据
  * 内部交易系统
* 但：

  * 技术深度高
  * 产品叙事硬
  * 可升级、可售卖

---

## 二、我们最终选定的“最小可行场景（MVP）”

### 🎯 聚焦一个预测市场

* **主题**：1 月份美联储是否加息（Fed hike in January）
* **刷新频率**：**小时级**
* **目标**：

  * 在工程难度低的前提下
  * 验证“信息 → 市场反应”是否存在可检测的 lag

这是一个**非常理性的切口**：

* 事件驱动强
* 信息源明确
* 市场关注度高
* 不需要毫秒级交易

---

## 三、数据源选择与原因

### A. 公共信息源：RSS.app（核心信息输入）

#### 为什么不用 Twitter？

* 官方 API 昂贵、不稳定
* 第三方 API 有合规/持续性风险
* 对你这个问题来说：

  * **噪声 > 信号**

#### 为什么用 RSS？

* **成本低**（RSS.app ~$10/月）
* **信息密度高**
* **时间戳清晰**
* 非常适合：

  * 事件驱动
  * lag 分析

#### RSS.app 的角色

* 聚合：

  * Reuters
  * 其他权威新闻源
* 你不关心“谁讨论了”
* 你关心：

  > **“什么时候出现了可影响市场预期的事实/解读”**

---

### B. 市场数据源：Polymarket（结果与共识）

#### 我们使用的 Polymarket 数据类型

1. **市场元数据（低频）**

   * market slug
   * close time
   * YES / NO 对应的 token_id

2. **价格数据（小时级）**

   * 当前 YES / NO 概率
   * 通过 CLOB REST API 拉取

#### 为什么不用 WebSocket（现在）

* 小时刷新已经足够验证 lag
* REST 轮询：

  * 实现简单
  * 稳定
  * 易 debug

WebSocket 是 **后续升级项**，不是 MVP 必需。

---

## 四、整体工程架构（你现在这个阶段的“最佳复杂度”）

```
[RSS.app]                [Polymarket APIs]
    |                         |
    v                         v
Kafka SaaS              Kafka SaaS
(rss.events)        (polymarket.price_hourly)
        \               /
         \             /
          v           v
            Apache Flink
      (event-time, window, state)
                 |
                 v
        lag / arbitrage signals
```

---

## 五、Kafka Topic 设计（最小但可扩展）

### 1️⃣ `rss.events`

* key: `source`
* value:

  * title
  * published_at
  * source_weight
  * keyword hits（Fed / rate / hike / dovish 等）

### 2️⃣ `polymarket.market_meta`（低频）

* key: `market_slug`
* value:

  * question
  * close_time
  * YES/NO token_id

### 3️⃣ `polymarket.price_hourly`

* key: `market_slug|outcome`
* value:

  * price
  * event_time（小时对齐）
  * fetched_at

---

## 六、Flink 中做什么（刻意保持简单）

### Job 1：RSS 信号小时聚合

* 1h tumbling window
* 输出：

  * mention_count
  * keyword_score
  * source_weighted_signal

### Job 2：市场价格小时对齐

* 标准化 price ∈ [0,1]
* 计算：

  * Δprice（小时变化）

### Job 3：Lag / 机会判断（MVP 规则）

最简单、最可解释的定义：

> **如果在 t 小时：**
>
> * RSS signal 明显上升
> * 但 Polymarket YES price 未变化 / 变化很小
>
> ⇒ 标记为 **potential lag window**

输出：

```json
{
  "market": "fed_hike_jan",
  "window": "2026-01-07T10:00Z",
  "signal_delta": 1.6,
  "price_delta": 0.00,
  "lag_flag": true,
  "confidence": 0.72
}
```

---

## 七、为什么这个设计“工程难度低但上限很高”

### 现在的优点

* 不依赖昂贵 API
* 不涉及交易执行
* Flink 能力展示非常纯粹：

  * event time
  * window
  * state
  * join
* Demo 解释性极强

### 后续可升级路径（我们已经预留）

1. 小时 → 5 分钟 → WebSocket
2. RSS → RSS + 社交
3. 简单规则 → CEP / 统计模型
4. 单市场 → 多市场（配置驱动）
5. Off-chain → Web3 signal 订阅

---

## 八、这个项目“在你职业转型中的定位”

这不是一个：

* 教程项目
* 玩具 demo
* 简单数据管道

这是一个：

> **“面向真实市场低效问题的 streaming 信息系统”**

它能够非常自然地证明：

* 你理解 streaming 的 **本质**
* 你能做 **产品级架构取舍**
* 你能在 **成本、工程、价值**之间做判断
