# MarketLag 项目所需的知识和技能

**基于**: output_project_design_v5.md
**生成日期**: 2026-01-07
**版本**: v2

---

## 学习路径概述

本文档列出了构建 MarketLag 项目所需的知识点和技能。这些知识点按顺序排列，形成线性学习路径，其中先决条件位于依赖概念之前。每个知识点都是原子性的，专注于 20/80 原则——涵盖本项目最关键的知识。

---

## 已假设的知识 vs 需要学习的知识

### ✅ 已假设的知识（学习者已具备）
学习者是一位经验丰富的数据工程师（10 年经验），具备以下专业知识：
- **流处理基础**: Kafka、Kinesis、事件驱动架构
- **云平台**: AWS（Lambda、EventBridge、S3、DynamoDB）、GCP、Azure
- **编程语言**: Python、SQL、Java 基础、TypeScript、Scala
- **数据工程**: ETL/ELT 管道、数据质量、数据仓库
- **大数据**: Apache Spark、Hadoop 生态系统
- **DevOps**: Docker、Kubernetes、Terraform、CI/CD
- **通用概念**: 时区处理、API 集成、错误处理模式

### 📚 需要学习的知识（本路径重点关注）
- **Flink 特定**: Flink 架构、API、时间概念、状态管理
- **Flink-Kafka 集成**: Flink Kafka 连接器、Schema Registry 集成
- **Flink SQL**: Table API、SQL 语法、窗口函数、连接
- **Confluent Cloud**: 托管 Flink 部署和运维
- **项目特定**: 滞后检测算法、信号处理、置信度评分
- **运维细节**: 特定部署模式、配置示例

---

## 1. Flink 基础

### 1.1 Flink 架构和执行模型
- Flink 集群架构：JobManager、TaskManager、slots
- Flink 作业生命周期：提交、调度、执行
- 并行度和任务分配
- LocalEnvironment vs RemoteEnvironment vs Confluent Cloud 环境
- **原因**: 理解 Flink 作业如何运行以及如何部署的基础

### 1.2 Flink DataStream API 基础
- 从源创建 DataStream（Kafka、集合、文件）
- 基本转换：map、filter、flatMap、keyBy
- DataStream 链式和算子融合
- **原因**: 构建流处理管道的核心 API

### 1.3 Flink Table API 和 SQL
- Table API vs DataStream API：何时使用哪个
- 从 DataStream 创建表
- Flink SQL 语法和功能
- 注册表和视图
- **原因**: 项目在 Job 1、2 和 3 中使用 Flink SQL——主要接口

### 1.4 Flink 时间概念和时区处理
- 处理时间 vs 事件时间 vs 摄入时间
- 从记录中提取事件时间
- 时间戳分配策略
- **UTC 标准化**: 为什么使用 UTC、时区转换（本地 → UTC）、ISO 8601 格式
- **事件时间对齐**: 小时对齐、窗口对齐、时区感知处理
- **原因**: 对窗口化和滞后检测至关重要——项目使用事件时间并采用 UTC 标准化

### 1.5 Flink 中的 Watermark
- Watermark 概念：它代表什么以及为什么需要
- Watermark 生成策略：周期性、标点符号
- Watermark 在算子中的传播
- 允许延迟和延迟数据处理
- Flink SQL 中的 Watermark 配置：`WATERMARK FOR published_at AS published_at - INTERVAL '5' MINUTE`
- **原因**: 事件时间窗口化必不可少——项目使用 5 分钟 watermark 延迟

### 1.6 Flink 窗口
- 窗口类型：滚动、滑动、会话
- 滚动窗口配置和语义
- 窗口分配：事件如何分配到窗口
- 窗口函数：聚合、处理、归约
- 窗口触发器和驱逐策略
- **原因**: 项目使用 1 小时滚动窗口进行 RSS 信号聚合

### 1.7 Flink 状态类型
- ValueState：每个键的单个值
- ListState：每个键的值列表
- MapState：每个键的键值映射（在 Job 3 中用于 max_signal_delta）
- ReducingState：每个键的聚合值
- 键控状态 vs 算子状态
- **原因**: 理解状态类型有助于为每个用例选择正确的类型

