-- DBT Model: stg_member_hospice_mapping
-- Database: dev_dtx_gc
-- Schema: staging
-- Alias: stg_member_hospice_mapping



WITH hospice_members AS (
	SELECT DISTINCT
		memberid,
		perf_period_key,
		lineofbusiness
	FROM dev_dtx_gc.staging.stg_hospice_members
)

SELECT DISTINCT
	m.memberid,
	pp.perf_period_key,
	lob.lineofbusiness,
	CASE
		WHEN h.memberid IS NOT NULL THEN 'Yes'
		ELSE 'No'
	END AS ishospicemember
FROM dev_dtx_gc.staging.STG_MEMBER AS m
	CROSS JOIN dev_dtx_gc.staging.stg_seed_performance_period AS pp
	CROSS JOIN dev_dtx_gc.staging.stg_lineofbussiness AS lob
	LEFT JOIN
		hospice_members AS h
		ON m.memberid = h.memberid AND pp.perf_period_key = h.perf_period_key AND lob.lineofbusiness = h.lineofbusiness
WHERE pp.perf_period_name LIKE 'PP%'