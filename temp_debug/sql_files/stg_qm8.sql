-- DBT Model: stg_qm8
-- Database: dev_dtx_gc
-- Schema: staging
-- Alias: stg_qm8



-- Denominator Logic:
-- . Member attribution 
-- AND
-- . Date of death
-- Numerator Logic:
/* This measure involves calculating an outcome to determine
 members who utilized hospice during the measurement period.
  “Performance Met” for this numerator indicates the member utilized
   hospice during the measurement period: indicating a high quality of care.
*/

WITH groupon            -- grouped continuous dates to each admission
AS (
	SELECT
		em.memberid,
		em.memberdeathdate,
		h.dateofservice,
		h.dateofserviceend,
		DATEDIFF(
			DAY,
			MIN(h.dateofservice) OVER (PARTITION BY em.memberid),
			h.dateofservice
		)
		- ROW_NUMBER() OVER (
			PARTITION BY em.memberid
			ORDER BY h.dateofservice ASC
		) AS admissiongroup
	FROM dev_dtx_gc.staging.stg_eol_members AS em
		INNER JOIN dev_dtx_gc.staging.stg_hospice_members AS h
			ON em.memberid = h.memberid AND em.lineofbusiness = h.lineofbusiness AND em.perf_period_key = h.perf_period_key
)

,
latesthospiceadmission              -- picking latest admission
AS (
	SELECT
		memberid,
		memberdeathdate,
		dateofservice,
		dateofserviceend,
		admissiongroup,
		RANK() OVER (
			PARTITION BY memberid
			ORDER BY admissiongroup DESC
		) AS rank
	FROM groupon
)

,
finalqm8 AS (
	SELECT
		memberid,
		memberdeathdate,
		1 AS numerator,
		MIN(dateofservice) AS hospicestart,
		MAX(dateofserviceend) AS hospiceend,
		DATEDIFF(DAY, hospicestart, memberdeathdate) AS hospicedays
	FROM latesthospiceadmission
	WHERE rank = 1
	GROUP BY
		memberid,
		memberdeathdate
)

SELECT
	em.memberid,
	1 AS denominator,
	COALESCE(h.numerator, 0) AS numerator,
	em.episode_start_date,
	em.episode_end_date,
	em.participatingprovidernpi,
	em.perf_period_key,
	em.principalcancercode,
	em.cancerdiagnosisgroupcode,
	em.tin,
	em.lineofbusiness,
	em.memberdeathdate,
	DATE_TRUNC(MONTH, em.memberdeathdate) AS contextdate,
	h.hospicestart AS hospicedate,
	h.hospiceend AS hospiceenddate
FROM dev_dtx_gc.staging.stg_eol_members AS em
	LEFT OUTER JOIN finalqm8 AS h
		ON em.memberid = h.memberid