# MarketLag 项目设计 Review 报告

## 总体评价

**项目概念**: ⭐⭐⭐⭐⭐ 优秀 - 清晰、有实际价值、适合学习Flink
**设计完整性**: ⭐⭐⭐ 中等 - 核心思路清晰，但技术细节缺失较多
**可执行性**: ⭐⭐⭐ 中等 - 需要补充大量实现细节才能开始开发

---

## 一、表述不清楚的地方

### 1.1 数据源到Kafka的接入方式不明确

**问题位置**: 第四章"整体工程架构"

**问题描述**:
- 架构图显示 `[RSS.app] → Kafka SaaS` 和 `[Polymarket APIs] → Kafka SaaS`
- 但**没有说明**如何从RSS.app和Polymarket API接入到Kafka
- 是写Python脚本轮询？使用Kafka Connect？还是其他方式？

**建议补充**:
```
数据接入层：
- RSS.app → Python脚本（定期拉取RSS feed）→ Kafka Producer → rss.events
- Polymarket API → Python脚本（每小时REST调用）→ Kafka Producer → polymarket.price_hourly
- 或者：使用Kafka Connect HTTP Source Connector（如果可用）
```

### 1.2 Flink Job之间的数据流关系不清晰

**问题位置**: 第六章"Flink 中做什么"

**问题描述**:
- 列出了3个Job，但没有说明：
  - 这3个Job是**独立的**还是**有依赖关系**？
  - Job 1的输出是否作为Job 3的输入？
  - Job 2的输出如何与Job 1的输出join？
  - 数据流是：`Job1 + Job2 → Job3` 还是 `Job1 → Job3` 和 `Job2 → Job3` 并行？

**建议补充**:
```
数据流关系：
- Job 1: rss.events → (1h window) → rss.signals_hourly (输出到新topic或直接作为中间流)
- Job 2: polymarket.price_hourly → (标准化) → polymarket.price_normalized (输出到新topic或中间流)
- Job 3: rss.signals_hourly + polymarket.price_normalized → (join + lag detection) → lag_signals
```

### 1.3 关键术语定义不明确

**问题位置**: 多处

**问题描述**:
- `keyword_score` - 如何计算？是关键词出现次数？还是加权分数？
- `source_weighted_signal` - source_weight如何定义？Reuters=1.0，其他=0.5？
- `明显上升` - 具体阈值是多少？signal_delta > 1.0？还是相对于baseline的百分比？
- `变化很小` - price_delta < 0.01？还是 < 1%？
- `confidence` - 如何计算？基于什么指标？

**建议补充**:
```
关键指标定义：
- keyword_score = sum(keyword_weight × occurrence_count) for each keyword
  - Fed=2.0, rate=1.5, hike=2.0, dovish=-1.5 (负值表示降低概率)
- source_weight: Reuters=1.0, Bloomberg=0.9, 其他=0.7
- source_weighted_signal = sum(article_score × source_weight) / count
- 明显上升: signal_delta > 1.0 或 > baseline的50%
- 变化很小: |price_delta| < 0.02 (2%)
- confidence = f(signal_strength, price_stability, time_window)
```

---

## 二、缺失的关键部分

### 2.1 数据接入层设计缺失

**缺失内容**:
- RSS.app API的具体调用方式（REST endpoint、认证、rate limit）
- Polymarket API的具体endpoint、认证方式、rate limit
- 如何将API响应转换为Kafka消息的schema设计
- 错误处理和重试机制
- 数据去重策略（RSS可能重复推送）

**建议补充章节**:
```markdown
## 数据接入层设计

### RSS.app 接入
- API: https://api.rss.app/v1/feeds/{feed_id}/items
- 认证: API Key in header
- 轮询频率: 每15分钟（避免rate limit）
- Schema转换: RSS item → Kafka message
- 去重: 基于published_at + title的hash

### Polymarket API 接入
- Market Metadata: GET /markets/{slug}
- Price Data: GET /markets/{slug}/prices
- 轮询频率: 每小时（整点）
- Schema: 直接映射到Kafka message
```

### 2.2 Flink Job详细设计缺失

**缺失内容**:
- 每个Job的具体代码结构（Java/SQL/Python的选择）
- Watermark策略（如何处理延迟数据）
- State backend选择（RocksDB？）
- Checkpoint配置
- 并行度设置
- 错误处理和side outputs

