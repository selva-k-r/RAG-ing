-- DBT Model: stg_member_tin_mapping
-- Database: dev_dtx_gc
-- Schema: staging
-- Alias: stg_member_tin_mapping


WITH mbr_tin_uniq AS (
	SELECT DISTINCT
		memberid,
		attributedprovidertaxid
	FROM dev_dtx_gc.staging.stg_attribution_all
)

SELECT
	m.memberid,
	m.membername,
	m.memberdeathdate,
	m.membergendercode,
	m.memberrace,
	m.membermedicaidnumber,
	m.membermedicarenumber,
	m.medicalrecordnumber,
	m.fileprocesseddatetime,
	m.subscriberid,
	m.memberagecurrent,
	sa.attributedprovidertaxid AS medicalfacilitytin,
	map.tin_group_1,
	map.tin_group_2,
	map.tin_group_3,
	TO_VARCHAR(m.memberbirthdate, 'MM/DD/YYYY') AS memberbirthdate,
	CONCAT(m.memberid, '_', sa.attributedprovidertaxid)
		AS memberid_attributedtin,
	DATE_TRUNC('seconds', SYSDATE()) AS recordinsertiondate_utc
FROM dev_dtx_gc.staging.STG_MEMBER AS m
	INNER JOIN mbr_tin_uniq AS sa
		ON m.memberid = sa.memberid
	LEFT JOIN dev_dtx_gc.staging.stg_client_tin_mapping AS map
		ON sa.attributedprovidertaxid = map.tin