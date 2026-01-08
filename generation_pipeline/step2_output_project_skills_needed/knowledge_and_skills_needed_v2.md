# Knowledge and Skills Needed for MarketLag Project

**Based on**: output_project_design_v5.md
**Generated**: 2026-01-07
**Version**: v2

---

## Learning Path Overview

This document lists the knowledge points and skills required to build the MarketLag project. Points are sequenced to form a linear learning path where prerequisites come before dependent concepts. Each point is atomic and focused on the 20/80 principle - covering the most critical knowledge for this project.

---

## Assumed Knowledge vs Knowledge to Learn

### ✅ Assumed Knowledge (Learner Already Has)
The learner is an experienced data engineer (10 years) with expertise in:
- **Streaming Basics**: Kafka, Kinesis, event-driven architecture
- **Cloud Platforms**: AWS (Lambda, EventBridge, S3, DynamoDB), GCP, Azure
- **Programming**: Python, SQL, Java basics, TypeScript, Scala
- **Data Engineering**: ETL/ELT pipelines, data quality, data warehousing
- **Big Data**: Apache Spark, Hadoop ecosystem
- **DevOps**: Docker, Kubernetes, Terraform, CI/CD
- **General Concepts**: Timezone handling, API integration, error handling patterns

### 📚 Knowledge to Learn (This Path Focuses On)
- **Flink-Specific**: Flink architecture, APIs, time concepts, state management
- **Flink-Kafka Integration**: Flink Kafka connectors, Schema Registry integration
- **Flink SQL**: Table API, SQL syntax, window functions, joins
- **Confluent Cloud**: Managed Flink deployment and operations
- **Project-Specific**: Lag detection algorithms, signal processing, confidence scoring
- **Operational Details**: Specific deployment patterns, configuration examples

---

## 1. Flink Fundamentals

### 1.1 Flink Architecture and Execution Model
- Flink cluster architecture: JobManager, TaskManager, slots
- Flink job lifecycle: submission, scheduling, execution
- Parallelism and task distribution
- LocalEnvironment vs RemoteEnvironment vs Confluent Cloud environment
- **Why**: Foundation for understanding how Flink jobs run and how to deploy them

### 1.2 Flink DataStream API Basics
- DataStream creation from sources (Kafka, collections, files)
- Basic transformations: map, filter, flatMap, keyBy
- DataStream chaining and operator fusion
- **Why**: Core API for building streaming pipelines

### 1.3 Flink Table API and SQL
- Table API vs DataStream API: when to use which
- Creating tables from DataStreams
- Flink SQL syntax and capabilities
- Registering tables and views
- **Why**: Project uses Flink SQL for Job 1, 2, and 3 - primary interface

### 1.4 Flink Time Concepts and Timezone Handling
- Processing time vs Event time vs Ingestion time
- Event time extraction from records
- Timestamp assignment strategies
- **UTC Standardization**: Why UTC, timezone conversion (local → UTC), ISO 8601 format
- **Event Time Alignment**: Hour alignment, window alignment, timezone-aware processing
- **Why**: Critical for windowing and lag detection - project uses event time with UTC standardization

### 1.5 Watermarks in Flink
- Watermark concept: what it represents and why needed
- Watermark generation strategies: periodic, punctuated
- Watermark propagation through operators
- Allowed lateness and late data handling
- Watermark configuration in Flink SQL: `WATERMARK FOR published_at AS published_at - INTERVAL '5' MINUTE`
- **Why**: Essential for event-time windowing - project uses 5-minute watermark delay

### 1.6 Flink Windows
- Window types: tumbling, sliding, session
- Tumbling window configuration and semantics
- Window assignment: how events are assigned to windows
- Window functions: aggregate, process, reduce
- Window triggers and eviction policies
- **Why**: Project uses 1-hour tumbling windows for RSS signal aggregation

### 1.7 Flink State Types
- ValueState: single value per key
- ListState: list of values per key
- MapState: key-value map per key (used in Job 3 for max_signal_delta)
- ReducingState: aggregated value per key
- Keyed state vs Operator state
- **Why**: Understanding state types helps choose the right one for each use case

