-- DBT Model: stg_member_chemotherapy
-- Database: dev_dtx_gc
-- Schema: staging
-- Alias: stg_member_chemotherapy


WITH diagnosis_chemo AS (
		SELECT * FROM dev_dtx_gc.staging.stg_seed_chemo_codes AS cc
		WHERE cc.code_type = 'DIAGNOSIS'
)
SELECT
	memberid,
	chemodate,
	claimlineplaceofservicecode,
	chemocode,
	chemodesc,
	'Pharmacy' AS category
FROM (
	SELECT DISTINCT
		c.memberid,
		c.claimprescriptionfilleddate AS chemodate,
		0 AS claimlineplaceofservicecode,
		cc.code AS chemocode,
		cc.agents AS chemodesc,
		1 AS prefrence
	FROM dev_dtx_gc.IC1.CLAIMPHARMACY AS c
		INNER JOIN dev_dtx_gc.staging.stg_seed_chemo_codes AS cc
			ON c.claimpharmacyndccode = cc.code AND cc.code_type = 'NDC'

	UNION DISTINCT

	SELECT DISTINCT
		c.memberid,
		c.claimprescriptionfilleddate AS chemodate,
		0 AS claimlineplaceofservicecode,
		cc.code AS chemocode,
		cc.agents AS chemodesc,
		2 AS prefrence
	FROM dev_dtx_gc.IC1.CLAIMPHARMACY AS c
		INNER JOIN dev_dtx_gc.staging.stg_seed_chemo_codes AS cc
			ON cc.code = LEFT(c.claimpharmacygenericproductidentifier, 10) AND cc.code_type = 'GPI10'

)
QUALIFY ROW_NUMBER() OVER (
		PARTITION BY memberid, chemodate
		ORDER BY prefrence DESC
	) = 1

UNION DISTINCT

SELECT
	memberid,
	chemodate,
	claimlineplaceofservicecode,
	chemocode,
	chemodesc,
	'Medical' AS category
FROM (
	SELECT DISTINCT
	c.memberid,
	cl.claimlineservicestartdate AS chemodate,
	cl.claimlineplaceofservicecode,
	cc.code AS chemocode,
	cc.agents AS chemodesc,
	1 AS prefrence
	FROM dev_dtx_gc.IC1.CLAIM AS c
	INNER JOIN dev_dtx_gc.IC1.CLAIMLINE AS cl
		ON c.claimid = cl.claimid
	INNER JOIN dev_dtx_gc.staging.stg_seed_chemo_codes AS cc
		ON cl.claimlinehealthservicecode = cc.code AND cc.code_type = 'HCPCS'

	UNION DISTINCT

	SELECT DISTINCT
		c.memberid,
		cl.claimlineservicestartdate AS chemodate,
		cl.claimlineplaceofservicecode,
		cc.code AS chemocode,
		cc.agents AS chemodesc,
		2 AS prefrence
	FROM dev_dtx_gc.IC1.CLAIM AS c
		INNER JOIN dev_dtx_gc.IC1.CLAIMLINE AS cl
			ON c.claimid = cl.claimid
		INNER JOIN diagnosis_chemo AS cc
			ON cl.claimlineprincipaldiagnosiscode = cc.code

	UNION DISTINCT

	SELECT DISTINCT
		c.memberid,
		cl.claimlineservicestartdate AS chemodate,
		cl.claimlineplaceofservicecode,
		cc.code AS chemocode,
		cc.agents AS chemodesc,
		3 AS prefrence
	FROM dev_dtx_gc.IC1.CLAIM AS c
		INNER JOIN dev_dtx_gc.IC1.CLAIMLINE AS cl
			ON c.claimid = cl.claimid
		INNER JOIN diagnosis_chemo AS cc
			ON cl.claimlineadmittingdiagnosiscode = cc.code

		UNION DISTINCT

	SELECT DISTINCT
		c.memberid,
		cl.claimlineservicestartdate AS chemodate,
		cl.claimlineplaceofservicecode,
		cc.code AS chemocode,
		cc.agents AS chemodesc,
		4 AS prefrence
	FROM dev_dtx_gc.IC1.CLAIM AS c
		INNER JOIN dev_dtx_gc.IC1.CLAIMLINE AS cl
			ON c.claimid = cl.claimid
		LEFT JOIN dev_dtx_gc.IC1.CLAIMLINEDIAGNOSIS AS cld
			ON cl.claimid = cld.claimid
				AND cl.claimlineid = cld.claimlineid
		INNER JOIN diagnosis_chemo AS cc
			ON cld.diagnosiscode = cc.code
)
QUALIFY ROW_NUMBER() OVER (
		PARTITION BY memberid, chemodate
		ORDER BY prefrence
	) = 1