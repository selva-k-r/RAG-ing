-- DBT Model: stg_qm6
-- Database: dev_dtx_gc
-- Schema: staging
-- Alias: stg_qm6



-- Denominator Logic:
-- . Member attribution 
-- AND
-- . Date of death
-- Numerator Logic:
/*This measure involves calculating an outcome to determine
 members who had fewer than two emergency department visits
 in the last 30 days of life. “Performance Met” for this
 numerator indicates the member had fewer than two emergency
 department visits in the last 30 days of life: indicating a high quality of care.
*/

WITH ed_visits AS (
	SELECT
		eol.memberid,
		eol.episode_start_date,
		eol.episode_end_date,
		eol.memberdeathdate,
		eol.participatingprovidernpi,
		eol.perf_period_key,
		eol.principalcancercode,
		eol.cancerdiagnosisgroupcode,
		eol.tin,
		eol.lineofbusiness,
		SUM(CASE
			WHEN ad.dateofservice IS NULL
				THEN 0
			ELSE 1
		END) OVER (
			PARTITION BY
				eol.memberid,
				eol.episode_start_date
		) AS ed_visit_count,
		ROW_NUMBER() OVER (
			PARTITION BY eol.memberid
			ORDER BY ad.dateofservice DESC
		) AS row_no,
		ad.dateofservice
	FROM dev_dtx_gc.staging.stg_eol_members AS eol
		LEFT JOIN dev_dtx_gc.staging.stg_member_admissions AS ad
			ON eol.memberid = ad.memberid
				AND (
					ad.claimlineplaceofservicecode IN (22, 23)
					AND (
						ad.claimlinerevenuecode IN ('0450', '0451', '0452', '0453', '0454', '0455', '0457', '0458', '0459')
						OR (ad.claimlinerevenuecode = '0456' AND ad.claimlinehealthservicecode IN ('99281', '99282', '99283', '99284', '99285'))
					)
				)
				AND ad.dateofservice >= eol.memberdeathdate - 30
				AND eol.memberdeathdate >= ad.dateofservice
)

SELECT
	ev.memberid,
	1 AS denominator,
	CASE
		WHEN ev.ed_visit_count <= 1
			THEN 1
		ELSE 0
	END AS numerator,
	ev.episode_start_date,
	ev.episode_end_date,
	ev.participatingprovidernpi,
	ev.perf_period_key,
	ev.principalcancercode,
	ev.cancerdiagnosisgroupcode,
	ev.tin,
	ev.lineofbusiness,
	ev.memberdeathdate,
	DATE_TRUNC(MONTH, ev.memberdeathdate) AS contextdate,
	ev.dateofservice AS lastedvisitdate
FROM ed_visits AS ev
WHERE ev.row_no = 1