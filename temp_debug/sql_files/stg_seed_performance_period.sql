-- DBT Model: stg_seed_performance_period
-- Database: dev_dtx_gc
-- Schema: staging
-- Alias: stg_seed_performance_period



SELECT
	perf_period_key,
	perf_period_name,
	perf_period_name_range,
	ccf_version,
	CAST(perf_period_start_date AS date) AS perf_period_start_date,
	CAST(perf_period_end_date AS date) AS perf_period_end_date
FROM dev_dtx_gc.anthemreporting_seed.seed_performance_period