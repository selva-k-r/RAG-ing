-- DBT Model: stg_avoidable_admissions
-- Database: dev_dtx_gc
-- Schema: staging
-- Alias: stg_avoidable_admissions



WITH ip_ed_admissions AS (
	SELECT
		ma.memberid,
		ma.claimid,
		ma.claimlineid,
		ma.claimlineprincipaldiagnosiscode,
		ma.claimlineplaceofservicecode,
		ma.claimlinehealthservicecode,
		ma.dateofservice,
		ma.claimlinerevenuecode,
		ma.admission_type,
		ma.admission_start_date,
		ma.ipdateid
	FROM dev_dtx_gc.staging.stg_member_admissions AS ma
	WHERE ma.admission_type IN ('IP', 'ED')
),

primary_avoidable_admissions AS (
	SELECT
		adm.*,
		avd.icd10code,
		avd.icd10description,
		avd.icd10group
	FROM ip_ed_admissions AS adm
		INNER JOIN dev_dtx_gc.staging.stg_seed_qm_avoidable_diagnosis AS avd
			ON adm.claimlineprincipaldiagnosiscode = avd.icd10code -- IC-20945 1. All pricipal diagnosis code that are avoidable diagnosis are to be considered as avoidable visits
),

secondary_avoidable_admissions AS (
	SELECT
		adm.*,
		avd.icd10code,
		avd.icd10description,
		avd.icd10group
	FROM ip_ed_admissions AS adm
		LEFT JOIN dev_dtx_gc.IC1.CLAIMLINEDIAGNOSIS AS cld -- IC-20945 to fetch secondary diagnosis code for claims, The column "diagnosiscode" will contian the 25 secondary diagnosis as rows
			ON adm.claimid = cld.claimid
				AND adm.claimlineid = cld.claimlineid
		LEFT JOIN dev_dtx_gc.staging.stg_seed_ocm_cancer_types AS ct
			ON adm.claimlineprincipaldiagnosiscode LIKE (ct.icd10code || '%')
		INNER JOIN dev_dtx_gc.staging.stg_seed_qm_avoidable_diagnosis AS avd
			ON cld.diagnosiscode = avd.icd10code -- IC-20945 2. IF pricipal diagnosis code are cancer codes and secondary diagnosis code are avoidable diagnosis the admissions are to be considered as avoidable visits
	WHERE NOT EXISTS (
			SELECT 1 FROM primary_avoidable_admissions AS paa
			WHERE paa.claimid = adm.claimid
				AND paa.claimlineid = adm.claimlineid
				AND paa.dateofservice = adm.dateofservice
		) -- IC-20945 To only look for admission that are not due to primary avoidable diagnosis
		AND ct.cancer_type IS NOT NULL -- IC-20945 to make sure the principal diagnosis is a cancer code
	QUALIFY ROW_NUMBER() OVER (
			PARTITION BY adm.memberid, adm.claimid, adm.dateofservice
			ORDER BY avd.icd10code
		) = 1 -- To consider the only one avoidable diagnosis id there are multiple on same day based on alphabetical order
)

SELECT *
FROM primary_avoidable_admissions

UNION DISTINCT

SELECT *
FROM secondary_avoidable_admissions