# MarketLag 项目工程设计文档

**项目名称**: MarketLag
**版本**: v5.0
**最后更新**: 2026-01-07

---

## 一、项目目标

**项目目标**：

> **利用公共高可信信息源（RSS/新闻）与 Polymarket 预测市场价格之间的时间差（information → market latency），在近实时/准实时层面识别潜在的市场低效（arbitrage / lag signals）。**

**注意**：
* 我们做的是 **"机会判断 / lag detection"**
* **不是自动交易系统**（这在合规、工程复杂度、产品叙事上都更合理）

---

## 二、MVP 场景定义

### 🎯 聚焦一个预测市场

* **主题**：1 月份美联储是否加息（Fed hike in January）
* **刷新频率**：
  * **RSS事件**：实时/近实时（每15分钟轮询，避免rate limit）
  * **Polymarket价格**：小时级（整点拉取）
  * **Lag检测**：每小时计算一次（但基于实时RSS数据）
* **目标**：
  * 在工程难度低的前提下
  * 验证"信息 → 市场反应"是否存在可检测的 lag

**注意**：RSS采用近实时轮询而非小时级，因为美联储相关新闻可能在任意时间发布，如果只在整点检查可能错过关键信息。

---

## 三、技术栈与版本

### 核心版本（锚定）
- **Apache Kafka**: 3.7.2
- **Apache Flink**: 2.2.0
- **PostgreSQL**: 14+ (Supabase托管)
- **Python**: 3.9+

### 数据接入
- **Python 3.9+** (requests, kafka-python, confluent-kafka)
- 运行环境：AWS Lambda（无服务器）
- 定时任务：AWS EventBridge（定时触发）

### 流处理与消息队列
- **Confluent Cloud** (Kafka + Flink托管服务)
  - Kafka: 托管Kafka集群（兼容Kafka 3.7.2）
  - Flink: 托管Flink计算集群（Flink 2.2.0）
  - Schema Registry: 托管schema管理
  - 优势：无需自建和维护，自动扩缩容，高可用

### 存储
- **Supabase** (PostgreSQL托管服务)
  - 托管PostgreSQL数据库
  - 自动备份和恢复
  - 内置连接池和监控
  - 优势：简单易用，成本低，PostgreSQL兼容

### 可视化
- **Grafana Cloud** (托管Grafana服务)
  - 托管Grafana实例
  - 数据源连接：Supabase PostgreSQL + Confluent Cloud metrics
  - 优势：无需自建，自动更新，专业监控

---

## 四、数据源

### A. RSS.app（核心信息输入）

#### API调用
- **Endpoint格式**: `https://rss.app/feeds/v1.1/{feed_id}.json`
  - 示例: `https://rss.app/feeds/v1.1/x6KH5aqpKp2jqVNE.json`
  - 每个feed是在RSS.app上手动创建的
- **认证**: 无需API Key（公开feed URL）
- **轮询频率**: 每15分钟（通过AWS EventBridge定时触发）
- **Rate Limit**: 根据RSS.app文档设置

#### 数据内容
- 聚合：Reuters、其他权威新闻源
- 关注点：**"什么时候出现了可影响市场预期的事实/解读"**
- **Feed管理**: 在RSS.app平台上手动创建和配置feed，获取feed_id后使用上述URL格式

---

### B. Polymarket（市场数据源）

#### API架构说明
Polymarket使用两套独立的API系统：
1. **Gamma API**: 用于市场元数据（market metadata）
2. **CLOB API**: 用于价格数据（price data）

#### 1. Market Metadata（Gamma API）

**Endpoint选项**:
- `GET https://gamma-api.polymarket.com/markets/slug/{slug}`
- 或 `GET https://gamma-api.polymarket.com/markets?slug={slug}`

**数据提取**:
- 从响应中提取 `clobTokenIds`（YES/NO token id）
- 提取市场基本信息：question, close_time等

**调用频率**: 低频（启动时或市场变更时拉取）

**认证**: MVP阶段使用public endpoints，无需API Key

#### 2. Price Data（CLOB API）

**推荐方式（批量）**:
- `POST https://clob.polymarket.com/prices`
- 请求体：`{"token_ids": ["0x...", "0x..."]}` (YES和NO token id)
- 一次请求获取YES/NO两个价格

**备选方式（单个）**:
- `GET https://clob.polymarket.com/price?token_id=...&side=BUY`

**调用频率**: 每小时整点拉取

**认证**: MVP阶段使用public endpoints，无需API Key

**数据流链路**:
```
market_slug → Gamma API → clobTokenIds (YES/NO) → CLOB API → prices
```

---

## 五、整体工程架构

```
[RSS.app]                [Polymarket APIs]
    |                         |
    |                    [Gamma API] → token_ids
    |                         |
    v                         v
AWS EventBridge        AWS EventBridge
(定时触发)            (定时触发)
    |                         |
    v                         v
AWS Lambda            AWS Lambda
(RSS Producer)        (Polymarket Producer)
    |                         |
    v                         v
Confluent Cloud Kafka    Confluent Cloud Kafka
(rss.events)        (polymarket.price_hourly)
        \               /
         \             /
          v           v
    Confluent Cloud Flink
      (event-time, window, state)
                 |
                 v
        lag_signals (Kafka Topic)
                 |
        +--------+--------+
        |                 |
        v                 v
  Supabase PostgreSQL  Grafana Cloud
  (持久化存储)        (可视化)
```

**架构说明**：
- 数据接入层：Python脚本打包为AWS Lambda函数，通过EventBridge定时触发
- EventBridge：RSS每15分钟触发一次，Polymarket每小时整点触发一次
- Confluent Cloud：托管Kafka和Flink，提供完整的流处理能力
- Supabase：托管PostgreSQL，存储历史数据
- Grafana Cloud：托管可视化服务，实时监控和展示

---

## 六、本地开发测试环境（Docker Compose，macOS）

### 环境组成
- **Kafka**: 3.7.2 (本地测试)
- **Zookeeper**: 3.8.x (Kafka依赖)
- **Schema Registry**: Confluent Schema Registry (本地测试)
- **PostgreSQL**: 14 (模拟Supabase)
- **Grafana**: 最新版本 (本地测试)

### Docker Compose配置

#### `docker-compose.yml`
```yaml
version: '3.8'

services:
  zookeeper:
    image: confluentinc/cp-zookeeper:7.5.0
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181
      ZOOKEEPER_TICK_TIME: 2000
    ports:
      - "2181:2181"

  kafka:
    image: confluentinc/cp-kafka:7.5.0
    depends_on:
      - zookeeper
    ports:
      - "9092:9092"
    environment:
      KAFKA_BROKER_ID: 1
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://localhost:9092
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
      KAFKA_AUTO_CREATE_TOPICS_ENABLE: 'true'

  schema-registry:
    image: confluentinc/cp-schema-registry:7.5.0
    depends_on:
      - kafka
    ports:
      - "8081:8081"
    environment:
      SCHEMA_REGISTRY_HOST_NAME: schema-registry
      SCHEMA_REGISTRY_KAFKASTORE_BOOTSTRAP_SERVERS: kafka:9092

  postgres:
    image: postgres:14
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: marketlag
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      GF_SECURITY_ADMIN_PASSWORD: admin
    volumes:
      - grafana_data:/var/lib/grafana

volumes:
  postgres_data:
  grafana_data:
```

