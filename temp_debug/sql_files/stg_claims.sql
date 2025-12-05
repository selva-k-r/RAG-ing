-- DBT Model: stg_claims
-- Database: dev_dtx_gc
-- Schema: staging
-- Alias: stg_claims



WITH fact_claims AS (
	SELECT
		scl.memberid,
		scl.perf_period_key,
		scl.episode_start_date,
		scl.episode_end_date,
		scl.claimid,
		scl.claimlinenumber,
		scl.medicalfacilitytin,
		scl.participatingprovidernpi,
		scl.claimbillingprovidernpinumber,
		scl.claimrenderingprovidernpinumber,
		scl.claimextractadjudicationdate,
		scl.claimlengthofinpatientstaynumber,
		scl.claimtypeofbillcode,
		scl.claimlinerevenuecode,
		scl.claimlineservicestartdate,
		scl.claimlineserviceenddate,
		scl.claimlinehealthservicecode,
		scl.claimlineproceduremodifier1code,
		scl.claimlineproviderrenderingprovidernetworkidentifier,
		scl.claimlinepatientdischargestatuscode,
		scl.claimlinehealthservicetypecode,
		scl.claimlineplaceofservicecode,
		scl.claimlineprincipaldiagnosiscode,
		scl.avoidablediagnosis,
		scl.avoidableadmissionflag,
		scl.avoidablediagnosisgroup,
		scl.chemotherapytype,
		scl.costcategory,
		scl.utilizationcategory,
		scl.claimlinepaidamount,
		scl.claimlineallowedamountvalue,
		scl.inoutnetwork,
		scl.cancerdiagnosisgroupcode,
		scl.claimpharmacyndccode,
		scl.claimpharmacygenericproductidentifier,
		scl.claimpharmacydrugmetricstrengthnumber,
		scl.claimpharmacydrugmetricunitnumber,
		scl.claimprescriptionfilleddate,
		scl.claimpharmacyfilledrefillsnumber,
		scl.claimpharmacysupplydaysnumber,
		scl.claimpharmacynationalprovideridentifier,
		scl.claimprescribingprovidernpinumber,
		scl.drgpaymentamount, -- until field mapping is identified, defaulted to 0
		scl.sourcename,
		CONCAT(scl.memberid, '_', scl.medicalfacilitytin) AS memberid_attributedtin,
		CONCAT(COALESCE(scl.participatingprovidernpi, ''), '_', scl.medicalfacilitytin) AS participatingnpi_attributedtin,
		CONCAT(COALESCE(scl.claimbillingprovidernpinumber, ''), '_', scl.medicalfacilitytin) AS billingnpi_attributedtin,
		CONCAT(COALESCE(scl.claimrenderingprovidernpinumber, ''), '_', scl.medicalfacilitytin) AS renderingnpi_attributedtin,
		CONCAT(COALESCE(scl.claimprescribingprovidernpinumber, ''), '_', scl.medicalfacilitytin) AS prescribingnpi_attributedtin,
		CONCAT(COALESCE(scl.claimpharmacynationalprovideridentifier, ''), '_', scl.medicalfacilitytin) AS pharmacynpi_attributedtin,
		CASE WHEN scl.utilizationcategory = 'ED' THEN MIN(scl.claimlineservicestartdate) OVER (PARTITION BY scl.claimid ORDER BY scl.claimlineservicestartdate ASC ) END AS emergencydeptvisitdate,
		CASE WHEN scl.utilizationcategory = 'ED' AND scl.avoidableadmissionflag = 1 THEN scl.avoidablediagnosis END AS emergencydeptvisitsbyavoidabledx,
		CASE WHEN scl.utilizationcategory = 'ED' THEN dpp.provider_name END AS emergencydeptvisitsbyattributedoncologist,
		CASE WHEN scl.utilizationcategory = 'ED' THEN 'Y' ELSE 'N' END AS edutilizationflag,
		CASE WHEN scl.utilizationcategory = 'ED' AND scl.avoidableadmissionflag = 1 THEN 'Y' ELSE 'N' END AS edavoidableutilizationflag,
		CASE WHEN scl.utilizationcategory = 'ED' THEN dct.cancertype END AS emergencydeptvisitscancertype,
		CASE WHEN scl.utilizationcategory = 'Inpatient' AND scl.avoidableadmissionflag = 1 THEN scl.avoidablediagnosis END AS inpatientadmissionsbyavoidablediagnosis,
		CASE WHEN scl.utilizationcategory = 'Inpatient' THEN dpp.provider_name END AS inpatientadmissionsbyattributedoncologist,
		CASE WHEN scl.utilizationcategory = 'Inpatient' THEN 'Y' ELSE 'N' END AS iputilizationflag,
		CASE WHEN scl.utilizationcategory = 'Inpatient' AND scl.avoidableadmissionflag = 1 THEN 'Y' ELSE 'N' END AS ipavoidableutilizationflag,
		CASE WHEN scl.utilizationcategory = 'Inpatient' THEN scl.admission_start_date END AS ipadmitdate,
		CASE WHEN scl.utilizationcategory IN ('ED', 'Inpatient') THEN 1 ELSE 0 END AS util_pl_flag,
		scl.lineofbusiness,
		scl.ipadmissiongroup,
		CASE 
			WHEN icd.concept_code = scl.claimlineprincipaldiagnosiscode THEN icd.concept_code || ' - ' || icd.concept_name
            WHEN scl.avoidablediagnosis LIKE '%' || scl.claimlineprincipaldiagnosiscode || '%' THEN scl.avoidablediagnosis 
            WHEN scl.claimlineprincipaldiagnosiscode = ssh.code THEN ssh.code || ' - ' || ssh.procedure_description 
            ELSE NULL 
		END AS diagnosiscodedescription,
		scl.ipdateid,
		scl.eddateid,
		scl.admission_start_date,
		scl.qualitymeasureindicator
	FROM dev_dtx_gc.staging.stg_claimline AS scl
	LEFT JOIN dev_dtx_gc.staging.stg_participating_provider AS dpp
		ON CONCAT(COALESCE(scl.participatingprovidernpi, ''), '_', scl.medicalfacilitytin) = dpp.participatingnpi_attributedtin
	LEFT JOIN dev_dtx_gc.staging.stg_Cancer_Type AS dct
		ON scl.cancerdiagnosisgroupcode = dct.cancerdiagnosisgroupcode
	LEFT JOIN dev_dtx_gc.staging.stg_seed_hcpcs AS ssh ON scl.claimlineprincipaldiagnosiscode = ssh.code
	LEFT JOIN dev_dtx_gc.staging.stg_seed_icd10cm_codes AS icd ON scl.claimlineprincipaldiagnosiscode = icd.concept_code

	UNION ALL

	SELECT
		memberid,
		perf_period_key,
		episode_start_date,
		episode_end_date,
		claimid,
		claimlinenumber,
		medicalfacilitytin,
		participatingprovidernpi,
		claimbillingprovidernpinumber,
		claimrenderingprovidernpinumber,
		claimextractadjudicationdate,
		claimlengthofinpatientstaynumber,
		claimtypeofbillcode,
		claimlinerevenuecode,
		claimlineservicestartdate,
		claimlineserviceenddate,
		claimlinehealthservicecode,
		claimlineproceduremodifier1code,
		claimlineproviderrenderingprovidernetworkidentifier,
		claimlinepatientdischargestatuscode,
		claimlinehealthservicetypecode,
		claimlineplaceofservicecode,
		claimlineprincipaldiagnosiscode,
		avoidablediagnosis,
		avoidableadmissionflag,
		avoidablediagnosisgroup,
		chemotherapytype,
		costcategory,
		utilizationcategory,
		claimlinepaidamount,
		claimlineallowedamountvalue,
		inoutnetwork,
		cancerdiagnosisgroupcode,
		claimpharmacyndccode,
		claimpharmacygenericproductidentifier,
		claimpharmacydrugmetricstrengthnumber,
		claimpharmacydrugmetricunitnumber,
		claimprescriptionfilleddate,
		claimpharmacyfilledrefillsnumber,
		claimpharmacysupplydaysnumber,
		claimpharmacynationalprovideridentifier,
		claimprescribingprovidernpinumber,
		drgpaymentamount, -- until field mapping is identified, defaulted to 0
		sourcename,
		CONCAT(memberid, '_', medicalfacilitytin) AS memberid_attributedtin,
		CONCAT(COALESCE(participatingprovidernpi, ''), '_', medicalfacilitytin) AS participatingnpi_attributedtin,
		CONCAT(COALESCE(claimbillingprovidernpinumber, ''), '_', medicalfacilitytin) AS billingnpi_attributedtin,
		CONCAT(COALESCE(claimrenderingprovidernpinumber, ''), '_', medicalfacilitytin) AS renderingnpi_attributedtin,
		CONCAT(COALESCE(claimprescribingprovidernpinumber, ''), '_', medicalfacilitytin) AS prescribingnpi_attributedtin,
		CONCAT(COALESCE(claimpharmacynationalprovideridentifier, ''), '_', medicalfacilitytin) AS pharmacynpi_attributedtin,
		NULL AS emergencydeptvisitdate,
		NULL AS emergencydeptvisitsbyavoidabledx,
		NULL AS emergencydeptvisitsbyattributedoncologist,
		NULL AS edutilizationflag,
		NULL AS edavoidableutilizationflag,
		NULL AS emergencydeptvisitscancertype,
		NULL AS inpatientadmissionsbyavoidablediagnosis,
		NULL AS inpatientadmissionsbyattributedoncologist,
		NULL AS iputilizationflag,
		NULL AS ipavoidableutilizationflag,
		NULL AS ipadmitdate,
		0 AS util_pl_flag,
		lineofbusiness,
		NULL AS ipadmissiongroup,
		NULL AS diagnosiscodedescription,
		NULL AS ipdateid,
		NULL AS qualitymeasureindicator,
		NULL AS eddateid,
		NULL AS admission_start_date
	FROM dev_dtx_gc.staging.stg_claimpharmacy

),

