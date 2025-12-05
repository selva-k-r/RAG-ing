-- DBT Model: stg_attribution
-- Database: dev_dtx_gc
-- Schema: staging
-- Alias: stg_attribution



WITH active_attributions AS (
SELECT
	memberid,
	cancerdiagnosisgroupcode,
	cancertype,
	memberkey,
	icsiteid,
	fileprocesseddatetime,
	attributedproviderid,
	attributednpiproviderid,
	attributedproviderfirstname,
	attributedproviderlastname,
	attributedproviderorganizationname,
	attributedproviderstreet1address,
	attributedproviderstreet2address,
	attributedprovidercityaddress,
	attributedproviderstateaddress,
	attributedproviderzipcodeaddress,
	attributionperiodbegindate,
	attributionperiodenddate,
	attributedprovidertaxid,
	providerentityname,
	programidentifier,
	attributionrecordtype,
	perf_period_key,
	memberageonattributedmonth,
	customcancercode,
	principalcancercode,
	lineofbusiness
FROM dev_dtx_gc.staging.stg_attribution_all
WHERE attributionrecordtype = 'ACT'
)

SELECT
	sa.*,
	hm.ishospicemember,
	map.tin_group_1,
	map.tin_group_2,
	map.tin_group_3,
	CONCAT(sa.memberid, '_', sa.attributedprovidertaxid)
		AS memberid_attributedtin,
	CONCAT(
		COALESCE(sa.attributednpiproviderid, ''),
		'_',
		sa.attributedprovidertaxid
	) AS participatingnpi_attributedtin,
	DATE_TRUNC('seconds', SYSDATE()) AS recordinsertiondate_utc
FROM active_attributions AS sa
	LEFT JOIN
		dev_dtx_gc.staging.stg_member_hospice_mapping AS hm
		ON sa.memberid = hm.memberid AND sa.perf_period_key = hm.perf_period_key AND sa.lineofbusiness = hm.lineofbusiness
	LEFT JOIN dev_dtx_gc.staging.stg_client_tin_mapping AS map
		ON sa.attributedprovidertaxid = map.tin