### 启动和停止

#### 启动环境
```bash
docker-compose up -d
```

#### 停止环境
```bash
docker-compose down
```

#### 查看日志
```bash
docker-compose logs -f kafka
```

### 本地开发配置

#### Python Producer配置（本地）
```python
{
    'bootstrap.servers': 'localhost:9092',
    'acks': 'all',
    'retries': 3,
    'max.in.flight.requests.per.connection': 1,
    'enable.idempotence': True
}
```

#### Flink本地测试
- 使用Flink LocalEnvironment进行本地测试
- 连接本地Kafka: `localhost:9092`
- 连接本地PostgreSQL: `localhost:5432`

### 与生产环境差异
- **Kafka**: 本地单节点，生产环境为Confluent Cloud多节点集群
- **Schema Registry**: 本地单实例，生产环境为Confluent Cloud托管
- **PostgreSQL**: 本地无备份，生产环境Supabase自动备份
- **Flink**: 本地LocalEnvironment，生产环境为Confluent Cloud Flink

---

## 七、GitHub仓库设计与CI/CD

### 仓库结构

#### 1. `marketlag-data-producers` (数据接入层)
- **内容**: RSS和Polymarket数据接入Python脚本
- **技术栈**: Python 3.9+, kafka-python, requests
- **CI/CD**:
  - 测试：pytest单元测试
  - 部署：自动打包为Lambda Layer和函数，通过Terraform/CloudFormation部署到AWS
  - EventBridge规则：通过Infrastructure as Code自动配置

#### 2. `marketlag-flink-jobs` (Flink作业)
- **内容**: Flink SQL和Java作业代码
- **技术栈**: Flink 2.2.0, Java 11+, Flink SQL
- **CI/CD**:
  - 构建：Maven/Gradle构建JAR
  - 测试：Flink本地测试
  - 部署：自动部署到Confluent Cloud Flink

#### 3. `marketlag-infrastructure` (基础设施)
- **内容**: Docker Compose配置、数据库迁移脚本、Grafana Dashboard JSON
- **技术栈**: Docker, SQL, Grafana
- **CI/CD**:
  - 验证：Docker Compose验证
  - 部署：手动应用到Supabase和Grafana Cloud

#### 4. `marketlag-docs` (文档)
- **内容**: 项目文档、API文档、运维手册
- **CI/CD**: 自动生成和发布文档站点

### CI/CD流程设计

#### GitHub Actions工作流

##### 1. 数据接入层CI/CD (`marketlag-data-producers/.github/workflows/cicd.yml`)
```yaml
name: Data Producers CI/CD

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest
      - name: Run tests
        run: pytest

  deploy:
    needs: test
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
      - name: Package Lambda function
        run: |
          zip -r lambda_function.zip *.py
          # 创建Lambda Layer（包含依赖）
          mkdir -p python/lib/python3.9/site-packages
          pip install -r requirements.txt -t python/lib/python3.9/site-packages/
          zip -r lambda_layer.zip python/
      - name: Deploy Lambda functions
        run: |
          # 使用AWS CLI或Terraform部署
          aws lambda update-function-code --function-name rss-producer --zip-file fileb://lambda_function.zip
          aws lambda update-function-code --function-name polymarket-producer --zip-file fileb://lambda_function.zip
          aws lambda publish-layer-version --layer-name marketlag-dependencies --zip-file fileb://lambda_layer.zip
      - name: Update EventBridge rules
        run: |
          # 确保EventBridge规则正确配置
          # 使用Terraform或CloudFormation更新
```

##### 2. Flink作业CI/CD (`marketlag-flink-jobs/.github/workflows/cicd.yml`)
```yaml
name: Flink Jobs CI/CD

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  build-and-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up JDK 11
        uses: actions/setup-jdk@v3
        with:
          java-version: '11'
      - name: Build with Maven
        run: mvn clean package
      - name: Run Flink tests
        run: mvn test

  deploy:
    needs: build-and-test
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Deploy to Confluent Cloud
        env:
          CONFLUENT_CLOUD_API_KEY: ${{ secrets.CONFLUENT_CLOUD_API_KEY }}
          CONFLUENT_CLOUD_API_SECRET: ${{ secrets.CONFLUENT_CLOUD_API_SECRET }}
        run: |
          # 使用Confluent Cloud CLI部署Flink作业
          confluent flink job create --jar target/marketlag-jobs.jar
```

##### 3. 基础设施验证 (`marketlag-infrastructure/.github/workflows/validate.yml`)
```yaml
name: Infrastructure Validation

on: [push, pull_request]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Validate Docker Compose
        run: docker-compose config
      - name: Validate SQL scripts
        run: |
          # 使用pg_format或类似工具验证SQL
```

### 部署流程

#### 开发环境
1. 本地Docker Compose启动
2. 本地运行Python producers（测试用）
3. 本地Flink LocalEnvironment测试
4. AWS Lambda本地测试（使用SAM CLI或LocalStack）

#### 测试环境
1. Confluent Cloud开发环境
2. Supabase测试项目
3. Grafana Cloud测试实例

#### 生产环境
1. Confluent Cloud生产环境
2. Supabase生产项目
3. Grafana Cloud生产实例
4. 通过GitHub Actions自动部署（main分支）

### 密钥管理
- **GitHub Secrets**: 存储API keys、数据库密码等敏感信息
- **Confluent Cloud**: 使用API Key和Secret
- **Supabase**: 使用项目API Key
- **Grafana Cloud**: 使用API Key

---

## 八、数据接入层设计（AWS Lambda + EventBridge）

### 部署架构

#### AWS Lambda函数
- **RSS Producer Lambda**: 从RSS.app拉取数据并写入Kafka
- **Polymarket Producer Lambda**: 从Polymarket API拉取数据并写入Kafka
- **运行时**: Python 3.9+
- **超时设置**: 5分钟（足够完成API调用和Kafka写入）
- **内存配置**: 256MB（足够处理单次请求）
- **环境变量**:
  - Confluent Cloud连接信息
  - RSS feed URLs
  - Polymarket market slugs

#### AWS EventBridge规则
- **RSS Producer触发**:
  - 规则名称: `rss-producer-schedule`
  - 触发频率: 每15分钟（cron: `*/15 * * * ? *`）
  - 目标: RSS Producer Lambda函数
- **Polymarket Producer触发**:
  - 规则名称: `polymarket-producer-schedule`
  - 触发频率: 每小时整点（cron: `0 * * * ? *`）
  - 目标: Polymarket Producer Lambda函数