### 1.8 Flink State Backend
- State backend types: MemoryStateBackend, FsStateBackend, RocksDBStateBackend
- State backend selection: when to use which
- RocksDB configuration: memory, write buffers (used in Confluent Cloud)
- State TTL (Time To Live) configuration
- **Why**: Project uses RocksDB in Confluent Cloud for state storage

### 1.9 Flink State Access Patterns
- State access in ProcessFunction: state.value(), state.get()
- State updates: state.update(), state.add()
- State initialization: checking if state exists
- **Why**: Job 3 needs to read/write max_signal_delta state

### 1.10 Flink Checkpoints
- Checkpoint concept: consistent snapshots
- Checkpoint configuration: interval, mode (EXACTLY_ONCE), timeout
- Checkpoint storage: filesystem, S3-compatible (Confluent Cloud uses S3)
- Checkpoint recovery: how Flink restores from checkpoints
- Savepoints vs checkpoints
- **Why**: Critical for fault tolerance - project uses 5-minute checkpoints

---

## 2. Flink-Kafka Integration

### 2.1 Flink Kafka Connector
- Kafka consumer configuration in Flink
- Kafka producer configuration in Flink
- Kafka source: FlinkKafkaConsumer (deprecated) vs KafkaSource (new)
- Kafka sink: FlinkKafkaProducer vs KafkaSink
- Consumer group management and offset handling
- **Why**: All data flows through Kafka - core integration

### 2.2 Flink Kafka Table Connector
- Kafka table connector configuration in Flink SQL
- Schema definition: format (JSON, Avro), schema registry integration
- Kafka topic as Flink table: CREATE TABLE ... WITH (...)
- Reading from Kafka: SELECT FROM kafka_table
- Writing to Kafka: INSERT INTO kafka_table
- **Example CREATE TABLE**:
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
- **Why**: Project uses Flink SQL with Kafka tables - primary pattern

### 2.3 Schema Registry Integration
- Schema Registry concept and purpose
- Confluent Schema Registry integration with Flink
- Schema evolution and compatibility
- Avro format with Schema Registry
- JSON Schema with Schema Registry
- **Configuration**: Adding Schema Registry URL and credentials to table connector
- **Why**: Project uses Confluent Cloud Schema Registry for schema management

### 2.4 Kafka Partitioning and Flink Parallelism
- Kafka partition key and Flink keyBy relationship
- Partition assignment strategies
- Parallelism and partition distribution
- **Project Pattern**: Using `market_slug` as partition key for `rss.events`, `market_slug|outcome` for `polymarket.price_hourly`
- **Why**: Understanding data distribution affects performance and correctness

---

## 3. Flink SQL Advanced Features

### 3.1 Flink SQL Window Functions
- TUMBLE window function syntax
- Window aggregation: COUNT, SUM, AVG over windows
- Window start and end time extraction
- Grouping by window and key
- **Example (Job 1)**:
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
- **Why**: Job 1 uses TUMBLE window for hourly RSS aggregation

### 3.2 Flink SQL Temporal Joins
- Regular join vs temporal join
- Event-time temporal join (AS OF SYSTEM TIME)
- Interval join: joining streams within time bounds
- **Why**: Understanding different join types helps choose the right one (project uses equi-join, not interval join)

### 3.3 Flink SQL Equi-Join
- Equi-join syntax: INNER JOIN, LEFT JOIN
- Join conditions: ON clause with equality
- Join performance: broadcast vs regular join
- **Example (Job 3)**:
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
- **Why**: Job 3 uses equi-join to combine RSS signals and prices by market_slug + window_start

### 3.4 Flink SQL Window Aggregations with LAG
- LAG function: accessing previous row values
- LAG with OVER clause: windowed lag calculation
- PARTITION BY and ORDER BY in window functions
- **Why**: Job 3 uses LAG to calculate signal_delta (current - previous)

