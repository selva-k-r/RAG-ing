-- DBT Model: stg_qm7
-- Database: dev_dtx_gc
-- Schema: staging
-- Alias: stg_qm7



-- Denominator Logic:
-- . Member attribution 
-- AND
-- . Date of death
-- Numerator Logic:
/* This measure involves calculating an outcome to determine
 members did not have an ICU admission in the last 30 days
  of life. “Performance Met” for this numerator indicates the member
  did not have an ICU admission in the last 30 days of life: indicating a high quality of care.
*/

WITH icu_visits AS (
	SELECT
		eol.memberid,
		eol.episode_start_date,
		eol.episode_end_date,
		CASE
			WHEN ad.dateofservice IS NULL
				THEN 0
			ELSE 1
		END AS icu_visit_count,
		eol.memberdeathdate,
		eol.participatingprovidernpi,
		eol.perf_period_key,
		eol.principalcancercode,
		eol.cancerdiagnosisgroupcode,
		eol.tin,
		eol.lineofbusiness,
		ad.dateofservice,
		ROW_NUMBER() OVER (
			PARTITION BY
				eol.memberid
			ORDER BY
				icu_visit_count DESC,
				ad.dateofservice DESC
		) AS row_no
	FROM dev_dtx_gc.staging.stg_eol_members AS eol
		LEFT JOIN dev_dtx_gc.staging.stg_member_admissions AS ad
			ON eol.memberid = ad.memberid
				AND ad.claimlineplaceofservicecode = 21
				AND (
					ad.claimlinerevenuecode >= 200
					AND ad.claimlinerevenuecode <= 209
				)
				AND ad.dateofservice >= eol.memberdeathdate - 30
				AND eol.memberdeathdate >= ad.dateofservice
)

SELECT
	iv.memberid,
	1 AS denominator,
	CASE
		WHEN iv.icu_visit_count = 0
			THEN 1
		ELSE 0
	END AS numerator,
	iv.episode_start_date,
	iv.episode_end_date,
	iv.participatingprovidernpi,
	iv.perf_period_key,
	iv.principalcancercode,
	iv.cancerdiagnosisgroupcode,
	iv.tin,
	iv.lineofbusiness,
	iv.memberdeathdate,
	DATE_TRUNC(MONTH, iv.memberdeathdate) AS contextdate,
	iv.dateofservice AS lasticuvisitdate
FROM icu_visits AS iv
WHERE iv.row_no = 1