#### Lambda Layer
- **依赖包**: kafka-python, confluent-kafka, requests等
- **打包方式**: 创建Lambda Layer，多个函数共享依赖

### RSS.app 接入

#### 数据处理
- **Schema转换**: RSS item → Kafka message
- **去重策略**（优先级顺序）:
  1. `item_id`（若RSS.app提供）
  2. `link`或`guid`（RSS item常见字段）
  3. Fallback: `hash(source + title + published_at)`
- **关键词匹配**: 在接入层进行，提取Fed/rate/hike/dovish等关键词
- **数据验证**:
  - 验证`published_at`格式（ISO 8601）
  - 验证`title`非空
  - 验证`source`字段存在

#### 错误处理
- **重试机制**: Lambda内置重试（最多3次）
- **失败处理**: 超过3次失败后记录到dead letter queue（Kafka topic或SQS）
- **监控**: 通过CloudWatch监控Lambda执行情况、API调用成功率、延迟等指标
- **告警**: CloudWatch Alarms监控Lambda错误率和超时

#### Kafka消息Schema
```json
{
  "title": "string",
  "link": "https://...",
  "summary": "string",
  "published_at": "2026-01-07T10:15:00Z",
  "source": "reuters",
  "source_weight": 1.0,
  "keywords": ["Fed", "rate", "hike"],
  "keyword_scores": {"Fed": 2.0, "rate": 1.5, "hike": 2.0},
  "timezone": "UTC"
}
```

**注意**: 增加了`link`和`summary`字段，便于后续LLM处理或debug回溯。

#### Confluent Cloud配置
- **Bootstrap Servers**: Confluent Cloud提供的endpoint
- **认证**: API Key + Secret (Confluent Cloud提供)
- **Schema Registry**: 使用Confluent Cloud Schema Registry
- **Producer配置**:
  ```python
  {
      'bootstrap.servers': '<confluent-cloud-endpoint>',
      'security.protocol': 'SASL_SSL',
      'sasl.mechanism': 'PLAIN',
      'sasl.username': '<api-key>',
      'sasl.password': '<api-secret>',
      'acks': 'all',
      'retries': 3,
      'max.in.flight.requests.per.connection': 1,
      'enable.idempotence': True
  }
  ```

---

### Polymarket API 接入

#### 数据流链路
1. **获取Market Metadata** (Gamma API):
   - 调用: `GET https://gamma-api.polymarket.com/markets/slug/{slug}`
   - 提取: `clobTokenIds` (YES和NO token id)
   - 存储: 本地缓存或配置文件

2. **获取Price Data** (CLOB API):
   - 调用: `POST https://clob.polymarket.com/prices`
   - 请求体: `{"token_ids": ["0x...", "0x..."]}`
   - 响应: YES和NO价格

3. **计算Price Delta**:
   - **在Lambda函数中计算**（推荐方案）
   - 保存上一小时的价格（使用DynamoDB或S3存储）
   - `price_delta = current_price - prev_price`
   - 如果是第一个小时，`price_delta = 0`

#### 数据处理
- **Schema转换**: 直接映射到Kafka message
- **数据验证**:
  - 验证`price ∈ [0,1]`范围
  - 验证`timestamp`有效（不能是未来时间）
  - 验证`market_slug`和`outcome`字段存在
- **时区处理**: 所有时间戳统一转换为UTC

#### 错误处理
- **重试机制**: Lambda内置重试（最多3次）
- **数据缺失处理**: 使用上一小时的数据（从DynamoDB或S3读取，对于价格数据）
- **异常值处理**: 记录日志到CloudWatch，不中断处理
- **监控**: 通过CloudWatch监控Lambda执行情况

#### Kafka消息Schema

**polymarket.market_meta** (低频):
```json
{
  "market_slug": "fed-hike-january-2026",
  "question": "Will the Fed raise rates in January 2026?",
  "close_time": "2026-01-31T23:59:59Z",
  "yes_token_id": "0x...",
  "no_token_id": "0x...",
  "timezone": "UTC"
}
```

**polymarket.price_hourly**:
```json
{
  "market_slug": "fed-hike-january-2026",
  "outcome": "YES",
  "price": 0.65,
  "price_delta": 0.02,
  "event_time": "2026-01-07T10:00:00Z",
  "fetched_at": "2026-01-07T10:00:15Z",
  "prev_price": 0.63,
  "timezone": "UTC"
}
```

**注意**: `price_delta`在Producer侧计算，Flink Job 2不再需要计算price_delta。

---

## 九、Kafka Topic 设计（Confluent Cloud）

### Topic配置原则
- 所有Topic在Confluent Cloud中创建
- 使用Confluent Cloud Schema Registry管理schema
- 利用Confluent Cloud的自动分区管理和监控

### 1️⃣ `rss.events`

* **Partition Key**: `market_slug` (为多市场扩展预留，即使目前单市场)
* **Partitions**: 3 (Confluent Cloud Basic计划支持)
* **Replication Factor**: 3 (Confluent Cloud自动管理)
* **Retention**: 7天
* **Schema**: 使用Schema Registry注册JSON schema

### 2️⃣ `polymarket.market_meta`（低频）

* **Partition Key**: `market_slug`
* **Partitions**: 1 (低频数据，单分区足够)
* **Retention**: 30天（元数据变化频率低）
* **Schema**: 使用Schema Registry注册JSON schema

### 3️⃣ `polymarket.price_hourly`

* **Partition Key**: `market_slug|outcome` (如 "fed-hike-january-2026|YES")
* **Partitions**: 3
* **Retention**: 7天
* **Schema**: 使用Schema Registry注册JSON schema

### 4️⃣ `rss.signals_hourly` (中间Topic，Job 1输出)

* **Partition Key**: `market_slug|window_start` (避免整点热点)
* **Partitions**: 3
* **Retention**: 7天
* **Value Schema**:
```json
{
  "market_slug": "fed-hike-january-2026",
  "window_start": "2026-01-07T10:00:00Z",
  "window_end": "2026-01-07T11:00:00Z",
  "mention_count": 15,
  "keyword_score": 8.5,
  "source_weighted_signal": 7.2,
  "timezone": "UTC"
}
```

### 5️⃣ `lag_signals` (最终输出Topic)

* **Partition Key**: `market_slug|window_start`
* **Partitions**: 3
* **Retention**: 30天
* **Schema**: 见"Flink Job设计"章节

### 6️⃣ Dead Letter Queues

* `dlq.rss.events`: RSS数据接入失败的记录
* `dlq.polymarket.price_hourly`: Polymarket数据接入失败的记录
* **Retention**: 30天（用于问题排查）

---

## 十、Flink Job 设计（Confluent Cloud Flink）

### Confluent Cloud Flink配置

#### 环境设置
- **Flink版本**: Flink 2.2.0
- **计算单元**: 根据数据量选择（Basic计划：1-4 CFU）
- **State Backend**: RocksDB (Confluent Cloud托管)
- **Checkpoint存储**: Confluent Cloud S3兼容存储

#### 数据流关系

