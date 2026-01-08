# Knowledge and Skills Needed for MarketLag Project

**Based on**: output_project_design_v5.md
**Generated**: 2026-01-07
**Version**: v1

---

## Learning Path Overview

This document lists the knowledge points and skills required to build the MarketLag project. Points are sequenced to form a linear learning path where prerequisites come before dependent concepts. Each point is atomic and focused on the 20/80 principle - covering the most critical knowledge for this project.

**Note**: The learner already knows general streaming concepts (Kafka, Kinesis), AWS services, Python, SQL, Java basics, and data engineering fundamentals. This path focuses on Flink-specific knowledge and project-specific integrations.

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

### 1.4 Flink Time Concepts
- Processing time vs Event time vs Ingestion time
- Event time extraction from records
- Timestamp assignment strategies
- **Why**: Critical for windowing and lag detection - project uses event time

### 1.5 Watermarks in Flink
- Watermark concept: what it represents and why needed
- Watermark generation strategies: periodic, punctuated
- Watermark propagation through operators
- Allowed lateness and late data handling
- Watermark configuration in Flink SQL: `WATERMARK FOR ... AS ...`
- **Why**: Essential for event-time windowing - project uses 5-minute watermark delay

### 1.6 Flink Windows
- Window types: tumbling, sliding, session
- Tumbling window configuration and semantics
- Window assignment: how events are assigned to windows
- Window functions: aggregate, process, reduce
- Window triggers and eviction policies
- **Why**: Project uses 1-hour tumbling windows for RSS signal aggregation

### 1.7 Flink State Management
- State types: ValueState, ListState, MapState, ReducingState
- Keyed state vs Operator state
- State backend types: MemoryStateBackend, FsStateBackend, RocksDBStateBackend
- State TTL (Time To Live) configuration
- State access patterns in ProcessFunction
- **Why**: Job 3 needs MapState to store historical max_signal_delta

### 1.8 Flink Checkpoints
- Checkpoint concept: consistent snapshots
- Checkpoint configuration: interval, mode (EXACTLY_ONCE), timeout
- Checkpoint storage: filesystem, S3-compatible
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
- **Why**: Project uses Flink SQL with Kafka tables - primary pattern

### 2.3 Schema Registry Integration
- Schema Registry concept and purpose
- Confluent Schema Registry integration with Flink
- Schema evolution and compatibility
- Avro format with Schema Registry
- JSON Schema with Schema Registry
- **Why**: Project uses Confluent Cloud Schema Registry for schema management

### 2.4 Kafka Partitioning and Flink Parallelism
- Kafka partition key and Flink keyBy relationship
- Partition assignment strategies
- Parallelism and partition distribution
- **Why**: Understanding data distribution affects performance and correctness

---

## 3. Flink SQL Advanced Features

### 3.1 Flink SQL Window Functions
- TUMBLE window function syntax
- Window aggregation: COUNT, SUM, AVG over windows
- Window start and end time extraction
- Grouping by window and key
- **Why**: Job 1 uses TUMBLE window for hourly RSS aggregation

### 3.2 Flink SQL Temporal Joins
- Regular join vs temporal join
- Event-time temporal join (AS OF SYSTEM TIME)
- Interval join: joining streams within time bounds
- **Why**: Job 3 uses equi-join (not interval join) - but understanding interval join helps

### 3.3 Flink SQL Equi-Join
- Equi-join syntax: INNER JOIN, LEFT JOIN
- Join conditions: ON clause with equality
- Join performance: broadcast vs regular join
- **Why**: Job 3 uses equi-join to combine RSS signals and prices by market_slug + window_start

### 3.4 Flink SQL User-Defined Functions (UDFs)
- Scalar UDF: simple transformations
- Table UDF: table-valued functions
- UDF registration and usage in SQL
- **Why**: May need custom functions for confidence calculation or signal processing

### 3.5 Flink SQL Time Attributes
- Event time attribute declaration
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

### 4.2 State Access Patterns
- Reading state: state.value(), state.get()
- Writing state: state.update(), state.add()
- State initialization: checking if state exists
- **Why**: Job 3 needs to read/write max_signal_delta state

### 4.3 State TTL Configuration
- TTL configuration: when to expire state
- TTL update strategies: OnCreateAndWrite, OnReadAndWrite
- State cleanup: expired state removal
- **Why**: Project uses 7-day TTL for historical state

---

## 5. Flink External System Integration

### 5.1 Flink JDBC Connector
- JDBC sink configuration
- JDBC table connector for reading/writing
- Batch insert configuration: batch size, flush interval
- Connection pool management
- **Why**: Project writes lag_signals to Supabase PostgreSQL via JDBC sink

### 5.2 Flink JDBC Sink Best Practices
- Idempotent writes: UPSERT vs INSERT
- Error handling: retry logic, dead letter handling
- Transaction management
- Connection string configuration
- **Why**: Ensuring reliable writes to Supabase

---

## 6. Confluent Cloud Flink

