-- DBT Model: stg_claimline
-- Database: dev_dtx_gc
-- Schema: staging
-- Alias: stg_claimline




WITH stg_claimline AS (
	SELECT DISTINCT
		c.memberid,
		ep.perf_period_key,
		ep.episode_start_date,
		ep.episode_end_date,
		c.claimid,
		TO_NUMBER(cl.claimlinenumber) AS claimlinenumber,
		COALESCE(ep.tin, c.claimbillingproviderfederaltaxidnumber) AS medicalfacilitytin,
		COALESCE(ep.participatingprovidernpi, c.claimrenderingprovidernpinumber, claimbillingprovidernpinumber) AS participatingprovidernpi,
		c.claimbillingprovidernpinumber,
		c.claimrenderingprovidernpinumber,
		c.claimextractadjudicationdate,
		COALESCE(c.claimlengthofinpatientstaynumber, 0) AS claimlengthofinpatientstaynumber,
		c.claimtypeofbillcode,
		cl.claimlinerevenuecode,
		cl.claimlineservicestartdate,
		cl.claimlineserviceenddate,
		cl.claimlinehealthservicecode,
		cl.claimlineproceduremodifier1code,
		cl.claimlineproviderrenderingprovidernetworkidentifier,
		cl.claimlinepatientdischargestatuscode,
		cl.claimlinehealthservicetypecode,
		cl.claimlineplaceofservicecode,
		cl.claimlineprincipaldiagnosiscode,
		CONCAT(ad.icd10code, ' - ', ad.icd10description) AS avoidablediagnosis,
		CASE WHEN ad.icd10code IS NULL THEN 0 ELSE 1 END AS avoidableadmissionflag,
		UPPER(ad.icd10group) AS avoidablediagnosisgroup,
		NULL AS chemotherapytype,
		CASE 
			WHEN mad.admission_type = 'IP' THEN 'Inpatient'
			WHEN mad.admission_type = 'ED' THEN 'ED'                         -- IC-14456: Only spefic codes are eligible for ED
			WHEN che.code IS NOT NULL THEN 'Chemo & Drugs (Medical)'   -- Independen of POS, it depends on chemocodes
			WHEN cl.claimlineplaceofservicecode IN (21,23)  THEN 'All other medicals' -- Rest of ED,IP POS will fall under Other
			ELSE cms.place_of_service_name
		END AS utilizationcategory,
		COALESCE(utilizationcategory, 'All other medicals') AS costcategory,
		cl.claimlinepaidamount,
		cl.claimlineallowedamountvalue,
		CASE WHEN cl.claimlineinnetworkcode = 'IN' THEN 'In Network'
			WHEN cl.claimlineinnetworkcode = 'OUT' THEN 'Out of Network' ELSE 'UnKnown'
		END AS inoutnetwork,
		ep.cancerdiagnosisgroupcode,
		NULL AS claimpharmacyndccode,
		NULL AS claimpharmacygenericproductidentifier,
		NULL AS claimpharmacydrugmetricstrengthnumber,
		NULL AS claimpharmacydrugmetricunitnumber,
		NULL AS claimprescriptionfilleddate,
		NULL AS claimpharmacyfilledrefillsnumber,
		NULL AS claimpharmacysupplydaysnumber,
		NULL AS claimpharmacynationalprovideridentifier,
		NULL AS claimprescribingprovidernpinumber,
		0 AS drgpaymentamount, -- until field mapping is identified, defaulted to 0
		CASE WHEN mad.admission_type IS NULL AND che.code IS NOT NULL THEN 'Chemo & Drugs (Medical)' ELSE 'Medical' END AS sourcename,
		COALESCE(ep.lineofbusiness, c.claimpayerlineofbusinessdescription) AS lineofbusiness,
		mad.admission_group AS ipadmissiongroup,
		mad.admission_start_date,
		mad.ipdateid,
		mad.eddateid,
		CASE WHEN qm3.numerator = 1 OR qm4.numerator = 1 THEN 'Y' ELSE 'N' END AS  qualitymeasureindicator
	FROM dev_dtx_gc.IC1.CLAIMLINE AS cl
		INNER JOIN dev_dtx_gc.IC1.CLAIM AS c
			ON cl.claimid = c.claimid
		LEFT JOIN dev_dtx_gc.staging.stg_member_admissions AS mad
			ON c.memberid = mad.memberid
				AND cl.claimid = mad.claimid
				AND cl.claimlineid = mad.claimlineid
		INNER JOIN dev_dtx_gc.staging.stg_episodes AS ep
			ON c.memberid = ep.memberid
				AND coalesce(mad.admission_start_date, cl.claimlineservicestartdate) >= ep.episode_start_date
				AND coalesce(mad.admission_start_date, cl.claimlineservicestartdate) <= ep.episode_end_date
		LEFT JOIN dev_dtx_gc.staging.stg_seed_place_of_service_mapping AS cms
			ON cl.claimlineplaceofservicecode = cms.place_of_service_code
		LEFT JOIN dev_dtx_gc.staging.stg_seed_chemo_codes AS che
			ON cl.claimlinehealthservicecode = che.code AND che.code_type = 'HCPCS'
		LEFT JOIN dev_dtx_gc.staging.stg_avoidable_admissions AS ad
			ON ep.memberid = ad.memberid
				AND cl.claimid = ad.claimid
				AND cl.claimlineid = ad.claimlineid
		LEFT JOIN dev_dtx_gc.staging.stg_qm3_4 AS qm3
            ON (mad.admission_type = 'IP' AND mad.ipdateid = qm3.ipdateid AND qm3.qm_name = 'QM3')
			AND qm3.numerator = 1
		LEFT JOIN dev_dtx_gc.staging.stg_qm3_4 AS qm4
            ON (mad.admission_type = 'ED' AND mad.memberid = qm4.memberid AND mad.admission_start_date = qm4.admission_start_date AND qm4.qm_name = 'QM4')
			AND qm4.numerator = 1
	WHERE cl.claimlinestatuscode = 'APRVD'
)

SELECT
	cl.*
FROM stg_claimline AS cl
QUALIFY ROW_NUMBER() OVER (
		PARTITION BY claimid, claimlinenumber
		ORDER BY episode_start_date DESC
	) = 1