```
rss.events (Confluent Cloud Kafka)
    ↓ (Job 1: 1h tumbling window)
rss.signals_hourly (Confluent Cloud Kafka)
    ↓
    ├─→ (Job 3: 等值Join)
    │
polymarket.price_hourly (Confluent Cloud Kafka) ──→ (Job 2: 价格标准化，price_delta已在Producer计算)
    ↓
    └─→ (Job 3: 等值Join)
    ↓
lag_signals (Confluent Cloud Kafka)
    ↓
    ├─→ Supabase PostgreSQL (JDBC Sink)
    └─→ Grafana Cloud (通过Supabase数据源)
```

**说明**：
- 所有Job在Confluent Cloud Flink中运行
- Job 1和Job 2可以并行运行，互不依赖
- Job 3依赖Job 1和Job 2的输出，通过等值Join合并数据流
- **Job 2简化**: price_delta已在Producer侧计算，Job 2只需做价格标准化
- 推荐：所有Job合并为一个Flink Application，减少运维复杂度

---

### Job 1：RSS 信号小时聚合

#### 设计选择
- **语言**: Flink SQL (Table API) - 简单窗口聚合
- **输入**: `rss.events` topic (Confluent Cloud Kafka)
- **输出**: `rss.signals_hourly` topic (Confluent Cloud Kafka)

#### 处理逻辑
- **窗口**: 1小时 tumbling window，基于`published_at`的event time
- **Keyed by**: `market_slug` (为多市场扩展预留)
- **Watermark策略**: 允许5分钟延迟
- **聚合计算**:
  - `mention_count`: COUNT(*)
  - `keyword_score`: SUM(keyword_weight × occurrence_count)
    - 关键词权重: Fed=2.0, rate=1.5, hike=2.0, dovish=-1.5 (负值表示降低概率)
  - `source_weighted_signal`: SUM(article_score × source_weight) / COUNT(*)
    - 来源权重: Reuters=1.0, Bloomberg=0.9, 其他=0.7
    - article_score = SUM(keyword_scores)

#### 配置
- **State**: 不需要keyed state（窗口聚合自动管理）
- **并行度**: 2 (Confluent Cloud Basic计划)
- **Checkpoint**: 每5分钟一次
- **Watermark配置**:
  ```sql
  WATERMARK FOR published_at AS published_at - INTERVAL '5' MINUTE
  ```

---

### Job 2：价格标准化（简化版）

#### 设计选择
- **语言**: Flink SQL (纯SQL实现，无需Java)
- **输入**: `polymarket.price_hourly` topic (Confluent Cloud Kafka)
- **输出**: 直接用于Job 3的Join（或输出到中间topic）

#### 处理逻辑
- **标准化**: 确保price ∈ [0,1]（API返回的price应该已经在这个范围）
- **注意**: `price_delta`已在Producer侧计算，Job 2只需做标准化和验证

#### 配置
- **并行度**: 2
- **Watermark策略**: 允许5分钟延迟
- **Checkpoint**: 每5分钟一次

**简化说明**: 由于price_delta在Producer侧计算，Job 2不再需要State管理，可以完全用Flink SQL实现，降低部署复杂度。

---

### Job 3：Lag / 机会判断（MVP 规则）

#### 设计选择
- **语言**: Flink SQL (Table API) - 等值Join
- **输入**:
  - `rss.signals_hourly` (来自Job 1，Confluent Cloud Kafka)
  - `polymarket.price_hourly` (来自Producer，包含price_delta，Confluent Cloud Kafka)
- **输出**:
  - `lag_signals` topic (Confluent Cloud Kafka)
  - Supabase PostgreSQL (通过JDBC Sink)

#### 处理逻辑
- **Join方式**: **等值Join**（不再使用Interval Join）
  - Join Key: `market_slug + window_start`
  - Join条件: `rss.signals_hourly.window_start = polymarket.price_hourly.event_time`
  - `event_time`是整点时间，`window_start`也是整点时间，完全对齐
- **Lag检测规则**（MVP版本，简化）:
  > **如果在 t 小时：**
  >
  > * `signal_delta = signal(t) - signal(t-1)`
  > * `signal_delta > 1.0`
  > * `abs(price_delta) < 0.02`
  >
  > ⇒ 标记为 **potential lag window**

**注意**: MVP只保留绝对阈值规则，baseline相对阈值留到后续版本。

- **Confidence计算**:
  ```
  confidence = min(1.0,
    (signal_delta / max_signal_delta) * 0.5 +
    (1 - |price_delta|) * 0.3 +
    (source_weight_avg) * 0.2
  )
  ```
  - `max_signal_delta`: 历史最大signal_delta（需要State保存）
  - `source_weight_avg`: 该窗口内RSS来源的平均权重

#### 输出Schema
```json
{
  "market": "fed-hike-january-2026",
  "window": "2026-01-07T10:00:00Z",
  "signal_delta": 1.6,
  "price_delta": 0.00,
  "lag_flag": true,
  "confidence": 0.72,
  "rss_signal": 7.2,
  "prev_rss_signal": 5.6,
  "price": 0.65,
  "prev_price": 0.65,
  "detected_at": "2026-01-07T10:05:00Z",
  "timezone": "UTC"
}
```

#### 配置
- **State**:
  - MapState<String, Double> (保存历史最大signal_delta，key为market_slug)
  - State TTL: 7天
- **并行度**: 2
- **Checkpoint**: 每5分钟一次
- **JDBC Sink配置** (写入Supabase):
  - Connection URL: Supabase PostgreSQL连接字符串
  - Table: `lag_signals_history`
  - Batch Size: 100
  - Flush Interval: 10秒

---

### 关键指标定义

#### keyword_score
```
keyword_score = sum(keyword_weight × occurrence_count) for each keyword
```
- 关键词权重示例: Fed=2.0, rate=1.5, hike=2.0, dovish=-1.5 (负值表示降低概率)

#### source_weighted_signal
```
source_weighted_signal = sum(article_score × source_weight) / count
```
- 来源权重: Reuters=1.0, Bloomberg=0.9, 其他=0.7
- article_score = SUM(keyword_scores for that article)

#### signal_delta
```
signal_delta = current_hour.source_weighted_signal - prev_hour.source_weighted_signal
```

#### Lag检测阈值（MVP版本）
- `signal_delta > 1.0` (绝对阈值)
- `abs(price_delta) < 0.02` (2%)

**注意**: MVP只使用绝对阈值，baseline相对阈值留到后续版本。

#### confidence
见Job 3的confidence计算公式

---

## 十一、时区处理策略

### 统一时区
- **所有时间戳统一转换为UTC**
- **小时对齐基于UTC时间**
- **在Kafka message中明确标注timezone字段为"UTC"**

### 实现细节
- RSS接入层: 将`published_at`转换为UTC（如果源数据是其他时区）
- Polymarket接入层: 将`event_time`和`fetched_at`转换为UTC
- Flink处理: 所有窗口和join操作基于UTC时间
- 输出: 所有输出时间戳均为UTC格式