### 3.5 Flink SQL User-Defined Functions (UDFs)
- Scalar UDF: simple transformations
- Table UDF: table-valued functions
- UDF registration and usage in SQL
- **Why**: May need custom functions for confidence calculation or signal processing

### 3.6 Flink SQL Time Attributes
- Event time attribute declaration in CREATE TABLE
- Processing time attribute declaration
- Time attribute propagation through queries
- **Why**: Required for windowing and watermark generation

---

## 4. Flink Stateful Processing

### 4.1 ProcessFunction for Stateful Logic
- ProcessFunction interface: processElement, onTimer
- KeyedProcessFunction for keyed state access
- Timer registration and firing
- **Why**: Job 3 may need ProcessFunction for confidence calculation with historical state

### 4.2 State TTL Configuration
- TTL configuration: when to expire state
- TTL update strategies: OnCreateAndWrite, OnReadAndWrite
- State cleanup: expired state removal
- **Example**: Setting 7-day TTL for MapState storing max_signal_delta
- **Why**: Project uses 7-day TTL for historical state

---

## 5. Flink External System Integration

### 5.1 Flink JDBC Connector Configuration
- JDBC sink configuration
- JDBC table connector for reading/writing
- Batch insert configuration: batch size, flush interval
- Connection pool management
- **Supabase Connection String Format**:
  ```
  jdbc:postgresql://db.<project-ref>.supabase.co:5432/postgres
  ```
- **Example CREATE TABLE for JDBC Sink**:
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
- **Why**: Project writes lag_signals to Supabase PostgreSQL via JDBC sink

### 5.2 Flink JDBC Sink Best Practices
- Idempotent writes: UPSERT vs INSERT
- Error handling: retry logic, dead letter handling
- Transaction management
- Handling connection failures: retry with exponential backoff
- **Why**: Ensuring reliable writes to Supabase

---

## 6. Confluent Cloud Flink

### 6.1 Confluent Cloud Overview
- Confluent Cloud architecture: managed Kafka and Flink
- Confluent Cloud vs self-hosted: differences and benefits
- Confluent Cloud pricing model: CKU (Kafka), CFU (Flink)
- **Why**: Project uses Confluent Cloud for production deployment

### 6.2 Confluent Cloud Flink Environment
- Flink environment creation in Confluent Cloud UI
- Flink version selection (2.2.0)
- Compute unit configuration (CFU): 2 CFU for MVP
- State backend configuration (RocksDB): automatic in Confluent Cloud
- Checkpoint storage configuration: S3-compatible storage
- **Why**: Understanding deployment environment

### 6.3 Deploying Flink Jobs to Confluent Cloud
- **Job Submission Methods**:
  - UI: Upload JAR or SQL script through Confluent Cloud UI
  - CLI: Using `confluent flink job create` command
  - API: REST API for programmatic deployment
- **Job Configuration**:
  - Parallelism: 2 (for MVP)
  - Checkpoint interval: 300000 (5 minutes)
  - Checkpoint mode: EXACTLY_ONCE
- **Job Monitoring**: UI dashboard, metrics, logs
- **Job Update**: Versioning, rolling updates
- **Why**: Operational knowledge for deploying and maintaining jobs

### 6.4 Confluent Cloud Monitoring
- Flink job metrics: throughput, latency, checkpoint success rate
- Kafka metrics: consumer lag, throughput
- Alerting configuration: setting up alerts for checkpoint failures, high lag
- **Why**: Monitoring job health and performance

---

## 7. Data Source Integration

### 7.1 RSS Feed Processing
- RSS feed structure: items, title, link, published_at
- RSS parsing libraries: feedparser (Python), rss-parser
- RSS item deduplication strategies: guid, link, hash
- Timezone handling: converting published_at to UTC
- **RSS.app API**: `https://rss.app/feeds/v1.1/{feed_id}.json`
- **Why**: Project ingests RSS feeds from RSS.app

