-- DBT Model: stg_emcodes_per_attributionmonth
-- Database: dev_dtx_gc
-- Schema: staging
-- Alias: stg_emcodes_per_attributionmonth



SELECT
	memberid,
	LISTAGG(DISTINCT claimlinehealthservicecode, ', ') WITHIN GROUP (
		ORDER BY claimlinehealthservicecode
	) AS emcodes,
	DATE_TRUNC('month', claimlineservicestartdate) AS attributionmonth
FROM dev_dtx_gc.staging.stg_claimline
WHERE (
	claimlinehealthservicecode LIKE '992%'
	OR claimlinehealthservicecode LIKE '993%'
	OR claimlinehealthservicecode LIKE '994%'
)
GROUP BY
	memberid,
	DATE_TRUNC('month', claimlineservicestartdate)