### 1.8 Flink 状态后端
- 状态后端类型：MemoryStateBackend、FsStateBackend、RocksDBStateBackend
- 状态后端选择：何时使用哪个
- RocksDB 配置：内存、写缓冲区（在 Confluent Cloud 中使用）
- 状态 TTL（生存时间）配置
- **原因**: 项目在 Confluent Cloud 中使用 RocksDB 进行状态存储

### 1.9 Flink 状态访问模式
- ProcessFunction 中的状态访问：state.value()、state.get()
- 状态更新：state.update()、state.add()
- 状态初始化：检查状态是否存在
- **原因**: Job 3 需要读写 max_signal_delta 状态

### 1.10 Flink Checkpoint
- Checkpoint 概念：一致快照
- Checkpoint 配置：间隔、模式（EXACTLY_ONCE）、超时
- Checkpoint 存储：文件系统、S3 兼容（Confluent Cloud 使用 S3）
- Checkpoint 恢复：Flink 如何从 checkpoint 恢复
- Savepoint vs checkpoint
- **原因**: 对容错至关重要——项目使用 5 分钟 checkpoint

---

## 2. Flink-Kafka 集成

### 2.1 Flink Kafka 连接器
- Flink 中的 Kafka 消费者配置
- Flink 中的 Kafka 生产者配置
- Kafka 源：FlinkKafkaConsumer（已弃用）vs KafkaSource（新）
- Kafka 汇：FlinkKafkaProducer vs KafkaSink
- 消费者组管理和偏移量处理
- **原因**: 所有数据都通过 Kafka 流动——核心集成

### 2.2 Flink Kafka Table 连接器
- Flink SQL 中的 Kafka 表连接器配置
- 模式定义：格式（JSON、Avro）、Schema Registry 集成
- Kafka topic 作为 Flink 表：CREATE TABLE ... WITH (...)
- 从 Kafka 读取：SELECT FROM kafka_table
- 写入 Kafka：INSERT INTO kafka_table
- **示例 CREATE TABLE**:
  ```sql
  CREATE TABLE rss_events (
    title STRING,
    link STRING,
    published_at TIMESTAMP(3),
    source STRING,
    keywords ARRAY<STRING>,
    WATERMARK FOR published_at AS published_at - INTERVAL '5' MINUTE
  ) WITH (
    'connector' = 'kafka',
    'topic' = 'rss.events',
    'properties.bootstrap.servers' = '<confluent-cloud-endpoint>',
    'properties.security.protocol' = 'SASL_SSL',
    'properties.sasl.mechanism' = 'PLAIN',
    'properties.sasl.username' = '<api-key>',
    'properties.sasl.password' = '<api-secret>',
    'format' = 'json',
    'json.ignore-parse-errors' = 'true'
  );
  ```
- **原因**: 项目使用 Flink SQL 和 Kafka 表——主要模式

### 2.3 Schema Registry 集成
- Schema Registry 概念和目的
- Confluent Schema Registry 与 Flink 的集成
- Schema 演进和兼容性
- 使用 Schema Registry 的 Avro 格式
- 使用 Schema Registry 的 JSON Schema
- **配置**: 向表连接器添加 Schema Registry URL 和凭据
- **原因**: 项目使用 Confluent Cloud Schema Registry 进行模式管理

### 2.4 Kafka 分区和 Flink 并行度
- Kafka 分区键和 Flink keyBy 的关系
- 分区分配策略
- 并行度和分区分布
- **项目模式**: 对 `rss.events` 使用 `market_slug` 作为分区键，对 `polymarket.price_hourly` 使用 `market_slug|outcome`
- **原因**: 理解数据分布影响性能和正确性

---

## 3. Flink SQL 高级功能

