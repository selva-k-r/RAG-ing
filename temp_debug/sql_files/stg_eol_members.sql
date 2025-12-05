-- DBT Model: stg_eol_members
-- Database: dev_dtx_gc
-- Schema: staging
-- Alias: stg_eol_members



SELECT
	ep.memberid,
	ep.episode_start_date,
	ep.episode_end_date,
	ep.participatingprovidernpi,
	ep.principalcancercode,
	ep.cancerdiagnosisgroupcode,
	ep.tin,
	ep.lineofbusiness,
	ep.perf_period_key,
	m.memberdeathdate
FROM dev_dtx_gc.staging.stg_episodes AS ep
	INNER JOIN dev_dtx_gc.staging.STG_MEMBER AS m
		ON ep.memberid = m.memberid
			AND ep.episode_start_date <= m.memberdeathdate
			AND ep.episode_end_date >= m.memberdeathdate
QUALIFY ROW_NUMBER() 
	OVER (PARTITION BY ep.memberid 
			ORDER BY m.memberdeathdate ASC
			, ep.episode_start_date ASC) = 1