-- DBT Model: stg_qm3_4
-- Database: dev_dtx_gc
-- Schema: staging
-- Alias: stg_qm3_4



-- Denominator Logic:
-- Members that are sent in Anthem’s attribution file
-- Numerator Logic: 
-- (qm3: >= one inpatient admission. qm4: >=one ed visit)
-- AND
-- ·       >= one of the 10 qualifying conditions (i.e., anemia, dehydration, diarrhea, emesis, fever, nausea, neutropenia, pain, pneumonia, or sepsis)
-- ·       <= 30 days of non-ipatient chemotherapy treatment (non-inpatient POS code condition: "!= 21" )

WITH months AS (
	SELECT DISTINCT DATE_TRUNC(MONTH, date) AS month
	FROM dev_dtx_gc.staging.stg_dates
),

initial_qm_3_4 AS (
	SELECT
		ep.memberid,
		ep.episode_start_date,
		ep.episode_end_date,
		ad.dateofservice,
		ad.admission_start_date,
		ad.ipdateid,
		m.month AS contextdate,
		mc.chemodate,
		mc.chemocode,
		mc.chemodesc,
		DATEDIFF(DD, mc.chemodate, ad.dateofservice) AS chemodays,
		CASE
			WHEN chemodays >= 0
				AND chemodays <= 30
				AND ad.dateofservice IS NOT NULL
				THEN 1
			ELSE 0
		END AS numerator,
		coalesce(ad.admission_type,' ') AS pos,
		ROW_NUMBER() OVER (
			PARTITION BY
				ep.memberid,
				ep.episode_start_date,
				contextdate,
				pos
			ORDER BY
				numerator DESC,
				ad.dateofservice DESC,
				mc.chemodate DESC
		) AS row_no,
		COUNT(DISTINCT pos) OVER (
			PARTITION BY ep.memberid, ep.episode_start_date, contextdate
		) AS distinct_pos_count,
		ad.claimlineplaceofservicecode,
		ep.participatingprovidernpi,
		ep.principalcancercode,
		ep.cancerdiagnosisgroupcode,
		ep.tin,
		ep.lineofbusiness,
		ad.icd10code,
		ad.icd10description,
		ad.claimlinehealthservicecode,
		ep.perf_period_key
	FROM dev_dtx_gc.staging.stg_episodes AS ep
		INNER JOIN months AS m
			ON m.month BETWEEN DATE_TRUNC(MONTH, ep.episode_start_date)
				AND DATE_TRUNC(MONTH, ep.episode_end_date)
		LEFT JOIN dev_dtx_gc.staging.stg_member_chemotherapy AS mc
			ON ep.memberid = mc.memberid
				AND mc.claimlineplaceofservicecode <> 21
				AND mc.chemodate BETWEEN ep.episode_start_date AND ep.episode_end_date
		LEFT JOIN dev_dtx_gc.staging.stg_avoidable_admissions AS ad
			ON ep.memberid = ad.memberid
				AND ep.episode_start_date <= ad.admission_start_date
				AND ep.episode_end_date >= ad.admission_start_date
				AND DATE_TRUNC(MONTH, ad.admission_start_date) = m.month
),

oneepisodepermonth AS (
	SELECT
		qm.memberid,
		1 AS denominator,
		CASE qm.pos
			WHEN 'IP'
				THEN qm.numerator
			ELSE 0
		END AS numerator,
		qm.episode_start_date,
		qm.episode_end_date,
		qm.contextdate,
		qm.participatingprovidernpi,
		qm.perf_period_key,
		qm.principalcancercode,
		qm.cancerdiagnosisgroupcode,
		qm.tin,
		qm.lineofbusiness,
		CASE WHEN qm.pos = 'IP' THEN qm.dateofservice END AS dateofservice,
		qm.chemodate,
		qm.chemocode,
		qm.chemodesc,
		qm.chemodays,
		qm.claimlineplaceofservicecode,
		qm.pos AS placeofservice,
		'QM3' AS qm_name,
		CASE WHEN qm.pos = 'IP' THEN qm.icd10code END AS icd10code,
		CASE WHEN qm.pos = 'IP' THEN qm.icd10description END AS icd10description,
		CASE WHEN qm.pos = 'IP' THEN qm.claimlinehealthservicecode END AS claimlinehealthservicecode,
		CASE WHEN qm.pos = 'IP' THEN qm.admission_start_date END AS admission_start_date,
		qm.ipdateid
	FROM initial_qm_3_4 AS qm
	WHERE qm.row_no = 1
		AND (distinct_pos_count = 1 OR qm.pos = 'IP') -- IC-15039: Added to avoid ED record for the patients having IP record
	QUALIFY ROW_NUMBER() OVER (
			PARTITION BY qm.memberid, qm.episode_start_date, qm.contextdate
			ORDER BY numerator DESC, qm.dateofservice DESC
		) = 1

	UNION ALL

	SELECT
		qm.memberid,
		1 AS denominator,
		CASE
			WHEN qm.pos = 'ED' -- IC-14456 , Ask is to add POS=22 with Specific Revcodes and Hcpcs are consider as ED
				THEN qm.numerator
			ELSE 0
		END AS numerator,
		qm.episode_start_date,
		qm.episode_end_date,
		qm.contextdate,
		qm.participatingprovidernpi,
		qm.perf_period_key,
		qm.principalcancercode,
		qm.cancerdiagnosisgroupcode,
		qm.tin,
		qm.lineofbusiness,
		CASE WHEN qm.pos = 'ED' THEN qm.dateofservice END AS dateofservice,
		qm.chemodate,
		qm.chemocode,
		qm.chemodesc,
		qm.chemodays,
		qm.claimlineplaceofservicecode,
		qm.pos AS placeofservice,
		'QM4' AS qm_name,
		CASE WHEN qm.pos = 'ED' THEN qm.icd10code END AS icd10code,
		CASE WHEN qm.pos = 'ED' THEN qm.icd10description END AS icd10description,
		CASE WHEN qm.pos = 'ED' THEN qm.claimlinehealthservicecode END AS claimlinehealthservicecode,
		CASE WHEN qm.pos = 'ED' THEN qm.admission_start_date END AS admission_start_date,
		NULL AS ipdateid
	FROM initial_qm_3_4 AS qm
	WHERE qm.row_no = 1
		AND (distinct_pos_count = 1 OR qm.pos = 'ED') -- IC-15039: Added to avoid IP record for the patients having ED record
	QUALIFY ROW_NUMBER() OVER (
			PARTITION BY qm.memberid, qm.episode_start_date, qm.contextdate
			ORDER BY numerator DESC, qm.dateofservice DESC
		) = 1
)

SELECT * FROM oneepisodepermonth