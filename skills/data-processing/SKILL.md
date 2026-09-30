---
name: data-processing
description: Transform, clean, aggregate, and analyze structured data (CSV, JSON, Parquet, SQL). Use for data cleaning, ETL pipelines, statistical analysis, and generating insights from datasets.
license: MIT
compatibility: Requires pandas, numpy; E2B sandbox for execution
metadata:
  author: AgenticAI
  version: "1.0"
  category: analytics
allowed_tools: E2BSandbox, PythonREPL
---

# Data Processing

## Overview

This skill enables the agent to perform data processing tasks including cleaning, transformation, aggregation, analysis, and visualization of structured data from various formats.

## Instructions

### 1. Load Data
- Identify data source (CSV, JSON, Parquet, Excel, SQL, API)
- Load into appropriate structure (pandas DataFrame, Polars, SQL)
- Inspect schema, dtypes, missing values, sample rows

### 2. Clean Data
- Handle missing values (drop, fill, interpolate)
- Remove duplicates
- Fix data type issues
- Standardize formats (dates, strings, categories)
- Handle outliers (detect, cap, remove)

### 3. Transform Data
- **Filter**: Select rows based on conditions
- **GroupBy**: Aggregate by categories
- **Pivot/Unpivot**: Reshape data
- **Merge/Join**: Combine datasets
- **Feature Engineering**: Create derived columns
- **Normalization**: Scale, encode categorical variables

### 4. Analyze Data
- **Descriptive Statistics**: Mean, median, std, quantiles
- **Correlation Analysis**: Feature relationships
- **Trend Analysis**: Time series patterns
- **Segmentation**: Cohort analysis, clustering
- **Statistical Tests**: T-test, chi-square, ANOVA

### 5. Visualize (if requested)
- Generate plot specifications (matplotlib, plotly, seaborn)
- Return chart config for frontend rendering

### 6. Export Results
- Return processed DataFrame as JSON/CSV
- Generate summary report
- Create reproducible pipeline code

## Supported Operations
| Operation | Description |
|-----------|-------------|
| filter | Row selection by conditions |
| groupby | Aggregation by categories |
| aggregate | Sum, mean, count, custom funcs |
| pivot | Reshape wide/long |
| merge | Join DataFrames |
| transform | Apply functions per group |
| window | Rolling/expanding operations |

## Examples

### Example 1: Sales Analysis
**Input**: sales.csv (100k rows)
**Operations**: Filter US region, group by product, sum revenue, top 10
**Output**: Top products by revenue with chart

### Example 2: Data Cleaning
**Input**: messy_data.xlsx
**Operations**: Drop nulls, parse dates, standardize categories, dedupe
**Output**: Clean dataset + cleaning report

### Example 3: Cohort Analysis
**Input**: user_events.parquet
**Operations**: Define cohorts, track retention over time
**Output**: Retention curves + insights

### Example 4: SQL to Analysis
**Input**: SQL query result
**Operations**: Pivot, calculate growth rates, detect anomalies
**Output**: Dashboard-ready metrics