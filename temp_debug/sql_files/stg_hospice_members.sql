-- DBT Model: stg_hospice_members
-- Database: dev_dtx_gc
-- Schema: staging
-- Alias: stg_hospice_members


SELECT DISTINCT
	ad.memberid,
	ad.dateofservice,
	ad.dateofserviceend,
	e.perf_period_key,
	e.lineofbusiness
FROM dev_dtx_gc.staging.stg_member_admissions AS ad
	INNER JOIN dev_dtx_gc.staging.stg_episodes AS e
		ON ad.memberid = e.memberid
			AND ad.dateofservice >= e.episode_start_date AND  ad.dateofservice <= e.episode_end_date
WHERE UPPER(e.lineofbusiness) = 'COMMERCIAL' AND (
	(
		ad.claimlinerevenuecode >= 650
		AND ad.claimlinerevenuecode <= 659
	)
	OR ad.claimlineplaceofservicecode = 34
)

UNION

SELECT DISTINCT
	ad.memberid,
	ad.hspcelectiondate AS dateofservice,
	ad.hspcdischargedate AS dateofserviceend,
	e.perf_period_key,
	e.lineofbusiness
FROM dev_dtx_gc.IC1.HOSPICE AS ad
	INNER JOIN dev_dtx_gc.staging.stg_episodes AS e
		ON ad.memberid = e.memberid
			AND ad.hspcelectiondate >= e.episode_start_date AND ad.hspcelectiondate <= e.episode_end_date
WHERE UPPER(e.lineofbusiness) = 'MEDICARE'