### 示例
```
RSS published_at: "2026-01-07T10:15:00-05:00" (EST)
→ 转换为: "2026-01-07T15:15:00Z" (UTC)
→ 对齐到小时窗口: "2026-01-07T15:00:00Z"
```

---

## 十二、存储设计（Supabase PostgreSQL）

### 数据库配置
- **服务**: Supabase (托管PostgreSQL)
- **版本**: PostgreSQL 14+
- **连接**: 通过Supabase提供的连接字符串
- **连接池**: Supabase自动管理

### 表结构设计

#### `lag_signals_history` (主表)
```sql
CREATE TABLE lag_signals_history (
    id SERIAL PRIMARY KEY,
    market VARCHAR(100) NOT NULL,
    window TIMESTAMP NOT NULL,
    signal_delta DECIMAL(10, 4),
    price_delta DECIMAL(10, 4),
    lag_flag BOOLEAN,
    confidence DECIMAL(3, 2),
    rss_signal DECIMAL(10, 4),
    prev_rss_signal DECIMAL(10, 4),
    price DECIMAL(5, 4),
    prev_price DECIMAL(5, 4),
    detected_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT unique_market_window UNIQUE (market, window)
);

CREATE INDEX idx_market_window ON lag_signals_history(market, window);
CREATE INDEX idx_detected_at ON lag_signals_history(detected_at);
CREATE INDEX idx_lag_flag ON lag_signals_history(lag_flag) WHERE lag_flag = true;
```

#### `api_health_log` (可选，用于监控)
```sql
CREATE TABLE api_health_log (
    id SERIAL PRIMARY KEY,
    source VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL,
    response_time_ms INTEGER,
    error_message TEXT,
    logged_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_source_logged_at ON api_health_log(source, logged_at);
```

### 数据保留策略
- **lag_signals_history**: 90天（可配置，通过Supabase自动清理或定时任务）
- **api_health_log**: 30天

### Flink JDBC Sink配置
- **Connector**: Flink JDBC Connector
- **Connection URL**: `jdbc:postgresql://<supabase-host>:5432/postgres`
- **Driver**: `org.postgresql.Driver`
- **Table**: `lag_signals_history`
- **Batch Size**: 100
- **Flush Interval**: 10秒
- **Max Retries**: 3

---

## 十三、可视化设计（Grafana Cloud）

### Grafana Cloud配置
- **服务**: Grafana Cloud (托管Grafana)
- **数据源**:
  - Supabase PostgreSQL (主要数据源)
  - Confluent Cloud Metrics (系统监控)

### Dashboard设计

#### Dashboard 1: Lag信号监控（实时）
- **Panel 1**: Lag信号数量（按小时）- Time Series
  - 查询: `SELECT date_trunc('hour', detected_at) as hour, COUNT(*) FROM lag_signals_history WHERE lag_flag = true GROUP BY date_trunc('hour', detected_at) ORDER BY hour`
  - **修正**: 使用`date_trunc('hour', detected_at)`按小时桶聚合，而不是`GROUP BY detected_at`
- **Panel 2**: Confidence分布 - Histogram
  - 查询: `SELECT confidence FROM lag_signals_history WHERE lag_flag = true`
- **Panel 3**: Signal delta vs Price delta - Scatter Plot
  - X轴: signal_delta, Y轴: price_delta
- **Panel 4**: 最近24小时Lag信号列表 - Table
  - 查询: `SELECT * FROM lag_signals_history WHERE lag_flag = true AND detected_at > NOW() - INTERVAL '24 hours' ORDER BY detected_at DESC`

#### Dashboard 2: 系统健康监控
- **Panel 1**: Confluent Cloud Flink Job状态
  - 数据源: Confluent Cloud Metrics API
- **Panel 2**: Kafka Consumer Lag
  - 数据源: Confluent Cloud Metrics API
- **Panel 3**: API健康度（RSS.app, Polymarket）
  - 数据源: `api_health_log`表
- **Panel 4**: 数据流吞吐量
  - 数据源: Confluent Cloud Metrics API

#### Dashboard 3: 历史分析
- **Panel 1**: False Positive Rate趋势
- **Panel 2**: 信号准确性分析
- **Panel 3**: RSS Signal和Price变化时间序列对比

### 告警配置
- **高优先级告警**:
  - Lag信号数量异常（突然为0或激增）
  - Flink Job失败
  - Kafka Consumer Lag > 1小时
- **通知渠道**: Email / Slack (Grafana Cloud支持)

---

## 十四、数据质量保障

### 数据验证

#### RSS数据验证
- 验证`published_at`格式（ISO 8601）
- 验证`title`非空
- 验证`source`字段存在且有效
- 验证`keywords`数组格式正确
- 验证`link`和`summary`字段存在（新增）

#### Polymarket数据验证
- 验证`price ∈ [0,1]`范围
- 验证`timestamp`有效（不能是未来时间）
- 验证`market_slug`和`outcome`字段存在
- 验证`price_delta`计算正确（Producer侧已计算）

### 异常处理

#### API失败处理
- **重试机制**: 失败后重试3次，指数退避（1s, 2s, 4s）
- **失败后处理**: 超过3次失败后记录到dead letter queue (Confluent Cloud Kafka topic)
- **监控告警**: API失败率 > 10%时触发Grafana告警

#### 数据缺失处理
- **价格数据缺失**: 使用上一小时的数据（Producer侧处理）
- **RSS数据缺失**: 跳过该小时窗口（不输出signal，但记录日志）
- **Join失败**: 如果RSS或Price数据缺失导致无法join，记录到side output

#### 异常值处理
- **价格超出范围**: 记录日志，不中断处理，使用clamp到[0,1]
- **时间戳异常**: 记录日志，使用当前时间作为fallback
- **计算异常**: 记录日志，输出confidence=0的lag信号

### Schema验证
- **Confluent Cloud Schema Registry**: 所有Topic使用Schema Registry管理schema
- **Flink侧验证**: 使用Flink SQL的类型系统进行验证
- **Supabase侧验证**: 使用PostgreSQL约束和触发器

---

## 十五、监控和运维

### 关键指标

#### Confluent Cloud Flink指标
- **Checkpoint成功率**: 目标 > 99% (通过Confluent Cloud UI监控)
- **Checkpoint时长**: 目标 < 30秒
- **背压（Backpressure）**: 通过Confluent Cloud Metrics监控
- **State Size**: 通过Confluent Cloud Metrics监控
- **Watermark延迟**: 监控event time和processing time的差距
- **Throughput**: 每秒处理的消息数

#### Confluent Cloud Kafka指标
- **Consumer Lag**: 各consumer group的lag，目标 < 1小时
- **Throughput**: 各topic的写入和读取速率
- **Partition分布**: 确保数据分布均匀
- **Broker健康度**: Confluent Cloud自动监控

