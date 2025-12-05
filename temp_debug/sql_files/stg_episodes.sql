-- DBT Model: stg_episodes
-- Database: dev_dtx_gc
-- Schema: staging
-- Alias: stg_episodes



WITH episodes AS (
	
	-- removed code becauae dbt test was using as code
	SELECT
		me.memberid,
		me.episode_start_date,
		me.episode_end_date,
		me.oncologist_tin,
		me.oncologist_npi,
		me.performanceperiodstartdate,
		me.performanceperiodenddate,
		me.contractname,
		me.lineofbusinessidentifier AS lineofbusiness
	FROM dev_dtx_gc.IC1.MASTEREPISODE AS me
),

episode_attributed_tin AS (
	SELECT
		e.memberid,
		e.episode_start_date,
		e.episode_end_date,
		a.attributedprovidertaxid,
		a.attributedproviderorganizationname,
		a.attributednpiproviderid
	FROM episodes AS e
		LEFT JOIN dev_dtx_gc.IC1.ATTRIBUTION AS a
			ON e.memberid = a.memberid AND a.attributionperiodbegindate BETWEEN e.episode_start_date AND e.episode_end_date
	WHERE a.attributedprovidertaxid IS NOT NULL
	QUALIFY ROW_NUMBER() OVER (
			PARTITION BY e.memberid, e.episode_start_date
			ORDER BY a.attributionperiodbegindate DESC
		) = 1
),

max_attributed_tin AS (
	SELECT
		e.memberid,
		a.attributedprovidertaxid,
		a.attributedproviderorganizationname,
		a.attributednpiproviderid
	FROM episodes AS e
		LEFT JOIN dev_dtx_gc.IC1.ATTRIBUTION AS a
			ON e.memberid = a.memberid
	WHERE a.attributedprovidertaxid IS NOT NULL
	QUALIFY ROW_NUMBER() OVER (
			PARTITION BY e.memberid
			ORDER BY a.attributionperiodbegindate DESC
		) = 1
),

member_cancer_info AS (
	SELECT
		e.memberid,
		COALESCE(ct.icd10code, 'ZZZZZ') AS cancerdiagnosisgroupcode,
		COALESCE(ct.cancer_type, 'Unknown') AS cancertype,
		COALESCE(ct.icd10code, cl.claimlineprincipaldiagnosiscode, 'Unknown') AS customcancercode,
		COALESCE(cl.claimlineprincipaldiagnosiscode, 'Unknown') AS principalcancercode,
		CASE WHEN ct.cancer_type IS NULL THEN 1 WHEN ct.cancer_type LIKE 'Secondary%' THEN 2 WHEN ct.cancer_type LIKE '%other%' THEN 3 ELSE 4 END AS cancerorder,
		ROW_NUMBER() OVER (
			PARTITION BY e.memberid
			ORDER BY cancerorder DESC, cl.claimlineservicestartdate ASC
		) AS cancerorder_rn
	FROM episodes AS e
		LEFT JOIN dev_dtx_gc.IC1.CLAIM AS c
			ON e.memberid = c.memberid
		LEFT JOIN dev_dtx_gc.IC1.CLAIMLINE AS cl
			ON c.claimid = cl.claimid AND cl.claimlinestatuscode = 'APRVD'
		LEFT JOIN dev_dtx_gc.staging.stg_seed_ocm_cancer_types AS ct
			ON cl.claimlineprincipaldiagnosiscode LIKE (ct.icd10code || '%')
)

SELECT
	e.memberid,
	e.episode_start_date,
	e.episode_end_date,
	COALESCE(e.oncologist_tin, et.attributedprovidertaxid, mt.attributedprovidertaxid) AS tin,
	COALESCE(e.oncologist_npi, et.attributednpiproviderid, mt.attributednpiproviderid) AS participatingprovidernpi,
	COALESCE(e.contractname, et.attributedproviderorganizationname, mt.attributedproviderorganizationname) AS contractname,
	e.lineofbusiness,
	pp.perf_period_key,
	pp.perf_period_start_date,
	pp.perf_period_end_date,
	c.cancerdiagnosisgroupcode,
	c.cancertype,
	c.customcancercode,
	c.principalcancercode
FROM episodes AS e
	INNER JOIN dev_dtx_gc.staging.stg_seed_performance_period AS pp
		ON e.episode_start_date BETWEEN pp.perf_period_start_date AND pp.perf_period_end_date
	LEFT JOIN member_cancer_info AS c
		ON e.memberid = c.memberid
	LEFT JOIN episode_attributed_tin AS et
		ON e.memberid = et.memberid AND e.episode_start_date = et.episode_start_date
	LEFT JOIN max_attributed_tin AS mt
		ON e.memberid = mt.memberid
WHERE c.cancerorder_rn = 1