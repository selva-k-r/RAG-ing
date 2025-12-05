-- DBT Model: stg_discontinued_attribution
-- Database: dev_dtx_gc
-- Schema: staging
-- Alias: stg_discontinued_attribution



WITH discontinued_attribution AS (
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
	lineofbusiness
FROM dev_dtx_gc.staging.stg_attribution_all
WHERE attributionrecordtype = 'DEL'
)
SELECT 
	da.*,
	hm.ishospicemember,
	map.tin_group_1,
	map.tin_group_2,
	map.tin_group_3,
	CONCAT(da.memberid, '_', da.attributedprovidertaxid)
		AS memberid_attributedtin,
	CONCAT(
		COALESCE(da.attributednpiproviderid, ''),
		'_',
		da.attributedprovidertaxid
	) AS participatingnpi_attributedtin,
	DATE_TRUNC('seconds', SYSDATE()) AS recordinsertiondate_utc
FROM discontinued_attribution AS da
	LEFT JOIN
		dev_dtx_gc.staging.stg_member_hospice_mapping AS hm
		ON da.memberid = hm.memberid AND da.perf_period_key = hm.perf_period_key AND da.lineofbusiness = hm.lineofbusiness
	LEFT JOIN dev_dtx_gc.staging.stg_client_tin_mapping AS map
		ON da.attributedprovidertaxid = map.tin