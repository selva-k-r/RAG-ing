-- DBT Model: stg_comorbidity
-- Database: dev_dtx_gc
-- Schema: staging
-- Alias: stg_comorbidity


-- get base population - any member who has a diagnosis on 

WITH comorbidity AS (

SELECT DISTINCT
	c.memberid,
	e.perf_period_key,
	e.episode_start_date,
	e.episode_end_date,
	DATE_TRUNC(MONTH, cl.claimlineservicestartdate) AS contextdate,
	c.claimid,
	TO_NUMBER(cl.claimlinenumber) AS claimlinenumber,
	cld.diagnosiscode,
	e.tin AS attributedprovidertaxid,
	e.participatingprovidernpi,
	cl.claimlineservicestartdate,
	e.customcancercode,
	e.cancerdiagnosisgroupcode,
	e.lineofbusiness,
	cdh.comorbidity_diagnosis_code,
	cdh.comorbidity || cdh.comorbidity_diagnosis_code || COALESCE(cdh.hcc_code, '') || COALESCE(cdh.rxhcc_code, '') AS comorbidity_key
FROM dev_dtx_gc.IC1.CLAIMLINE AS cl
	INNER JOIN dev_dtx_gc.IC1.CLAIM AS c
		ON cl.claimid = c.claimid
	INNER JOIN dev_dtx_gc.staging.stg_episodes AS e
		ON c.memberid = e.memberid
			AND cl.claimlineservicestartdate >= e.episode_start_date
			AND cl.claimlineservicestartdate <= e.episode_end_date
	INNER JOIN dev_dtx_gc.IC1.CLAIMLINEDIAGNOSIS AS cld
		ON cl.claimid = cld.claimid
			AND cl.claimlineid = cld.claimlineid
	INNER JOIN dev_dtx_gc.staging.stg_comorbidtiy_diagnosis_hcc AS cdh
		ON cld.diagnosiscode = cdh.comorbidity_diagnosis_code
)

SELECT
	sc.*,
	hm.ishospicemember,
	CONCAT(sc.memberid, '_', sc.attributedprovidertaxid) AS memberid_attributedtin,
	CONCAT(COALESCE(sc.participatingprovidernpi, ''), '_', sc.attributedprovidertaxid) AS participatingnpi_attributedtin,
	DATE_TRUNC('seconds', SYSDATE()) AS recordinsertiondate_utc,
	map.tin_group_1,
	map.tin_group_2,
	map.tin_group_3
FROM comorbidity AS sc
	LEFT JOIN dev_dtx_gc.staging.stg_member_hospice_mapping AS hm
		ON sc.memberid = hm.memberid AND sc.perf_period_key = hm.perf_period_key AND sc.lineofbusiness = hm.lineofbusiness
	LEFT JOIN dev_dtx_gc.staging.stg_client_tin_mapping AS map
		ON sc.attributedprovidertaxid = map.tin