**建议补充**:
```markdown
### Job 1 详细设计
- 语言: Flink SQL (Table API)
- Watermark: 允许5分钟延迟
- State: 不需要keyed state（窗口聚合）
- 输出: 写入新topic `rss.signals_hourly`

### Job 2 详细设计
- 语言: Flink SQL
- Keyed by: market_slug|outcome
- State: 需要保存上一小时价格（ValueState）
- 输出: 写入新topic `polymarket.price_normalized`

### Job 3 详细设计
- 语言: Java (ProcessFunction) - 需要复杂join逻辑
- Join: Interval join (1小时窗口)
- State: 保存RSS signal和price的历史（MapState）
- 输出: lag_signals topic + side output for alerts
```

### 2.3 输出和存储设计缺失

**缺失内容**:
- lag_signals输出到哪里？（Kafka topic？数据库？文件？）
- 如何展示结果？（Dashboard？API？）
- 是否需要持久化存储历史数据？
- 数据保留策略

**建议补充**:
```markdown
## 输出和存储设计

### 输出目标
1. Kafka topic: `lag_signals` (实时流)
2. PostgreSQL表: `lag_signals_history` (持久化，用于分析)
3. Grafana Dashboard (可视化)

### 数据保留
- Kafka: 7天
- PostgreSQL: 90天（可配置）
```

### 2.4 监控和运维设计缺失

**缺失内容**:
- 如何监控Flink job健康状态？
- 如何监控数据延迟？
- 如何监控Kafka lag？
- 告警策略（什么时候需要人工介入？）
- 故障恢复策略

**建议补充**:
```markdown
## 监控和运维

### 关键指标
- Flink: checkpoint成功率、背压、state size
- Kafka: consumer lag、throughput
- 业务: lag信号数量、false positive rate

### 告警
- Flink job失败
- Kafka consumer lag > 1小时
- 数据源API失败 > 3次
```

### 2.5 测试策略缺失

**缺失内容**:
- 如何测试Flink jobs？
- 测试数据如何生成？
- 如何验证lag detection的准确性？
- 单元测试、集成测试策略

**建议补充**:
```markdown
## 测试策略

### 测试数据
- 使用历史RSS数据和Polymarket价格数据
- 人工构造lag场景（已知信息发布但价格未变化的时间点）

### 测试方法
- Flink本地测试（LocalEnvironment）
- 集成测试（embedded Kafka）
- 准确性验证（对比已知lag事件）
```

---

## 三、设计不合理的地方

### 3.1 架构图中的"Kafka SaaS"表述不准确

**问题位置**: 第四章架构图

**问题描述**:
- 写"Kafka SaaS"容易让人误解为使用云服务（如Confluent Cloud）
- 实际上可能是自建Kafka或本地Kafka
- 应该明确说明Kafka的部署方式

**建议修改**:
```
[RSS.app]                [Polymarket APIs]
    |                         |
    v                         v
Python Producers        Python Producers
    |                         |
    v                         v
Kafka Cluster          Kafka Cluster
(rss.events)        (polymarket.price_hourly)
        \               /
         \             /
          v           v
            Apache Flink
```

### 3.2 小时级刷新可能错过重要事件

**问题位置**: 第二章MVP场景

**问题描述**:
- 美联储相关新闻可能在任意时间发布（不一定是整点）
- 如果只在整点检查，可能错过关键信息
- 建议：RSS应该实时或近实时（5-15分钟），只有Polymarket价格可以小时级

**建议修改**:
```
刷新频率：
- RSS事件: 实时/近实时（15分钟轮询或Webhook）
- Polymarket价格: 小时级（整点拉取）
- Lag检测: 每小时计算一次（但基于实时RSS数据）
```

### 3.3 Job设计可能过于简化

**问题位置**: 第六章

**问题描述**:
- Job 1只做简单聚合，但keyword matching应该在接入层就做，而不是在Flink中
- Job 2和Job 3可以合并（价格标准化和lag检测可以在一起）
- 3个Job可能增加不必要的复杂度

**建议优化**:
```
方案A（推荐）:
- Job 1: RSS事件预处理 + 小时聚合（包含keyword matching）
- Job 2: 价格标准化 + Lag检测（合并）

方案B（更简单）:
- 单一Flink Job: 同时处理RSS和价格流，直接输出lag signals
```

### 3.4 缺少数据质量保障