### 3.1 Flink SQL 窗口函数
- TUMBLE 窗口函数语法
- 窗口聚合：COUNT、SUM、AVG over windows
- 窗口开始和结束时间提取
- 按窗口和键分组
- **示例（Job 1）**:
  ```sql
  SELECT
    market_slug,
    TUMBLE_START(published_at, INTERVAL '1' HOUR) as window_start,
    TUMBLE_END(published_at, INTERVAL '1' HOUR) as window_end,
    COUNT(*) as mention_count,
    SUM(keyword_score) as keyword_score,
    AVG(article_score * source_weight) as source_weighted_signal
  FROM rss_events
  GROUP BY market_slug, TUMBLE(published_at, INTERVAL '1' HOUR)
  ```
- **原因**: Job 1 使用 TUMBLE 窗口进行每小时 RSS 聚合

### 3.2 Flink SQL 时间连接
- 常规连接 vs 时间连接
- 事件时间时间连接（AS OF SYSTEM TIME）
- 区间连接：在时间边界内连接流
- **原因**: 理解不同的连接类型有助于选择正确的类型（项目使用等值连接，而不是区间连接）

### 3.3 Flink SQL 等值连接
- 等值连接语法：INNER JOIN、LEFT JOIN
- 连接条件：带等式的 ON 子句
- 连接性能：广播 vs 常规连接
- **示例（Job 3）**:
  ```sql
  SELECT
    r.market_slug,
    r.window_start,
    r.source_weighted_signal as rss_signal,
    p.price,
    p.price_delta,
    (r.source_weighted_signal - LAG(r.source_weighted_signal)
      OVER (PARTITION BY r.market_slug ORDER BY r.window_start)) as signal_delta
  FROM rss_signals_hourly r
  INNER JOIN polymarket_price_hourly p
  ON r.market_slug = p.market_slug
    AND r.window_start = p.event_time
  WHERE ...
  ```
- **原因**: Job 3 使用等值连接通过 market_slug + window_start 组合 RSS 信号和价格

### 3.4 Flink SQL 窗口聚合与 LAG 函数
- LAG 函数：访问前一行值
- 带 OVER 子句的 LAG：窗口化滞后计算
- 窗口函数中的 PARTITION BY 和 ORDER BY
- **原因**: Job 3 使用 LAG 计算 signal_delta（当前 - 前一个）

### 3.5 Flink SQL 用户定义函数 (UDF)
- 标量 UDF：简单转换
- 表 UDF：表值函数
- SQL 中的 UDF 注册和使用
- **原因**: 可能需要自定义函数进行置信度计算或信号处理

### 3.6 Flink SQL 时间属性
- CREATE TABLE 中的事件时间属性声明
- 处理时间属性声明
- 时间属性在查询中的传播
- **原因**: 窗口化和 watermark 生成所必需

---

## 4. Flink 有状态处理

### 4.1 ProcessFunction 用于有状态逻辑
- ProcessFunction 接口：processElement、onTimer
- KeyedProcessFunction 用于键控状态访问
- 计时器注册和触发
- **原因**: Job 3 可能需要 ProcessFunction 进行带历史状态的置信度计算

### 4.2 状态 TTL 配置
- TTL 配置：何时使状态过期
- TTL 更新策略：OnCreateAndWrite、OnReadAndWrite
- 状态清理：过期状态移除
- **示例**: 为存储 max_signal_delta 的 MapState 设置 7 天 TTL
- **原因**: 项目对历史状态使用 7 天 TTL

---

## 5. Flink 外部系统集成

### 5.1 Flink JDBC 连接器配置
- JDBC sink 配置
- 用于读写的 JDBC 表连接器
- 批量插入配置：批量大小、刷新间隔
- 连接池管理
- **Supabase 连接字符串格式**:
  ```
  jdbc:postgresql://db.<project-ref>.supabase.co:5432/postgres
  ```
