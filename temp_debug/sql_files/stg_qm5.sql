-- DBT Model: stg_qm5
-- Database: dev_dtx_gc
-- Schema: staging
-- Alias: stg_qm5



-- Denominator Logic:
-- . Member attribution 
-- AND
-- . Date of death
-- Numerator Logic:
-- Count of all patients that died minus the unique count of patients that received chemotherapy treatment in the last 14 days of death by comparing death date to date of service of chemo administration claim.

WITH member_chemo AS (
	SELECT
		eol.memberid,
		eol.episode_start_date,
		eol.episode_end_date,
		CASE
			WHEN mc.memberid IS NULL
				THEN 0
			ELSE 1
		END AS chemo_exists,
		eol.memberdeathdate,
		mc.chemodate,
		mc.chemocode,
		eol.participatingprovidernpi,
		eol.perf_period_key,
		eol.principalcancercode,
		eol.cancerdiagnosisgroupcode,
		eol.tin,
		eol.lineofbusiness,
		ROW_NUMBER() OVER (
			PARTITION BY eol.memberid
			ORDER BY chemo_exists DESC
		) AS row_no
	FROM dev_dtx_gc.staging.stg_eol_members AS eol
		LEFT JOIN dev_dtx_gc.staging.stg_member_chemotherapy AS mc
			ON eol.memberid = mc.memberid
				AND mc.chemodate >= DATEADD(DAY, -14, eol.memberdeathdate)
				AND eol.memberdeathdate >= mc.chemodate
)

SELECT
	mc.memberid,
	1 AS denominator,
	CASE mc.chemo_exists
		WHEN 0
			THEN 1
		ELSE 0
	END AS numerator,
	mc.episode_start_date,
	mc.episode_end_date,
	mc.participatingprovidernpi,
	mc.perf_period_key,
	mc.principalcancercode,
	mc.cancerdiagnosisgroupcode,
	mc.tin,
	mc.lineofbusiness,
	mc.memberdeathdate,
	DATE_TRUNC(MONTH, mc.memberdeathdate) AS contextdate,
	mc.chemodate,
	mc.chemocode
FROM member_chemo AS mc
WHERE mc.row_no = 1