### 6.1 Confluent Cloud Overview
- Confluent Cloud architecture: managed Kafka and Flink
- Confluent Cloud vs self-hosted: differences and benefits
- Confluent Cloud pricing model: CKU (Kafka), CFU (Flink)
- **Why**: Project uses Confluent Cloud for production deployment

### 6.2 Confluent Cloud Flink Environment
- Flink environment creation in Confluent Cloud
- Flink version selection (2.2.0)
- Compute unit configuration (CFU)
- State backend configuration (RocksDB)
- Checkpoint storage configuration
- **Why**: Understanding deployment environment

### 6.3 Deploying Flink Jobs to Confluent Cloud
- Job submission: JAR upload, SQL script upload
- Job configuration: parallelism, checkpoint interval
- Job monitoring: UI, metrics, logs
- Job update and versioning
- **Why**: Operational knowledge for deploying and maintaining jobs

### 6.4 Confluent Cloud Monitoring
- Flink job metrics: throughput, latency, checkpoint success rate
- Kafka metrics: consumer lag, throughput
- Alerting configuration
- **Why**: Monitoring job health and performance

---

## 7. Data Source Integration

### 7.1 RSS Feed Processing
- RSS feed structure: items, title, link, published_at
- RSS parsing libraries: feedparser (Python), rss-parser
- RSS item deduplication strategies: guid, link, hash
- Timezone handling: converting published_at to UTC
- **Why**: Project ingests RSS feeds from RSS.app

### 7.2 Polymarket API Integration
- Polymarket API architecture: Gamma API vs CLOB API
- Gamma API: market metadata, token IDs extraction
- CLOB API: price data retrieval, batch vs single token queries
- API authentication: public endpoints (MVP)
- Rate limiting and error handling
- **Why**: Project fetches market prices from Polymarket

### 7.3 Price Delta Calculation
- Price delta computation: current_price - prev_price
- State management for previous price: DynamoDB, S3, or in-memory
- First-time handling: delta = 0 for first data point
- **Why**: Project calculates price_delta in Producer (Lambda), not in Flink

---

## 8. AWS Lambda and EventBridge

### 8.1 AWS Lambda for Data Producers
- Lambda function structure: handler, dependencies
- Lambda layers for shared dependencies
- Lambda environment variables and configuration
- Lambda timeout and memory configuration
- **Why**: RSS and Polymarket producers run as Lambda functions

### 8.2 AWS EventBridge Scheduling
- EventBridge rule creation: cron expressions
- EventBridge target configuration: Lambda function
- EventBridge rule frequency: every 15 minutes (RSS), hourly (Polymarket)
- **Why**: Triggers data producers on schedule

### 8.3 Lambda-Kafka Integration
- Kafka producer in Lambda: confluent-kafka, kafka-python
- Confluent Cloud authentication: API key + secret
- Error handling and retry logic in Lambda
- Dead letter queue: failed records handling
- **Why**: Lambda functions write to Confluent Cloud Kafka

---

## 9. Timezone and Time Handling

### 9.1 UTC Standardization
- Why UTC: avoiding timezone confusion in distributed systems
- Timezone conversion: local time → UTC
- ISO 8601 format: standard timestamp representation
- **Why**: Project standardizes all timestamps to UTC

### 9.2 Event Time Alignment
- Hour alignment: rounding timestamps to hour boundaries
- Window alignment: ensuring windows align with business hours
- Timezone-aware processing: handling daylight saving time
- **Why**: Project aligns windows to UTC hours for consistent processing

---

## 10. Error Handling and Data Quality

### 10.1 Dead Letter Queue Pattern
- DLQ concept: storing failed records
- DLQ implementation: Kafka topic, SQS, S3
- DLQ monitoring and alerting
- DLQ record analysis and reprocessing
- **Why**: Project uses DLQ topics for failed RSS and Polymarket records

### 10.2 Data Validation in Streaming
- Schema validation: using Schema Registry
- Data range validation: price ∈ [0,1]
- Timestamp validation: not future, not too old
- Missing field handling: default values, skipping records
- **Why**: Ensuring data quality before processing

### 10.3 Exception Handling in Flink
- Try-catch in operators
- Side outputs for error records
- Exception handling in ProcessFunction
- **Why**: Graceful handling of malformed data

---

## 11. Testing Flink Applications

### 11.1 Flink Local Testing
- LocalEnvironment setup for testing
- Test data generation: creating test streams
- Unit testing Flink operators
- Testing stateful functions: state verification
- **Why**: Validating logic before deployment

### 11.2 Flink Integration Testing
- Docker Compose setup: Kafka, PostgreSQL, Schema Registry
- End-to-end testing: source → Flink → sink
- Test data replay: using historical data
- **Why**: Validating complete data pipeline

### 11.3 Flink Checkpoint Testing
- Testing checkpoint creation and recovery
- Simulating failures: killing tasks, network partitions
- Verifying state recovery correctness
- **Why**: Ensuring fault tolerance works

---

## 12. Monitoring and Observability

