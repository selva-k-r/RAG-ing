-- DBT Model: stg_care_coordination_fee
-- Database: dev_dtx_gc
-- Schema: staging
-- Alias: stg_care_coordination_fee



/**********************************************************************************************************

IC-15569 | Care Coordination Fee Dashboard Patient List DBT

**********************************************************************************************************/
WITH pg_id_status AS (
	SELECT DISTINCT
		payer_program_id,
		completed_improvement_plan,
		improvement_plan_completion_date
	FROM dev_dtx_gc.staging.stg_seed_anthem_salesforce_apm_enrollees
),

tax_id_status AS (
	SELECT DISTINCT
		tax_id,
		completed_improvement_plan,
		improvement_plan_completion_date
	FROM dev_dtx_gc.staging.stg_seed_anthem_salesforce_apm_enrollees
),

care_coordination_fee AS (
SELECT DISTINCT
	cc.memberid,
	cc.providergroupid,
	cc.attributedprovidertaxid,
	UPPER(IFF(
		nd.entity_type_code = 2, nd.provider_organization_name_legal_business_name,
		COALESCE(nd.provider_last_name_legal_name, '') || ', ' || COALESCE(nd.provider_first_name, '')
	)) AS provider_name,
	cc.payeenpinumber,
	cc.paymentbegindate,
	CASE
		WHEN pp.ccf_version = 0
			THEN cc.payeepaymentamount
		WHEN pp.ccf_version = 1
			THEN
				CASE WHEN pg.completed_improvement_plan IS NULL AND tax.completed_improvement_plan IS NULL
						THEN cc.payeepaymentamount
					WHEN (cc.paymentbegindate >= pg.improvement_plan_completion_date AND pg.completed_improvement_plan = TRUE) 
							or (cc.paymentbegindate >= tax.improvement_plan_completion_date AND tax.completed_improvement_plan = TRUE)
						THEN (CASE WHEN cc.payeepaymentamount > 0 THEN 1 ELSE -1 end) * 130 
					ELSE
						(CASE WHEN cc.payeepaymentamount > 0 THEN 1 ELSE -1 END) * 85
				END
	END AS ccfamount,
	TO_CHAR(cc.paymentbegindate, 'MON-YYYY') AS ccfmonth,
	cc.fileprocesseddatetime,
	cc.subscriberid,
	cc.cmsfiledate,
    COALESCE(fa.lineofbusiness, INITCAP(cc.lineofbusinessidentifier), 'NA') AS lineofbusiness,
	COALESCE(fa.cancerdiagnosisgroupcode, 'ZZZZZ') AS cancerdiagnosisgroupcode,
	pp.perf_period_key,
    cc.programidentifier
FROM dev_dtx_gc.IC1.CCF AS cc
	LEFT OUTER JOIN dev_dtx_gc.staging.stg_attribution_all AS fa
		ON cc.memberid = fa.memberid
			AND TO_CHAR(cc.paymentbegindate, 'MON-YYYY') = TO_CHAR(fa.attributionperiodbegindate, 'MON-YYYY')
	LEFT OUTER JOIN dev_dtx_gc.staging.stg_seed_performance_period AS pp
		ON cc.paymentbegindate >= pp.perf_period_start_date
			AND cc.paymentbegindate <= pp.perf_period_end_date
	LEFT JOIN pg_id_status AS pg
		ON cc.programidentifier = pg.payer_program_id
	LEFT JOIN tax_id_status AS tax
		ON cc.attributedprovidertaxid = tax.tax_id
	LEFT OUTER JOIN
		
			PROD_INTELLIGENCE_DTX.IC_TO_ANTHEM.NPIDATA AS nd
		
		ON cc.payeenpinumber = nd.npi
)

SELECT
	cc.*,
	hm.ishospicemember,
	CONCAT(cc.memberid, '_', COALESCE(cc.attributedprovidertaxid, ''))
		AS memberid_attributedtin,
	CONCAT(
		COALESCE(cc.payeenpinumber, ''),
		'_',
		COALESCE(cc.attributedprovidertaxid, '')
	) AS participatingnpi_attributedtin,
	DATE_TRUNC('seconds', SYSDATE()) AS recordinsertiondate_utc
FROM care_coordination_fee AS cc
	LEFT JOIN
		dev_dtx_gc.staging.stg_member_hospice_mapping AS hm
		ON cc.memberid = hm.memberid AND cc.perf_period_key = hm.perf_period_key AND cc.lineofbusiness = hm.lineofbusiness