**问题描述**:
- 没有考虑RSS数据缺失的情况
- 没有考虑Polymarket API失败的情况
- 没有数据验证（schema validation）
- 没有处理异常数据（价格超出[0,1]范围等）

**建议补充**:
```markdown
## 数据质量保障

### 数据验证
- RSS: 验证published_at格式、title非空
- Polymarket: 验证price ∈ [0,1]、timestamp有效

### 异常处理
- API失败: 重试3次，失败后记录到dead letter queue
- 数据缺失: 使用上一小时的数据（对于价格）或跳过（对于RSS）
- 异常值: 记录日志，不中断处理
```

### 3.5 时区处理不明确

**问题描述**:
- RSS的published_at和Polymarket的event_time可能在不同时区
- 小时对齐需要统一时区（建议UTC）
- 文档中没有明确说明

**建议补充**:
```
时区处理：
- 所有时间戳统一转换为UTC
- 小时对齐基于UTC时间
- 在Kafka message中明确标注时区
```

---

## 四、需要补充的章节

### 4.1 技术栈选择

```markdown
## 技术栈

### 数据接入
- Python 3.9+ (requests, kafka-python)
- 或: Kafka Connect HTTP Source

### 流处理
- Apache Flink 2.2.0
- Java 11+ (核心逻辑)
- Flink SQL (简单聚合)
- PyFlink (可选，用于NLP处理)

### 消息队列
- Apache Kafka 3.x
- 或: Confluent Cloud (如果使用SaaS)

### 存储
- PostgreSQL (历史数据)
- 或: TimescaleDB (时序数据优化)

### 可视化
- Grafana (实时dashboard)
- 或: 简单Web UI
```

### 4.2 开发计划

```markdown
## 开发计划（4周）

### Week 1: 数据接入
- RSS.app API集成
- Polymarket API集成
- Kafka producers实现
- 数据验证和测试

### Week 2: Flink Job开发
- Job 1: RSS聚合
- Job 2: 价格处理
- 本地测试

### Week 3: Lag检测和集成
- Job 3: Lag检测逻辑
- 端到端测试
- 准确性验证

### Week 4: 完善和文档
- 监控和告警
- Dashboard
- 文档和演示准备
```

### 4.3 风险评估

```markdown
## 风险评估

### 技术风险
- Polymarket API变更 → 需要适配层
- RSS.app服务中断 → 需要备用数据源
- Flink state过大 → 需要state TTL

### 业务风险
- Lag信号可能不准确（false positive）
- 市场可能已经反应（false negative）
- 需要人工验证信号有效性

### 缓解措施
- 实现confidence score
- 记录所有信号供后续分析
- 建立反馈机制（标记信号准确性）
```

---

## 五、优先级建议

### 🔴 高优先级（必须补充）
1. ✅ 数据接入层详细设计（如何从API到Kafka）
2. ✅ Flink Job之间的数据流关系
3. ✅ 关键指标的计算公式和阈值定义
4. ✅ 输出和存储设计
5. ✅ 时区处理策略

### 🟡 中优先级（建议补充）
1. Flink Job详细设计（watermark、state、checkpoint）
2. 监控和运维设计
3. 数据质量保障
4. 测试策略

### 🟢 低优先级（可以后续补充）
1. 性能优化
2. 扩展性设计
3. 安全设计

---

## 六、总体建议

### 优点
1. ✅ 项目概念清晰，有实际价值
2. ✅ MVP范围合理，不会过于复杂
3. ✅ 技术选型合理（Flink + Kafka）
4. ✅ 考虑了成本和工程复杂度

### 需要改进
1. ⚠️ 技术细节缺失较多，需要补充才能开始开发
2. ⚠️ 数据流设计不够清晰
3. ⚠️ 缺少运维和监控考虑
4. ⚠️ 部分设计可能需要优化（Job拆分、刷新频率）

### 下一步行动
1. 补充数据接入层设计
2. 明确Flink Job的数据流关系
3. 定义所有关键指标的计算方式
4. 设计输出和存储方案
5. 制定开发计划和时间表

---

## 总结

这是一个**概念优秀但需要补充技术细节**的项目设计。核心思路清晰，适合学习Flink，但需要补充大量实现细节才能开始开发。建议按照优先级逐步补充缺失部分，特别是数据接入层和Flink Job的详细设计。

**可执行性评分**: 6/10（补充关键缺失部分后可提升到8/10）