### 7.2 Polymarket API Integration
- Polymarket API architecture: Gamma API vs CLOB API
- **Gamma API**: `GET https://gamma-api.polymarket.com/markets/slug/{slug}` - market metadata, token IDs extraction
- **CLOB API**: `POST https://clob.polymarket.com/prices` with `{"token_ids": [...]}` - price data retrieval
- API authentication: public endpoints (MVP)
- Rate limiting and error handling
- **Why**: Project fetches market prices from Polymarket

### 7.3 Computation Placement: Producer vs Flink
- **Decision Factor**: Where to place computation logic
- **Producer-side computation**: price_delta calculation in Lambda (before Kafka)
  - Pros: Reduces Flink state complexity, simpler Flink job
  - Cons: Requires external state storage (DynamoDB/S3)
- **Flink-side computation**: Computation in Flink operators
  - Pros: Centralized logic, Flink state management
  - Cons: More complex Flink state, larger state size
- **Project Choice**: price_delta calculated in Producer (Lambda) using DynamoDB for previous price
- **Why**: Understanding trade-offs helps make architectural decisions

### 7.4 Price Delta Calculation Implementation
- Price delta computation: current_price - prev_price
- State management for previous price: DynamoDB, S3, or in-memory
- First-time handling: delta = 0 for first data point
- **DynamoDB Pattern**: Store `{market_slug|outcome: prev_price}` with TTL
- **Why**: Project calculates price_delta in Producer (Lambda), not in Flink

---

## 8. AWS Lambda and EventBridge

### 8.1 AWS Lambda for Data Producers
- Lambda function structure: handler, dependencies
- Lambda layers for shared dependencies: packaging kafka-python, confluent-kafka
- Lambda environment variables and configuration
- Lambda timeout and memory configuration: 5 minutes timeout, 256MB memory
- **Why**: RSS and Polymarket producers run as Lambda functions

### 8.2 AWS EventBridge Scheduling
- EventBridge rule creation: cron expressions
- **RSS Producer Cron**: `*/15 * * * ? *` (every 15 minutes)
- **Polymarket Producer Cron**: `0 * * * ? *` (every hour at minute 0)
- EventBridge target configuration: Lambda function
- **Why**: Triggers data producers on schedule

### 8.3 Lambda-Kafka Integration
- Kafka producer in Lambda: confluent-kafka, kafka-python
- **Confluent Cloud Authentication**:
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
- Error handling and retry logic in Lambda
- Dead letter queue: failed records handling (DLQ Kafka topics)
- **Why**: Lambda functions write to Confluent Cloud Kafka

---

## 9. Error Handling and Data Quality

### 9.1 Dead Letter Queue Pattern
- DLQ concept: storing failed records
- DLQ implementation: Kafka topic (`dlq.rss.events`, `dlq.polymarket.price_hourly`), SQS, S3
- DLQ monitoring and alerting
- DLQ record analysis and reprocessing
- **Why**: Project uses DLQ topics for failed RSS and Polymarket records

### 9.2 Data Validation in Streaming
- Schema validation: using Schema Registry
- Data range validation: price ∈ [0,1]
- Timestamp validation: not future, not too old
- Missing field handling: default values, skipping records
- **Why**: Ensuring data quality before processing

### 9.3 Exception Handling in Flink
- Try-catch in operators
- Side outputs for error records
- Exception handling in ProcessFunction
- **Why**: Graceful handling of malformed data

### 9.4 Project-Specific Error Handling Patterns
- **Missing RSS Data in Window**: Skip the window (no output), log warning
- **Missing Price Data in Join**: Use LEFT JOIN to handle missing prices, set price_delta = 0
- **API Rate Limits in Lambda**: Exponential backoff retry, record to DLQ after max retries
- **Schema Registry Evolution**: Handle schema compatibility, version management
- **Why**: Specific error scenarios in the project

---

## 10. Testing Flink Applications

### 10.1 Flink Local Testing
- LocalEnvironment setup for testing
- Test data generation: creating test streams
- Unit testing Flink operators
- Testing stateful functions: state verification
- **Why**: Validating logic before deployment

### 10.2 Flink Integration Testing
- Docker Compose setup: Kafka, PostgreSQL, Schema Registry
- End-to-end testing: source → Flink → sink
- Test data replay: using historical data
- **Why**: Validating complete data pipeline