### 12.1 Flink Metrics
- Built-in metrics: throughput, latency, checkpoint duration
- Custom metrics: registering custom counters, gauges
- Metrics export: Prometheus, InfluxDB
- **Why**: Monitoring job performance and health

### 12.2 Grafana Dashboard Creation
- Grafana data source configuration: PostgreSQL, Prometheus
- Panel types: time series, histogram, scatter plot, table
- SQL queries for time series: date_trunc for hourly aggregation
- Dashboard organization and layout
- **Why**: Project visualizes lag signals and system health in Grafana

### 12.3 Alerting Configuration
- Grafana alert rules: threshold-based alerts
- Alert notification channels: email, Slack
- Alert evaluation and firing
- **Why**: Getting notified of system issues or anomalies

---

## 13. Project-Specific Concepts

### 13.1 Lag Detection Algorithm
- Signal delta calculation: signal(t) - signal(t-1)
- Price delta comparison: abs(price_delta) < threshold
- Lag flag logic: signal_delta > threshold AND abs(price_delta) < threshold
- **Why**: Core business logic of the project

### 13.2 Confidence Score Calculation
- Confidence formula: weighted combination of factors
- Factor normalization: scaling to [0,1] range
- Historical baseline: using max_signal_delta for normalization
- **Why**: Quantifying reliability of lag signals

### 13.3 Keyword Scoring System
- Keyword weights: positive (Fed, rate, hike) vs negative (dovish)
- Keyword occurrence counting
- Keyword score aggregation: SUM(weight × count)
- **Why**: Converting RSS content into numerical signals

### 13.4 Source Weighting
- Source credibility weights: Reuters=1.0, Bloomberg=0.9, others=0.7
- Source-weighted signal: weighted average of article scores
- **Why**: Accounting for source reliability in signal calculation

---

## 14. Operational Knowledge

### 14.1 Flink Job Deployment Workflow
- Code compilation: Maven/Gradle build
- JAR packaging: including dependencies
- Job submission: CLI, UI, API
- Job configuration management: environment-specific configs
- **Why**: Deploying jobs to Confluent Cloud

### 14.2 Flink Job Troubleshooting
- Common issues: checkpoint failures, backpressure, OOM
- Debugging techniques: logs, metrics, UI inspection
- Performance tuning: parallelism, state backend, checkpoint interval
- **Why**: Maintaining healthy production jobs

### 14.3 Cost Optimization
- Confluent Cloud cost factors: CKU, CFU, storage, network
- Cost monitoring: tracking usage and spending
- Optimization strategies: right-sizing, data retention tuning
- **Why**: Managing project costs within budget

---

## 15. Advanced Topics (Optional but Helpful)

### 15.1 Flink CEP (Complex Event Processing)
- Pattern definition: detecting event sequences
- Pattern matching: detecting lag patterns
- **Why**: Alternative approach for lag detection (not used in MVP)

### 15.2 Flink Async I/O
- AsyncFunction for external lookups
- Async I/O configuration: capacity, timeout
- **Why**: If needing to enrich data with external APIs

### 15.3 Flink State Backend Tuning
- RocksDB configuration: memory, write buffers
- State backend selection: when to use which
- **Why**: Optimizing state performance for large state

---

## Learning Sequence Summary

**Phase 1: Flink Fundamentals (Days 1-5)**
- 1.1-1.8: Core Flink concepts, time, watermarks, windows, state, checkpoints

**Phase 2: Flink-Kafka Integration (Days 6-8)**
- 2.1-2.4: Kafka connectors, Schema Registry, partitioning

**Phase 3: Flink SQL (Days 9-12)**
- 3.1-3.5: SQL window functions, joins, UDFs, time attributes

**Phase 4: Stateful Processing (Days 13-14)**
- 4.1-4.3: ProcessFunction, state access, TTL

**Phase 5: External Integrations (Days 15-17)**
- 5.1-5.2: JDBC connector, Supabase integration
- 6.1-6.4: Confluent Cloud deployment
- 7.1-7.3: Data source APIs

**Phase 6: Infrastructure (Days 18-19)**
- 8.1-8.3: AWS Lambda, EventBridge
- 9.1-9.2: Timezone handling

**Phase 7: Quality and Testing (Days 20-22)**
- 10.1-10.3: Error handling, data validation
- 11.1-11.3: Testing strategies

**Phase 8: Monitoring and Operations (Days 23-25)**
- 12.1-12.3: Metrics, Grafana, alerting
- 14.1-14.3: Deployment, troubleshooting, cost optimization

**Phase 9: Project Implementation (Days 26-30)**
- 13.1-13.4: Project-specific algorithms and logic
- Building and deploying the complete system

---

## Notes

- **Atomic Learning Points**: Each numbered item is a focused, atomic learning unit
- **Prerequisites**: Items are sequenced - later items depend on earlier ones
- **20/80 Focus**: Prioritizes knowledge most critical for this project
- **Functional + Operational**: Covers both "how to use" and "how to deploy/monitor"
- **Assumed Knowledge**: Learner already knows Kafka basics, AWS, Python, SQL, Java - this path focuses on Flink-specific and project-specific knowledge