- **JDBC Sink 的示例 CREATE TABLE**:
  ```sql
  CREATE TABLE lag_signals_sink (
    market VARCHAR(100),
    window TIMESTAMP,
    signal_delta DECIMAL(10, 4),
    price_delta DECIMAL(10, 4),
    lag_flag BOOLEAN,
    confidence DECIMAL(3, 2),
    detected_at TIMESTAMP
  ) WITH (
    'connector' = 'jdbc',
    'url' = 'jdbc:postgresql://db.xxx.supabase.co:5432/postgres',
    'table-name' = 'lag_signals_history',
    'username' = 'postgres',
    'password' = '<password>',
    'sink.buffer-flush.max-rows' = '100',
    'sink.buffer-flush.interval' = '10s'
  );
  ```
- **原因**: 项目通过 JDBC sink 将 lag_signals 写入 Supabase PostgreSQL

### 5.2 Flink JDBC Sink 最佳实践
- 幂等写入：UPSERT vs INSERT
- 错误处理：重试逻辑、死信处理
- 事务管理
- 处理连接失败：指数退避重试
- **原因**: 确保可靠写入 Supabase

---

## 6. Confluent Cloud Flink

### 6.1 Confluent Cloud 概述
- Confluent Cloud 架构：托管 Kafka 和 Flink
- Confluent Cloud vs 自托管：差异和优势
- Confluent Cloud 定价模型：CKU（Kafka）、CFU（Flink）
- **原因**: 项目使用 Confluent Cloud 进行生产部署

### 6.2 Confluent Cloud Flink 环境
- 在 Confluent Cloud UI 中创建 Flink 环境
- Flink 版本选择（2.2.0）
- 计算单元配置（CFU）：MVP 使用 2 CFU
- 状态后端配置（RocksDB）：在 Confluent Cloud 中自动配置
- Checkpoint 存储配置：S3 兼容存储
- **原因**: 理解部署环境

### 6.3 部署 Flink 作业到 Confluent Cloud
- **作业提交方法**:
  - UI：通过 Confluent Cloud UI 上传 JAR 或 SQL 脚本
  - CLI：使用 `confluent flink job create` 命令
  - API：用于程序化部署的 REST API
- **作业配置**:
  - 并行度：2（MVP）
  - Checkpoint 间隔：300000（5 分钟）
  - Checkpoint 模式：EXACTLY_ONCE
- **作业监控**: UI 仪表板、指标、日志
- **作业更新**: 版本控制、滚动更新
- **原因**: 部署和维护作业的运维知识

### 6.4 Confluent Cloud 监控
- Flink 作业指标：吞吐量、延迟、checkpoint 成功率
- Kafka 指标：消费者滞后、吞吐量
- 告警配置：为 checkpoint 失败、高滞后设置告警
- **原因**: 监控作业健康和性能

---

## 7. 数据源集成

### 7.1 RSS Feed 处理
- RSS feed 结构：items、title、link、published_at
- RSS 解析库：feedparser（Python）、rss-parser
- RSS 项去重策略：guid、link、hash
- 时区处理：将 published_at 转换为 UTC
- **RSS.app API**: `https://rss.app/feeds/v1.1/{feed_id}.json`
- **原因**: 项目从 RSS.app 摄取 RSS feed

### 7.2 Polymarket API 集成
- Polymarket API 架构：Gamma API vs CLOB API
- **Gamma API**: `GET https://gamma-api.polymarket.com/markets/slug/{slug}` - 市场元数据、token ID 提取
- **CLOB API**: `POST https://clob.polymarket.com/prices` 带 `{"token_ids": [...]}` - 价格数据检索
- API 认证：公共端点（MVP）
- 速率限制和错误处理
- **原因**: 项目从 Polymarket 获取市场价格

### 7.3 计算位置：Producer vs Flink
- **决策因素**: 将计算逻辑放在哪里
- **Producer 端计算**: 在 Lambda 中计算 price_delta（在 Kafka 之前）
  - 优点：减少 Flink 状态复杂性，简化 Flink 作业
  - 缺点：需要外部状态存储（DynamoDB/S3）
- **Flink 端计算**: 在 Flink 算子中计算
  - 优点：集中逻辑，Flink 状态管理
  - 缺点：更复杂的 Flink 状态，更大的状态大小