postchemo AS (
	SELECT
		fc.memberid,
		fc.claimlineservicestartdate,
		MAX(cs.chemodate) AS recentchemodate,
		CASE
			WHEN
				DATEDIFF(DAY, MAX(cs.chemodate), fc.claimlineservicestartdate)
				<= 3
				THEN '<=3 days'
			--Only days greater than 3 will pass here
			WHEN
				DATEDIFF(DAY, MAX(cs.chemodate), fc.claimlineservicestartdate)
				<= 7
				THEN '4-7 days'
			--Only days greater than 7 will pass here
			WHEN
				DATEDIFF(DAY, MAX(cs.chemodate), fc.claimlineservicestartdate)
				<= 15
				THEN '8-15 days'
			--Only days greater than 15 will pass here
			WHEN
				DATEDIFF(DAY, MAX(cs.chemodate), fc.claimlineservicestartdate)
				<= 30
				THEN '16-30 days'
		END AS postchemodaysbucket,
		DATEDIFF(DAY, MAX(cs.chemodate), fc.claimlineservicestartdate)
			AS postchemodays,
		CASE
			WHEN
				DATEDIFF(DAY, MAX(cs.chemodate), fc.claimlineservicestartdate)
				<= 3
				THEN 0
			--Only days greater than 3 will pass here
			WHEN
				DATEDIFF(DAY, MAX(cs.chemodate), fc.claimlineservicestartdate)
				<= 7
				THEN 1
			--Only days greater than 7 will pass here
			WHEN
				DATEDIFF(DAY, MAX(cs.chemodate), fc.claimlineservicestartdate)
				<= 15
				THEN 2
			--Only days greater than 15 will pass here
			WHEN
				DATEDIFF(DAY, MAX(cs.chemodate), fc.claimlineservicestartdate)
				<= 30
				THEN 3
		END AS postchemodaysbucketsort
	FROM fact_claims AS fc
		INNER JOIN dev_dtx_gc.staging.stg_member_chemotherapy AS cs
			ON
				fc.memberid = cs.memberid
				AND fc.claimlineservicestartdate > cs.chemodate
	GROUP BY fc.memberid, fc.claimlineservicestartdate
),
groupon  AS (          -- grouped continuous dates to each admission

	SELECT
		memberid,
		dateofservice,
		dateofserviceend,
		perf_period_key,
		lineofbusiness,
		DATEDIFF(
			DAY,
			MIN(dateofservice) OVER (PARTITION BY memberid),
			dateofservice
		)
		- ROW_NUMBER() OVER (
			PARTITION BY memberid
			ORDER BY dateofservice ASC
		) AS admissiongroup
	FROM dev_dtx_gc.staging.stg_hospice_members 
),