#### 业务指标（通过Grafana监控）
- **Lag信号数量**: 每小时检测到的lag信号数
- **False Positive Rate**: 需要人工标记验证
- **数据源健康度**: RSS和Polymarket API的可用性
- **端到端延迟**: 从RSS发布到lag信号输出的时间

### 告警策略

#### 高优先级告警（立即处理）
- Flink job失败或重启 (Confluent Cloud告警)
- Kafka consumer lag > 1小时 (Confluent Cloud告警)
- Checkpoint失败率 > 5% (Confluent Cloud告警)
- 数据源API连续失败 > 3次 (Grafana告警)

#### 中优先级告警（1小时内处理）
- 背压持续 > 10分钟 (Confluent Cloud告警)
- State size增长异常 (Confluent Cloud告警)
- Watermark延迟 > 10分钟 (Confluent Cloud告警)
- Lag信号数量异常（突然为0或突然激增）(Grafana告警)

#### 低优先级告警（24小时内处理）
- API失败率 > 10% (Grafana告警)
- 数据质量指标下降 (Grafana告警)
- 性能指标异常（但不影响功能）(Confluent Cloud告警)

### 故障恢复策略

#### Confluent Cloud Flink Job故障
- **自动恢复**: Confluent Cloud自动重启失败的Job
- **State恢复**: 从最新checkpoint恢复（Confluent Cloud自动管理）
- **手动恢复**: 通过Confluent Cloud UI手动重启

#### Confluent Cloud Kafka故障
- **自动故障转移**: Confluent Cloud自动处理broker故障
- **数据丢失**: 从checkpoint恢复，重新处理数据

#### 数据源故障
- **RSS.app故障**: 记录到dead letter queue，等待恢复后重试
- **Polymarket API故障**: 使用上一小时数据，记录告警

#### Supabase故障
- **自动备份恢复**: Supabase自动备份，支持时间点恢复
- **连接故障**: Flink JDBC Sink自动重试

---

## 十六、费用分析

### 计费模型说明

#### Confluent Cloud Kafka
**计费因子**:
- **容量单位 (CKU)**: 根据数据吞吐量和存储需求
- **存储**: 按GB/月计费
- **网络**: 出站流量计费
- **Region**: 不同region价格不同

**MVP用量假设**:
- 数据吞吐量: < 1 MB/s (RSS事件 + Polymarket价格)
- 存储需求: < 10 GB (7-30天retention)
- 网络流量: < 10 GB/月

**费用区间估算**:
- **Basic计划**: $0.10-0.15/CKU/小时
- MVP需要: 1-2 CKU
- **月度费用**: $73-110/月 (1 CKU) 或 $146-220/月 (2 CKU)
- **存储费用**: $0.10/GB/月，约$1/月
- **网络费用**: 通常包含在计划内
- **总计区间**: **$74-221/月**（取决于region和实际用量）

#### Confluent Cloud Flink
**计费因子**:
- **CFU (Confluent Flink Unit)**: 按CFU-minute计费
- **Region**: 不同region价格不同

**MVP用量假设**:
- 计算需求: 2 CFU (足够处理MVP数据量)
- 运行时间: 24/7运行

**费用区间估算**:
- **Basic计划**: $0.008-0.012/CFU-minute
- MVP需要: 2 CFU × 43,200分钟/月 = 86,400 CFU-minutes
- **月度费用**: $691-1,037/月
- **总计区间**: **$691-1,037/月**（取决于region）

#### Supabase
- **Free计划**: $0/月 (适合MVP)
  - 包含：500MB数据库，1GB带宽，2个项目
  - MVP数据量：预计每天<10MB，90天保留约900MB（接近但可用）
- **Pro计划** (如需要): $25/月
  - 包含：8GB数据库，50GB带宽，无限项目
  - **推荐MVP使用Free计划，如数据增长再升级**
- **Supabase小计**: **$0-25/月**

#### Grafana Cloud
- **Free计划**: $0/月
  - 包含：10,000 metrics，50GB logs，3 users
  - MVP需求：预计<1,000 metrics，足够使用
- **Pro计划** (如需要): $8/user/月
  - 包含：150,000 metrics，100GB logs
  - **推荐MVP使用Free计划**
- **Grafana Cloud小计**: **$0/月**

#### RSS.app
- **Basic计划**: **$10/月**
  - 包含：1,000 API calls/小时，足够MVP需求

#### AWS Lambda + EventBridge
- **Lambda执行费用**:
  - 请求数: RSS每15分钟1次 + Polymarket每小时1次 = 约4,380次/月
  - 计算时间: 每次约5秒，256MB内存
  - 费用: 前100万次请求免费，之后$0.20/百万次 ≈ **$0/月**（MVP阶段）
- **Lambda计算费用**:
  - RSS: 4,380次 × 5秒 × 256MB = 约5,606,400 GB-秒/月
  - Polymarket: 730次 × 5秒 × 256MB = 约934,400 GB-秒/月
  - 总计: 约6,540,800 GB-秒/月
  - 费用: 前400,000 GB-秒免费，之后$0.0000166667/GB-秒 ≈ **$0.10/月**
- **EventBridge规则**: 前100万次触发免费，之后$1.00/百万次 ≈ **$0/月**（MVP阶段）
- **DynamoDB** (存储上一小时价格，可选):
  - 按需计费，MVP阶段约$0.25/月
  - 或使用S3（更便宜，约$0.02/月）
- **AWS Lambda + EventBridge小计**: **约$0.10-0.35/月**

### 总费用估算（MVP阶段）

#### 最低配置（保守估算）
- Confluent Cloud Kafka: $74/月 (1 CKU)
- Confluent Cloud Flink: $691/月 (2 CFU)
- Supabase: $0/月 (Free计划)
- Grafana Cloud: $0/月 (Free计划)
- RSS.app: $10/月
- AWS Lambda + EventBridge: $0.10/月
- **总计: 约$775/月**

#### 推荐配置（中等估算）
- Confluent Cloud Kafka: $150/月 (2 CKU)
- Confluent Cloud Flink: $864/月 (2 CFU，中等region)
- Supabase: $0/月 (Free计划)
- Grafana Cloud: $0/月 (Free计划)
- RSS.app: $10/月
- AWS Lambda + EventBridge: $0.35/月 (包含DynamoDB)
- **总计: 约$1,024/月**

#### 高配置（上限估算）
- Confluent Cloud Kafka: $221/月 (2 CKU，高价格region)
- Confluent Cloud Flink: $1,037/月 (2 CFU，高价格region)
- Supabase: $25/月 (Pro计划)
- Grafana Cloud: $0/月 (Free计划)
- RSS.app: $10/月
- AWS Lambda + EventBridge: $0.35/月 (包含DynamoDB)
- **总计: 约$1,293/月**

### 重要说明
- **以上估算基于Confluent Cloud公开定价和MVP用量假设**
- **实际费用取决于**:
  - Region选择（不同region价格差异较大）
  - 实际数据量和吞吐量
  - 存储使用量
  - 网络流量