- **项目选择**: 在 Producer（Lambda）中使用 DynamoDB 存储前一个价格来计算 price_delta
- **原因**: 理解权衡有助于做出架构决策

### 7.4 价格差值计算实现
- 价格差值计算：current_price - prev_price
- 前一个价格的状态管理：DynamoDB、S3 或内存
- 首次处理：第一个数据点的 delta = 0
- **DynamoDB 模式**: 存储 `{market_slug|outcome: prev_price}` 并设置 TTL
- **原因**: 项目在 Producer（Lambda）中计算 price_delta，而不是在 Flink 中

---

## 8. AWS Lambda 和 EventBridge

### 8.1 AWS Lambda 用于数据生产者
- Lambda 函数结构：handler、依赖项
- 共享依赖的 Lambda 层：打包 kafka-python、confluent-kafka
- Lambda 环境变量和配置
- Lambda 超时和内存配置：5 分钟超时、256MB 内存
- **原因**: RSS 和 Polymarket 生产者作为 Lambda 函数运行

### 8.2 AWS EventBridge 调度
- EventBridge 规则创建：cron 表达式
- **RSS Producer Cron**: `*/15 * * * ? *`（每 15 分钟）
- **Polymarket Producer Cron**: `0 * * * ? *`（每小时的第 0 分钟）
- EventBridge 目标配置：Lambda 函数
- **原因**: 按计划触发数据生产者

### 8.3 Lambda-Kafka 集成
- Lambda 中的 Kafka 生产者：confluent-kafka、kafka-python
- **Confluent Cloud 认证**:
  ```python
  {
      'bootstrap.servers': '<confluent-cloud-endpoint>',
      'security.protocol': 'SASL_SSL',
      'sasl.mechanism': 'PLAIN',
      'sasl.username': '<api-key>',
      'sasl.password': '<api-secret>',
      'acks': 'all',
      'retries': 3,
      'enable.idempotence': True
  }
  ```
- Lambda 中的错误处理和重试逻辑
- 死信队列：失败记录处理（DLQ Kafka topics）
- **原因**: Lambda 函数写入 Confluent Cloud Kafka

---

## 9. 错误处理和数据质量

### 9.1 死信队列模式
- DLQ 概念：存储失败记录
- DLQ 实现：Kafka topic（`dlq.rss.events`、`dlq.polymarket.price_hourly`）、SQS、S3
- DLQ 监控和告警
- DLQ 记录分析和重新处理
- **原因**: 项目使用 DLQ topics 处理失败的 RSS 和 Polymarket 记录

### 9.2 流处理中的数据验证
- Schema 验证：使用 Schema Registry
- 数据范围验证：price ∈ [0,1]
- 时间戳验证：不是未来，不太旧
- 缺失字段处理：默认值、跳过记录
- **原因**: 在处理前确保数据质量

### 9.3 Flink 中的异常处理
- 算子中的 try-catch
- 错误记录的侧输出
- ProcessFunction 中的异常处理
- **原因**: 优雅处理格式错误的数据

### 9.4 项目特定的错误处理模式
- **窗口中缺少 RSS 数据**: 跳过窗口（无输出），记录警告
- **连接中缺少价格数据**: 使用 LEFT JOIN 处理缺失价格，设置 price_delta = 0
- **Lambda 中的 API 速率限制**: 指数退避重试，达到最大重试次数后记录到 DLQ
- **Schema Registry 演进**: 处理 schema 兼容性、版本管理
- **原因**: 项目中的特定错误场景

---

## 10. 测试 Flink 应用

### 10.1 Flink 本地测试
- 用于测试的 LocalEnvironment 设置
- 测试数据生成：创建测试流
- Flink 算子单元测试
- 有状态函数测试：状态验证
- **原因**: 在部署前验证逻辑

### 10.2 Flink 集成测试
- Docker Compose 设置：Kafka、PostgreSQL、Schema Registry
- 端到端测试：source → Flink → sink
- 测试数据重放：使用历史数据
- **原因**: 验证完整的数据管道