### 10.3 Flink Checkpoint Testing
- Testing checkpoint creation and recovery
- Simulating failures: killing tasks, network partitions
- Verifying state recovery correctness
- **Why**: Ensuring fault tolerance works

### 10.4 Project-Specific Testing Scenarios
- **Testing Window Aggregation (Job 1)**: Verify mention_count, keyword_score, source_weighted_signal calculation
- **Testing Join Correctness (Job 3)**: Verify equi-join matches correct window_start with event_time
- **Testing State Recovery**: Verify max_signal_delta state is correctly restored after failure
- **Testing Watermark Behavior**: Verify late data handling, window triggering with watermarks
- **Testing Lag Detection Logic**: Verify signal_delta > 1.0 AND abs(price_delta) < 0.02 correctly flags lag
- **Why**: Validating project-specific functionality

---

## 11. Monitoring and Observability

### 11.1 Flink Metrics
- Built-in metrics: throughput, latency, checkpoint duration
- Custom metrics: registering custom counters, gauges
- Metrics export: Prometheus, InfluxDB
- **Why**: Monitoring job performance and health

### 11.2 Grafana Dashboard Creation
- Grafana data source configuration: PostgreSQL, Prometheus
- Panel types: time series, histogram, scatter plot, table
- **SQL Query Example (Hourly Aggregation)**:
  ```sql
  SELECT
    date_trunc('hour', detected_at) as hour,
    COUNT(*) as lag_count
  FROM lag_signals_history
  WHERE lag_flag = true
  GROUP BY date_trunc('hour', detected_at)
  ORDER BY hour
  ```
- Dashboard organization and layout
- **Why**: Project visualizes lag signals and system health in Grafana

### 11.3 Alerting Configuration
- Grafana alert rules: threshold-based alerts
- Alert notification channels: email, Slack
- Alert evaluation and firing
- **Project Alerts**: Lag signal count = 0 (unexpected), Flink job failure, high consumer lag
- **Why**: Getting notified of system issues or anomalies

---

## 12. Project-Specific Concepts

### 12.1 Lag Detection Algorithm
- Signal delta calculation: signal(t) - signal(t-1)
- Price delta comparison: abs(price_delta) < threshold (0.02 = 2%)
- Lag flag logic: signal_delta > 1.0 AND abs(price_delta) < 0.02
- **Why**: Core business logic of the project

### 12.2 Confidence Score Calculation Formula
- **Formula**:
  ```
  confidence = min(1.0,
    (signal_delta / max_signal_delta) * 0.5 +
    (1 - |price_delta|) * 0.3 +
    (source_weight_avg) * 0.2
  )
  ```
- Factor normalization: scaling to [0,1] range
- Historical baseline: using max_signal_delta for normalization (stored in MapState)
- **Why**: Quantifying reliability of lag signals

### 12.3 Keyword Scoring System
- Keyword weights: positive (Fed=2.0, rate=1.5, hike=2.0) vs negative (dovish=-1.5)
- Keyword occurrence counting
- Keyword score aggregation: SUM(weight × count) per article
- **Why**: Converting RSS content into numerical signals

### 12.4 Source Weighting and Signal Calculation
- Source credibility weights: Reuters=1.0, Bloomberg=0.9, others=0.7
- Article score: SUM(keyword_scores for that article)
- Source-weighted signal: SUM(article_score × source_weight) / COUNT(*) per window
- **Formula**: `source_weighted_signal = AVG(article_score × source_weight)`
- **Why**: Accounting for source reliability in signal calculation

### 12.5 Join Type Selection: Equi-Join vs Interval Join
- **Equi-Join**: Exact match on join keys (market_slug + window_start = event_time)
  - Used in project: window_start and event_time are both aligned to UTC hours
  - Pros: Simple, efficient, exact matching
- **Interval Join**: Join within time bounds (e.g., ±5 minutes)
  - Not used in project: data is already aligned to hours
  - Pros: Handles slight misalignment