- **建议**: 使用Confluent Cloud定价计算器获取准确报价（按选择的region）
- **成本优化**:
  - 使用开发环境进行测试（更便宜）
  - 合理设置数据保留时间
  - 监控实际用量，及时调整配置

### 成本优化建议
1. **Confluent Cloud**:
   - MVP阶段使用开发环境进行测试（更便宜）
   - 选择价格较低的region
   - 监控实际用量，避免过度配置
2. **Supabase**: 先用Free计划，数据增长后再升级
3. **Grafana Cloud**: Free计划足够MVP使用
4. **数据接入**: 使用AWS Lambda，按实际执行计费，成本极低
5. **监控**: 合理设置数据保留时间，避免存储费用增长

---

## 十七、项目拆分：按部署阶段的子项目

### 子项目1：数据接入层（Week 1）

#### 目标
独立完成RSS.app和Polymarket API到Confluent Cloud Kafka的数据接入

#### 交付物
- Python脚本：RSS数据接入 (`rss_producer.py`)
- Python脚本：Polymarket数据接入 (`polymarket_producer.py`)
  - Gamma API集成（获取token_ids）
  - CLOB API集成（获取价格）
  - Price delta计算（Lambda函数内，使用DynamoDB/S3存储上一小时价格）
- AWS Lambda函数配置：函数定义、环境变量、超时设置
- AWS EventBridge规则：定时触发配置
- Infrastructure as Code：Terraform或CloudFormation模板
- 配置文件：Confluent Cloud连接配置
- 测试脚本：数据验证和端到端测试（包括Lambda本地测试）
- 文档：数据接入层使用说明和部署指南

#### 验收标准
- [ ] RSS数据成功写入`rss.events` topic
- [ ] Polymarket数据成功写入`polymarket.price_hourly` topic（包含price_delta）
- [ ] 数据验证通过（schema、格式、时区）
- [ ] 错误处理和重试机制工作正常
- [ ] Dead letter queue记录失败数据
- [ ] 去重策略正确（link/guid优先）

#### 依赖
- Confluent Cloud账号和Kafka集群
- RSS.app API Key
- Polymarket API（无需Key，使用public endpoints）

---

### 子项目2：Flink Job 1和2（Week 2）

#### 目标
实现RSS聚合和价格标准化处理

#### 交付物
- Flink Job 1：RSS信号小时聚合（Flink SQL）
- Flink Job 2：价格标准化（Flink SQL，简化版，无需Java）
- 部署配置：Confluent Cloud Flink环境配置
- 测试数据：用于验证的测试数据集
- 文档：Job设计和部署说明

#### 验收标准
- [ ] Job 1成功从`rss.events`读取并输出到`rss.signals_hourly`
- [ ] Job 2成功从`polymarket.price_hourly`读取并标准化价格
- [ ] 窗口聚合计算正确（mention_count, keyword_score, source_weighted_signal）
- [ ] Watermark和延迟处理正常
- [ ] Checkpoint正常工作

#### 依赖
- 子项目1完成（数据接入层）
- Confluent Cloud Flink环境

---

### 子项目3：Flink Job 3和存储集成（Week 3）

#### 目标
实现Lag检测逻辑并集成Supabase存储

#### 交付物
- Flink Job 3：Lag检测逻辑（Flink SQL，等值Join）
- Supabase数据库：表结构创建脚本
- Flink JDBC Sink：配置和部署
- 测试脚本：端到端测试和准确性验证
- 文档：Lag检测算法说明和存储设计

#### 验收标准
- [ ] Job 3成功等值join RSS signal和price数据
- [ ] Lag检测规则正确执行（MVP版本：signal_delta > 1.0 && abs(price_delta) < 0.02）
- [ ] Confidence计算准确
- [ ] 数据成功写入Supabase `lag_signals_history`表
- [ ] 端到端数据流完整（从Kafka到PostgreSQL）
- [ ] 已知lag事件能被正确检测

#### 依赖
- 子项目2完成（Job 1和2）
- Supabase账号和数据库

---

### 子项目4：可视化和监控（Week 4）

#### 目标
完成Grafana Dashboard和监控告警配置

#### 交付物
- Grafana Dashboard：Lag信号监控（SQL修正：date_trunc按小时聚合）
- Grafana Dashboard：系统健康监控
- Grafana Dashboard：历史分析
- 告警配置：Grafana告警规则
- Confluent Cloud监控：关键指标监控配置
- 文档：监控和运维手册

#### 验收标准
- [ ] Grafana成功连接Supabase数据源
- [ ] 所有Dashboard面板正常显示数据（时间序列图正确按小时聚合）
- [ ] 告警规则配置正确并能够触发
- [ ] Confluent Cloud监控指标正常收集
- [ ] 系统健康度可视化完整

#### 依赖
- 子项目3完成（数据流完整）
- Grafana Cloud账号
- Supabase数据已有数据

---

### 子项目5：数据质量保障和优化（可选，Week 5）

#### 目标
完善数据质量保障机制和性能优化

#### 交付物
- 数据验证增强：更完善的验证逻辑
- 异常处理完善：更全面的异常场景处理
- 性能优化：Flink Job性能调优
- 监控增强：更详细的业务指标监控
- 文档：数据质量保障手册

#### 验收标准
- [ ] 数据验证覆盖所有异常场景
- [ ] 异常处理机制完善
- [ ] 性能指标达到预期（延迟、吞吐量）
- [ ] 监控指标完整

#### 依赖
- 子项目1-4完成
- 有实际运行数据用于优化

---

## 十八、开发计划（按子项目）

### Week 1: 子项目1 - 数据接入层
- **Day 1-2**: RSS.app API集成
  - API调用实现
  - 数据转换和验证
  - 关键词匹配逻辑
  - 去重策略实现（link/guid优先）
- **Day 3-4**: Polymarket API集成
  - Gamma API集成（获取token_ids）
  - CLOB API集成（获取价格）
  - Price delta计算（Producer侧）
  - 数据转换和验证
- **Day 5**: AWS Lambda和EventBridge部署
  - Lambda函数打包和部署
  - EventBridge规则配置
  - Confluent Cloud Kafka集成
  - Schema Registry集成
  - Topic创建和配置
- **Day 6-7**: 测试和验证
  - 单元测试
  - 集成测试
  - 数据质量验证

### Week 2: 子项目2 - Flink Job 1和2
- **Day 1-2**: Job 1 - RSS聚合
  - Flink SQL实现
  - Watermark配置
  - 窗口聚合逻辑
- **Day 3-4**: Job 2 - 价格标准化（简化版）
  - 价格标准化（纯SQL，无需Java）
  - Watermark配置
- **Day 5-6**: Confluent Cloud Flink部署
  - 环境配置
  - Job部署和测试
  - 监控配置
- **Day 7**: 验证和优化
  - 输出验证
  - 性能测试
  - 问题修复

### Week 3: 子项目3 - Lag检测和存储
- **Day 1-3**: Job 3 - Lag检测逻辑
  - 等值Join实现（不再使用Interval Join）
  - Lag检测规则（MVP版本）
  - Confidence计算
  - State管理