### 10.3 Flink Checkpoint 测试
- 测试 checkpoint 创建和恢复
- 模拟故障：终止任务、网络分区
- 验证状态恢复正确性
- **原因**: 确保容错工作

### 10.4 项目特定的测试场景
- **测试窗口聚合（Job 1）**: 验证 mention_count、keyword_score、source_weighted_signal 计算
- **测试连接正确性（Job 3）**: 验证等值连接正确匹配 window_start 与 event_time
- **测试状态恢复**: 验证 max_signal_delta 状态在故障后正确恢复
- **测试 Watermark 行为**: 验证延迟数据处理、使用 watermark 的窗口触发
- **测试滞后检测逻辑**: 验证 signal_delta > 1.0 AND abs(price_delta) < 0.02 正确标记滞后
- **原因**: 验证项目特定功能

---

## 11. 监控和可观测性

### 11.1 Flink 指标
- 内置指标：吞吐量、延迟、checkpoint 持续时间
- 自定义指标：注册自定义计数器、仪表
- 指标导出：Prometheus、InfluxDB
- **原因**: 监控作业性能和健康

### 11.2 Grafana 仪表板创建
- Grafana 数据源配置：PostgreSQL、Prometheus
- 面板类型：时间序列、直方图、散点图、表格
- **SQL 查询示例（每小时聚合）**:
  ```sql
  SELECT
    date_trunc('hour', detected_at) as hour,
    COUNT(*) as lag_count
  FROM lag_signals_history
  WHERE lag_flag = true
  GROUP BY date_trunc('hour', detected_at)
  ORDER BY hour
  ```
- 仪表板组织和布局
- **原因**: 项目在 Grafana 中可视化滞后信号和系统健康

### 11.3 告警配置
- Grafana 告警规则：基于阈值的告警
- 告警通知渠道：电子邮件、Slack
- 告警评估和触发
- **项目告警**: 滞后信号计数 = 0（意外）、Flink 作业失败、高消费者滞后
- **原因**: 收到系统问题或异常的通知

---

## 12. 项目特定概念

### 12.1 滞后检测算法
- 信号差值计算：signal(t) - signal(t-1)
- 价格差值比较：abs(price_delta) < threshold (0.02 = 2%)
- 滞后标志逻辑：signal_delta > 1.0 AND abs(price_delta) < 0.02
- **原因**: 项目的核心业务逻辑

### 12.2 置信度分数计算公式
- **公式**:
  ```
  confidence = min(1.0,
    (signal_delta / max_signal_delta) * 0.5 +
    (1 - |price_delta|) * 0.3 +
    (source_weight_avg) * 0.2
  )
  ```
- 因子归一化：缩放到 [0,1] 范围
- 历史基线：使用 max_signal_delta 进行归一化（存储在 MapState 中）
- **原因**: 量化滞后信号的可靠性

### 12.3 关键词评分系统
- 关键词权重：正面（Fed=2.0、rate=1.5、hike=2.0）vs 负面（dovish=-1.5）
- 关键词出现计数
- 关键词分数聚合：每篇文章的 SUM(weight × count)
- **原因**: 将 RSS 内容转换为数值信号

### 12.4 源权重和信号计算
- 源可信度权重：Reuters=1.0、Bloomberg=0.9、其他=0.7
- 文章分数：该文章的关键词分数之和
- 源加权信号：每个窗口的 SUM(article_score × source_weight) / COUNT(*)
- **公式**: `source_weighted_signal = AVG(article_score × source_weight)`
- **原因**: 在信号计算中考虑源可靠性

### 12.5 连接类型选择：等值连接 vs 区间连接
- **等值连接**: 连接键上的精确匹配（market_slug + window_start = event_time）
  - 在项目中使用：window_start 和 event_time 都对齐到 UTC 小时
  - 优点：简单、高效、精确匹配
- **区间连接**: 在时间边界内连接（例如，±5 分钟）
  - 项目中未使用：数据已对齐到小时
  - 优点：处理轻微不对齐