- **Decision Factor**: Data alignment - if data is pre-aligned, equi-join is better
- **Why**: Understanding when to use which join type

---

## 13. Operational Knowledge

### 13.1 Flink Job Deployment Workflow
- Code compilation: Maven/Gradle build
- JAR packaging: including dependencies (fat JAR)
- Job submission: CLI, UI, API
- Job configuration management: environment-specific configs
- **Why**: Deploying jobs to Confluent Cloud

### 13.2 Flink Job Troubleshooting
- Common issues: checkpoint failures, backpressure, OOM
- Debugging techniques: logs, metrics, UI inspection
- Performance tuning: parallelism, state backend, checkpoint interval
- **Why**: Maintaining healthy production jobs

### 13.3 Cost Optimization and Resource Planning
- Confluent Cloud cost factors: CKU, CFU, storage, network
- **CFU Estimation**: 2 CFU for MVP (based on data volume < 1 MB/s)
- Cost monitoring: tracking usage and spending in Confluent Cloud UI
- Optimization strategies: right-sizing, data retention tuning (7-30 days)
- **Cost Alerts**: Setting up billing alerts
- **Why**: Managing project costs within budget ($775-1,293/month for MVP)

---

## 14. Advanced Topics (Optional but Helpful)

### 14.1 Flink CEP (Complex Event Processing)
- Pattern definition: detecting event sequences
- Pattern matching: detecting lag patterns
- **Why**: Alternative approach for lag detection (not used in MVP)

### 14.2 Flink Async I/O
- AsyncFunction for external lookups
- Async I/O configuration: capacity, timeout
- **Why**: If needing to enrich data with external APIs

---

## Learning Sequence Summary

**Phase 1: Flink Fundamentals (Days 1-5)**
- 1.1-1.3: Core Flink architecture, DataStream API, Table API/SQL
- 1.4: Time concepts and timezone handling (merged)
- 1.5-1.6: Watermarks and windows
- 1.7-1.9: State types, state backend, state access
- 1.10: Checkpoints

**Phase 2: Flink-Kafka Integration (Days 6-8)**
- 2.1-2.4: Kafka connectors, Schema Registry, partitioning

**Phase 3: Flink SQL (Days 9-12)**
- 3.1-3.6: SQL window functions, joins, UDFs, time attributes

**Phase 4: Stateful Processing (Days 13-14)**
- 4.1-4.2: ProcessFunction, state TTL

**Phase 5: External Integrations (Days 15-17)**
- 5.1-5.2: JDBC connector, Supabase integration (with examples)
- 6.1-6.4: Confluent Cloud deployment (with specific steps)
- 7.1-7.4: Data source APIs, computation placement patterns

**Phase 6: Infrastructure (Days 18-19)**
- 8.1-8.3: AWS Lambda, EventBridge (with cron examples)
- Timezone already covered in 1.4

**Phase 7: Quality and Testing (Days 20-22)**
- 9.1-9.4: Error handling, data validation, project-specific patterns
- 10.1-10.4: Testing strategies, project-specific scenarios

**Phase 8: Monitoring and Operations (Days 23-25)**
- 11.1-11.3: Metrics, Grafana (with SQL examples), alerting
- 13.1-13.3: Deployment, troubleshooting, cost optimization

**Phase 9: Project Implementation (Days 26-30)**
- 12.1-12.5: Project-specific algorithms, formulas, join type selection
- Building and deploying the complete system

---

## Notes

- **Atomic Learning Points**: Each numbered item is a focused, atomic learning unit
- **Prerequisites**: Items are sequenced - later items depend on earlier ones
- **20/80 Focus**: Prioritizes knowledge most critical for this project
- **Functional + Operational**: Covers both "how to use" and "how to deploy/monitor"
- **Specific Examples**: Includes code snippets, configuration examples, and formulas from the project
- **Assumed Knowledge**: Explicitly listed at the top - learner already knows Kafka basics, AWS, Python, SQL, Java
- **MVP Focus**: Emphasizes knowledge needed for MVP, advanced topics marked as optional

