-- DBT Model: stg_claimpharmacy
-- Database: dev_dtx_gc
-- Schema: staging
-- Alias: stg_claimpharmacy




SELECT DISTINCT
	cp.memberid,
	ep.perf_period_key,
	ep.episode_start_date,
	ep.episode_end_date,
	cp.claimid,
	TO_NUMBER(cp.claimpharmacylinenumber) AS claimlinenumber,
	ep.tin AS medicalfacilitytin,
	COALESCE(ep.participatingprovidernpi, cp.claimpharmacynationalprovideridentifier, cp.claimpharmacyfacilitynpinumber) AS participatingprovidernpi,
	cp.claimpharmacyfacilitynpinumber AS claimbillingprovidernpinumber,
	cp.claimpharmacynationalprovideridentifier AS claimrenderingprovidernpinumber,
	NULL AS claimextractadjudicationdate,
	0 AS claimlengthofinpatientstaynumber,
	NULL AS claimtypeofbillcode,
	NULL AS claimlinerevenuecode,
	cp.claimprescriptionfilleddate AS claimlineservicestartdate,
	NULL AS claimlineserviceenddate,
	NULL AS claimlinehealthservicecode,
	NULL AS claimlineproceduremodifier1code,
	NULL AS claimlineproviderrenderingprovidernetworkidentifier,
	NULL AS claimlinepatientdischargestatuscode,
	NULL AS claimlinehealthservicetypecode,
	NULL AS claimlineplaceofservicecode,
	NULL AS claimlineprincipaldiagnosiscode,
	NULL AS avoidablediagnosis,
	NULL AS avoidableadmissionflag,
	NULL AS avoidablediagnosisgroup,
	NULL AS chemotherapytype,
	'Retail Pharmacy' AS costcategory,
	NULL AS utilizationcategory,
	cp.claimpharmacypaidamount AS claimlinepaidamount,
	cp.claimpharmacyallowedamount AS claimlineallowedamountvalue,
	CASE WHEN cp.claimpharmacyinnetworkcode = 'IN' THEN 'In Network'
		WHEN cp.claimpharmacyinnetworkcode = 'OUT' THEN 'Out of Network' ELSE 'UnKnown'
	END AS inoutnetwork,
	ep.cancerdiagnosisgroupcode,
	cp.claimpharmacyndccode,
	cp.claimpharmacygenericproductidentifier,
	cp.claimpharmacydrugmetricstrengthnumber,
	cp.claimpharmacydrugmetricunitnumber,
	cp.claimprescriptionfilleddate,
	cp.claimpharmacyfilledrefillsnumber,
	cp.claimpharmacysupplydaysnumber,
	cp.claimpharmacynationalprovideridentifier,
	cp.claimprescribingprovidernpinumber,
	0 AS drgpaymentamount, -- until field mapping is identified, defaulted to 0
	'Retail Pharmacy' AS sourcename,
	ep.lineofbusiness
FROM dev_dtx_gc.IC1.CLAIMPHARMACY AS cp
	INNER JOIN dev_dtx_gc.staging.stg_episodes AS ep
		ON cp.memberid = ep.memberid
			AND cp.claimprescriptionfilleddate >= ep.episode_start_date
			AND cp.claimprescriptionfilleddate <= ep.episode_end_date
WHERE cp.claimpharmacylinestatuscode = 'APRVD'
QUALIFY ROW_NUMBER() OVER (
		PARTITION BY claimid, claimlinenumber
		ORDER BY episode_start_date DESC
	) = 1