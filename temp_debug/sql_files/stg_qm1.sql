-- DBT Model: stg_qm1
-- Database: dev_dtx_gc
-- Schema: staging
-- Alias: stg_qm1



-- Denominator Logic:
-- 1.       Member attributed (month of attribution)

-- 2.       Member has (Y, N or P) in TREATMENTPLANPATHWAYREGIMENINDICATORCODE column of DEV_DTX.IC1.TreatmentPlan table AND TREATMENTPLANDRUGTYPEDESCRIPTION = 'CHEMO'

-- 3.       Each row meeting this criteria should be counted in the denominator where Memberid + TreatmentPlanPlannedStartDate + TreatmentPlanSourceRegimenCode +TreatmentPlanPathwayRegimenIndicatorCode is a unique concatenated value
-- Numerator Logic: 
-- 1. Qualifying numerator for pathway adherence
-- 2.Identify members with qualifying on-pathway regimen utilizing “Pathway Regimen Indicator Code” field 
--     a. “Y” indicates that the member was treated with an on-pathway regimen
--     b. “P” indicates that the member was treated with an on-pathway regimen but has missing data elements
-- 4. Sum the number of regimens in the cohort who are “Y” 
-- 5. Sum the number of regimens in the cohort who are “P” and multiply by ½
-- 6. Sum the number of regimens in the cohort who are “Y’ and “ ½ P”

WITH treatmentplanwithcptcode AS (
	SELECT
		tp.memberid,
		tp.aimplannedtreatmentbegindate AS treatmentplanplannedstartdate,
		tp.aimplannedtreatmentenddate AS treatmentplanplannedenddate,
		tp.aimpathwayregimenindicatorcode AS treatmentplanpathwayregimenindicatorcode,
		tp.aimregimenname AS treatmentplanregimenname,
		tp.aimutilizationmanagementhealthconditiondescription AS health_condition,
		tp.utilizataionmanagementrequestinitiateddate AS authrequestdate,
		tp.aimreferencenumber AS authidreference,
		tp.aimprovidernpinumber AS orderingprovidernpi,
		tp.clinicalscenariodescription,
		REPLACE(LISTAGG(DISTINCT CHAR(8226) || ' ' || tp.dosingdeviationtext, ','), ',', CHAR(10)) AS dosingdeviationtext,
		REPLACE(LISTAGG(DISTINCT CHAR(8226) || ' ' || tp.biomarkercodedescription || '-' || COALESCE(tp.biomarkerresulttext, 'Unknown'), ','), ',', CHAR(10)) AS biomarkercodedescription,
		e.perf_period_key
	FROM dev_dtx_gc.IC1.ANTHEMAIM AS tp
		INNER JOIN dev_dtx_gc.staging.stg_episodes AS e
			ON tp.memberid = e.memberid
				AND tp.aimplannedtreatmentenddate >= e.episode_start_date
				AND tp.aimplannedtreatmentbegindate <= e.episode_end_date
	WHERE tp.aimdrugtypecode = 'CHEMO'
		AND tp.aimpathwayregimenindicatorcode IN (
			'Y',
			'N',
			'P'
		)
	GROUP BY
		tp.memberid,
		tp.aimplannedtreatmentbegindate,
		tp.aimplannedtreatmentenddate,
		tp.aimpathwayregimenindicatorcode,
		tp.aimregimenname,
		tp.aimutilizationmanagementhealthconditiondescription,
		tp.utilizataionmanagementrequestinitiateddate,
		tp.aimreferencenumber,
		tp.aimprovidernpinumber,
		tp.clinicalscenariodescription,
		e.perf_period_key
),

months AS (
	SELECT DISTINCT DATE_TRUNC(MONTH, date) AS month FROM dev_dtx_gc.staging.stg_dates
),

oneepisodepermonth AS (
	SELECT DISTINCT
		tp.memberid,
		1 AS denominator,
		CASE tp.treatmentplanpathwayregimenindicatorcode
			WHEN 'Y'
				THEN 1
			WHEN 'P'
				THEN 0.5
			WHEN 'N'
				THEN 0
		END AS numerator,
		e.episode_start_date,
		e.episode_end_date,
		m.month AS contextdate,
		tp.orderingprovidernpi,
		sp.provider_name AS orderingprovider,
		e.participatingprovidernpi,
		e.perf_period_key,
		e.cancerdiagnosisgroupcode,
		e.principalcancercode,
		e.tin,
		e.lineofbusiness,
		tp.treatmentplanpathwayregimenindicatorcode,
		tp.treatmentplanplannedenddate AS denominatortriggerdate,
		tp.treatmentplanplannedstartdate AS numeratortriggerdate,
		tp.treatmentplanplannedstartdate AS chemodates,
		tp.treatmentplanregimenname AS drugsadministered,
		tp.health_condition,
		tp.authrequestdate,
		tp.authidreference,
		tp.clinicalscenariodescription,
		tp.dosingdeviationtext,
		tp.biomarkercodedescription
	FROM treatmentplanwithcptcode AS tp
		INNER JOIN
			dev_dtx_gc.staging.stg_episodes
				AS e
			ON tp.memberid = e.memberid
				AND tp.perf_period_key = e.perf_period_key
		INNER JOIN months AS m
			ON m.month BETWEEN DATE_TRUNC(MONTH, e.episode_start_date)
				AND DATE_TRUNC(MONTH, e.episode_end_date)
		LEFT OUTER JOIN dev_dtx_gc.staging.stg_provider AS sp
			ON tp.orderingprovidernpi = sp.npi
)

SELECT * FROM oneepisodepermonth