- **决策因素**: 数据对齐——如果数据已预对齐，等值连接更好
- **原因**: 理解何时使用哪种连接类型

---

## 13. 运维知识

### 13.1 Flink 作业部署工作流
- 代码编译：Maven/Gradle 构建
- JAR 打包：包含依赖项（fat JAR）
- 作业提交：CLI、UI、API
- 作业配置管理：环境特定配置
- **原因**: 将作业部署到 Confluent Cloud

### 13.2 Flink 作业故障排除
- 常见问题：checkpoint 失败、背压、OOM
- 调试技术：日志、指标、UI 检查
- 性能调优：并行度、状态后端、checkpoint 间隔
- **原因**: 维护健康的生产作业

### 13.3 成本优化和资源规划
- Confluent Cloud 成本因素：CKU、CFU、存储、网络
- **CFU 估算**: MVP 使用 2 CFU（基于数据量 < 1 MB/s）
- 成本监控：在 Confluent Cloud UI 中跟踪使用情况和支出
- 优化策略：正确调整大小、数据保留调优（7-30 天）
- **成本告警**: 设置计费告警
- **原因**: 在预算内管理项目成本（MVP 为 $775-1,293/月）

---

## 14. 高级主题（可选但有用）

### 14.1 Flink CEP（复杂事件处理）
- 模式定义：检测事件序列
- 模式匹配：检测滞后模式
- **原因**: 滞后检测的替代方法（MVP 中未使用）

### 14.2 Flink 异步 I/O
- 用于外部查找的 AsyncFunction
- 异步 I/O 配置：容量、超时
- **原因**: 如果需要使用外部 API 丰富数据

---

## 学习序列摘要

**阶段 1: Flink 基础（第 1-5 天）**
- 1.1-1.3: 核心 Flink 架构、DataStream API、Table API/SQL
- 1.4: 时间概念和时区处理（合并）
- 1.5-1.6: Watermark 和窗口
- 1.7-1.9: 状态类型、状态后端、状态访问
- 1.10: Checkpoint

**阶段 2: Flink-Kafka 集成（第 6-8 天）**
- 2.1-2.4: Kafka 连接器、Schema Registry、分区

**阶段 3: Flink SQL（第 9-12 天）**
- 3.1-3.6: SQL 窗口函数、连接、UDF、时间属性

**阶段 4: 有状态处理（第 13-14 天）**
- 4.1-4.2: ProcessFunction、状态 TTL

**阶段 5: 外部集成（第 15-17 天）**
- 5.1-5.2: JDBC 连接器、Supabase 集成（带示例）
- 6.1-6.4: Confluent Cloud 部署（带具体步骤）
- 7.1-7.4: 数据源 API、计算位置模式

**阶段 6: 基础设施（第 18-19 天）**
- 8.1-8.3: AWS Lambda、EventBridge（带 cron 示例）
- 时区已在 1.4 中涵盖

**阶段 7: 质量和测试（第 20-22 天）**
- 9.1-9.4: 错误处理、数据验证、项目特定模式
- 10.1-10.4: 测试策略、项目特定场景

**阶段 8: 监控和运维（第 23-25 天）**
- 11.1-11.3: 指标、Grafana（带 SQL 示例）、告警
- 13.1-13.3: 部署、故障排除、成本优化

**阶段 9: 项目实现（第 26-30 天）**
- 12.1-12.5: 项目特定算法、公式、连接类型选择
- 构建和部署完整系统

---

## 注释

- **原子学习点**: 每个编号项都是一个专注的、原子的学习单元
- **先决条件**: 项目按顺序排列——后面的项目依赖于前面的项目
- **20/80 重点**: 优先考虑本项目最关键的知识
- **功能 + 运维**: 涵盖"如何使用"和"如何部署/监控"
- **具体示例**: 包括代码片段、配置示例和项目中的公式
- **已假设知识**: 在顶部明确列出——学习者已经了解 Kafka 基础、AWS、Python、SQL、Java
- **MVP 重点**: 强调 MVP 所需的知识，高级主题标记为可选
