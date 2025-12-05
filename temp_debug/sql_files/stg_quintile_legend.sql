-- DBT Model: stg_quintile_legend
-- Database: dev_dtx_gc
-- Schema: staging
-- Alias: stg_quintile_legend



SELECT
	qmid,
	'Performance (Commercial)' AS type,
	qmname,
	'0% to ' || (quintile_1 * 100) || '%' AS quintile_1,
	(quintile_1 * 100)
	+ 0.01
	|| '% to '
	|| (quintile_2 * 100)
	|| '%' AS quintile_2,
	(quintile_2 * 100)
	+ 0.01
	|| '% to '
	|| (quintile_3 * 100)
	|| '%' AS quintile_3,
	(quintile_3 * 100)
	+ 0.01
	|| '% to '
	|| (quintile_4 * 100)
	|| '%' AS quintile_4,
	(quintile_4 * 100)
	+ 0.01
	|| '% to '
	|| (quintile_5 * 100)
	|| '%' AS quintile_5
FROM dev_dtx_gc.staging.stg_seed_quality_measures
WHERE qmid IN (1, 2, 3, 4, 14)

UNION ALL

SELECT
	qmid,
	'Performance (Medicare Advantage)' AS type,
	qmname,
	'0% to ' || (quintile_1_ma * 100) || '%' AS quintile_1,
	(quintile_1_ma * 100)
	+ 0.01
	|| '% to '
	|| (quintile_2_ma * 100)
	|| '%' AS quintile_2,
	(quintile_2_ma * 100)
	+ 0.01
	|| '% to '
	|| (quintile_3_ma * 100)
	|| '%' AS quintile_3,
	(quintile_3_ma * 100)
	+ 0.01
	|| '% to '
	|| (quintile_4_ma * 100)
	|| '%' AS quintile_4,
	(quintile_4_ma * 100)
	+ 0.01
	|| '% to '
	|| (quintile_5_ma * 100)
	|| '%' AS quintile_5
FROM dev_dtx_gc.staging.stg_seed_quality_measures
WHERE qmid IN (1, 2, 3, 4, 14)

UNION ALL

SELECT
	qmid,
	'Points' AS type,
	qmname,
	TO_VARCHAR(group1score) AS quintile_1,
	TO_VARCHAR(group2score) AS quintile_2,
	TO_VARCHAR(group3score) AS quintile_3,
	TO_VARCHAR(group4score) AS quintile_4,
	TO_VARCHAR(group5score) AS quintile_5
FROM dev_dtx_gc.staging.stg_seed_quality_measures
WHERE qmid IN (1, 2, 3, 4, 14)