- **Day 4**: Supabase集成
  - 数据库创建
  - 表结构设计
  - Flink JDBC Sink配置
- **Day 5-6**: 端到端测试
  - 完整数据流测试
  - 已知事件验证
  - 边界情况测试
- **Day 7**: 准确性验证
  - 历史数据回放
  - False positive分析
  - 阈值调优

### Week 4: 子项目4 - 可视化和监控
- **Day 1-2**: Grafana Dashboard开发
  - Lag信号监控Dashboard（SQL修正：date_trunc）
  - 系统健康监控Dashboard
  - 历史分析Dashboard
- **Day 3**: 告警配置
  - Grafana告警规则
  - Confluent Cloud告警配置
  - 通知渠道设置
- **Day 4-5**: 监控完善
  - 业务指标监控
  - 系统指标监控
  - 数据质量监控
- **Day 6-7**: 文档和演示
  - 监控运维手册
  - 用户使用文档
  - 演示准备

---

## 十九、测试策略

### 测试数据

#### 历史数据回放
- 使用历史RSS数据和Polymarket价格数据
- 构造已知的lag场景（已知信息发布但价格未变化的时间点）
- 验证lag detection的准确性

#### 人工构造测试数据
- 构造RSS signal上升但price不变的场景
- 构造RSS signal不变但price变化的场景（验证不会误报）
- 构造边界情况（signal_delta刚好在阈值附近）

### 测试方法

#### 单元测试
- **数据接入层**: Mock API响应，测试数据转换和验证逻辑
- **Flink Operators**: 使用Flink测试工具，测试单个operator的逻辑
- **指标计算**: 测试keyword_score、source_weighted_signal等计算函数

#### 集成测试
- **本地Docker Compose环境**: 使用本地Kafka和PostgreSQL，测试完整数据流
- **Confluent Cloud环境**: 使用Confluent Cloud开发环境，测试完整数据流
- **Mock数据源**: 使用可控的数据源，验证各种场景
- **端到端测试**: 从数据接入到存储的完整流程

#### 准确性验证
- **已知事件对比**: 对比已知的lag事件（如历史新闻发布后市场反应延迟）
- **False Positive分析**: 分析误报的lag信号，优化阈值
- **Confidence校准**: 验证confidence score与实际准确性的相关性

### 测试环境
- **开发环境**: 本地Docker Compose + Confluent Cloud开发环境
- **测试环境**: Confluent Cloud测试环境 + Supabase测试项目
- **生产环境**: 完整监控和告警

---

## 二十、风险评估

### 技术风险

#### Confluent Cloud服务中断
- **风险**: Confluent Cloud服务不可用，导致系统中断
- **影响**: 高
- **缓解措施**:
  - Confluent Cloud提供SLA保证
  - 实现数据备份和恢复机制
  - 监控服务健康度

#### Polymarket API变更
- **风险**: Gamma API或CLOB API endpoint或schema变更导致集成失败
- **影响**: 高
- **缓解措施**:
  - 实现适配层，封装API调用
  - 版本化API client
  - 监控API响应格式变化

#### RSS.app服务中断
- **风险**: RSS.app服务不可用，导致数据源中断
- **影响**: 中
- **缓解措施**:
  - 实现备用数据源（如直接RSS feed）
  - 重试机制和告警
  - 数据缺失时的降级处理

#### Supabase容量限制
- **风险**: Free计划容量限制，数据增长后需要升级
- **影响**: 低
- **缓解措施**:
  - 合理设置数据保留时间
  - 监控存储使用量
  - 及时升级到Pro计划

### 业务风险

#### Lag信号不准确（False Positive）
- **风险**: 检测到的lag信号实际上不是真正的市场低效
- **影响**: 高（影响产品可信度）
- **缓解措施**:
  - 实现confidence score
  - 记录所有信号供后续分析
  - 建立反馈机制（标记信号准确性）
  - 持续优化阈值和规则

#### 市场已经反应（False Negative）
- **风险**: 真正的lag存在但未被检测到
- **影响**: 中（错过机会）
- **缓解措施**:
  - 降低检测阈值（但会增加false positive）
  - 多维度信号分析
  - 人工review机制

### 成本风险

#### Confluent Cloud费用超预期
- **风险**: 数据量增长导致费用超出预算
- **影响**: 中
- **缓解措施**:
  - 设置费用告警
  - 监控数据量增长
  - 优化数据保留策略
  - 考虑降级到更便宜的方案

---

## 附录：关键配置示例

### Confluent Cloud Kafka Producer配置
```python
{
    'bootstrap.servers': '<confluent-cloud-endpoint>',
    'security.protocol': 'SASL_SSL',
    'sasl.mechanism': 'PLAIN',
    'sasl.username': '<api-key>',
    'sasl.password': '<api-secret>',
    'acks': 'all',
    'retries': 3,
    'max.in.flight.requests.per.connection': 1,
    'enable.idempotence': True
}
```

### Confluent Cloud Flink Checkpoint配置
```java
env.enableCheckpointing(300000); // 5分钟
env.getCheckpointConfig().setCheckpointingMode(CheckpointingMode.EXACTLY_ONCE);
env.getCheckpointConfig().setMinPauseBetweenCheckpoints(60000);
env.getCheckpointConfig().setCheckpointTimeout(600000);
env.getCheckpointConfig().setMaxConcurrentCheckpoints(1);
// Checkpoint存储使用Confluent Cloud S3兼容存储
```

### Supabase PostgreSQL连接字符串
```
postgresql://postgres:[YOUR-PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres
```

### Flink JDBC Sink配置
```java
JdbcSink.sink(
    "INSERT INTO lag_signals_history (...) VALUES (?, ?, ...)",
    (statement, signal) -> {
        statement.setString(1, signal.getMarket());
        // ... 设置其他字段
    },
    JdbcConnectionOptions.JdbcConnectionOptionsBuilder()
        .withUrl("jdbc:postgresql://<supabase-host>:5432/postgres")
        .withDriverName("org.postgresql.Driver")
        .withUsername("postgres")
        .withPassword("<password>")
        .build()
);
```

### Watermark配置（Flink SQL）
```sql
WATERMARK FOR published_at AS published_at - INTERVAL '5' MINUTE
```

### 等值Join配置（Flink SQL，Job 3）
```sql
SELECT
    r.market_slug,
    r.window_start,
    r.source_weighted_signal,
    p.price,
    p.price_delta,
    (r.source_weighted_signal - LAG(r.source_weighted_signal) OVER (PARTITION BY r.market_slug ORDER BY r.window_start)) as signal_delta
FROM rss.signals_hourly r
INNER JOIN polymarket.price_hourly p
ON r.market_slug = p.market_slug
AND r.window_start = p.event_time
WHERE ...
```

---

**文档版本**: v5.0
**最后更新**: 2026-01-07
**基于Review报告**: review_report_v4.md