latesthospiceadmission  AS (            -- picking latest admission

	SELECT
		memberid,
		perf_period_key,
		lineofbusiness,
		admissiongroup,
		MIN(dateofservice) AS hospicestart,
		MAX(dateofserviceend) AS hospiceend,
		RANK() OVER (
			PARTITION BY memberid
			ORDER BY admissiongroup DESC
		) AS rank
	FROM groupon
	GROUP BY memberid,	
		perf_period_key,
		lineofbusiness,
		admissiongroup
	QUALIFY rank=1
)

SELECT
	fc.*,
	pc.postchemodaysbucket,
	pc.postchemodays,
	pc.postchemodaysbucketsort,
	hm.ishospicemember, --IC:16451 : Used this field in UI filter, To pick only one record per patient per Date. Sorting based on flag respective to ED or IP. 
	hsp.hospicestart,
	hsp.hospiceend,
	map.tin_group_1,
	map.tin_group_2,
	map.tin_group_3,
	CAST(CASE
		WHEN fc.costcategory = 'Chemo & Drugs (Medical)' THEN 1
		WHEN fc.costcategory = 'Retail Pharmacy' THEN 2
		WHEN fc.costcategory = 'Outpatient' THEN 3
		WHEN fc.costcategory = 'Inpatient' THEN 4
		WHEN fc.costcategory = 'Professional' THEN 5
		WHEN fc.costcategory = 'All other medicals' THEN 6
		WHEN fc.costcategory = 'Home' THEN 7
		WHEN fc.costcategory = 'ED' THEN 8
		WHEN fc.costcategory = 'Ambulatory surgery' THEN 9
		WHEN fc.costcategory = 'Lab' THEN 10
		WHEN fc.costcategory = 'Transportation' THEN 11
		WHEN fc.costcategory = 'Skilled nursing' THEN 12
	END AS number(38, 0)) AS static_costcategory_order,	
	NULL AS ip_rank,
	NULL AS ed_rank, --for sorting	
	COALESCE(ipdateid, eddateid) AS edipdateid,
	CASE WHEN edipdateid IS NOT NULL THEN
		ROW_NUMBER() OVER (
			PARTITION BY
				edipdateid
			ORDER BY
				fc.util_pl_flag DESC,
				COALESCE(fc.ipavoidableutilizationflag, fc.edavoidableutilizationflag) DESC,
				fc.claimlengthofinpatientstaynumber DESC,
				admission_start_date ASC
		) 
	END AS ed_ip_rank,
	DATE_TRUNC('seconds', SYSDATE()) AS recordinsertiondate_utc,
	CASE WHEN fc.ipdateid IS NOT NULL THEN SUM(fc.claimlineallowedamountvalue) OVER(PARTITION BY fc.ipdateid) ELSE 0 END AS totalipvisitcost,
	CASE WHEN fc.eddateid IS NOT NULL THEN SUM(fc.claimlineallowedamountvalue) OVER(PARTITION BY fc.eddateid) ELSE 0 END AS totaledvisitcost,
	CASE WHEN fc.ipdateid IS NOT NULL THEN totalipvisitcost WHEN fc.eddateid IS NOT NULL THEN  totaledvisitcost END AS totalvisitcost
FROM fact_claims AS fc
	LEFT JOIN postchemo AS pc
		ON
			fc.memberid = pc.memberid
			AND fc.claimlineservicestartdate = pc.claimlineservicestartdate
	LEFT JOIN
		dev_dtx_gc.staging.stg_member_hospice_mapping AS hm
		ON fc.memberid = hm.memberid AND fc.perf_period_key = hm.perf_period_key AND fc.lineofbusiness = hm.lineofbusiness
	LEFT JOIN dev_dtx_gc.staging.stg_client_tin_mapping AS map
		ON fc.medicalfacilitytin = map.tin
	-- pull latest hospice information
	LEFT JOIN latesthospiceadmission as hsp
		ON fc.memberid = hsp.memberid AND fc.perf_period_key = hsp.perf_period_key AND fc.lineofbusiness = hsp.lineofbusiness