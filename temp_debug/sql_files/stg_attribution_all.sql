-- DBT Model: stg_attribution_all
-- Database: dev_dtx_gc
-- Schema: staging
-- Alias: stg_attribution_all



/**********************************************************************************************************

IC-14282 | recentmemberdata is configured to fetch only one record per month regardless of attribution start date in a month | Selva

**********************************************************************************************************/

WITH latestrecordmember0 AS (
	SELECT DISTINCT
		memberid,
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
		attributedprovidertaxid,
		providerentityname,
		programidentifier,
		attributionrecordtype,
		DATE_TRUNC(MONTH, attributionperiodbegindate)
			AS attributionperiodbegindate,
		-- This is used to identify the status of member
		LAST_DAY(attributionperiodenddate, MONTH) AS attributionperiodenddate,
		UPPER(lineofbusinessidentifier) AS lineofbusiness,
		ROW_NUMBER()
			OVER (
				PARTITION BY
					memberid, DATE_TRUNC(MONTH, attributionperiodbegindate)
				ORDER BY
					fileprocesseddatetime ASC, attributionperiodenddate DESC
			)
			AS recentmemberdata
	FROM dev_dtx_gc.IC1.ATTRIBUTION
),

latestrecordmember AS (
	SELECT * FROM latestrecordmember0
	WHERE recentmemberdata = 1
),

member_cancer_info AS (
	SELECT
		a.memberid,
		COALESCE(ct.icd10code, 'ZZZZZ') AS cancerdiagnosisgroupcode,
		COALESCE(ct.cancer_type, 'Unknown') AS cancertype,
		COALESCE(ct.icd10code, cl.claimlineprincipaldiagnosiscode, 'Unknown')
			AS customcancercode,
		COALESCE(cl.claimlineprincipaldiagnosiscode, 'Unknown')
			AS principalcancercode,
		CASE
			WHEN ct.cancer_type IS NULL THEN 1 WHEN
				ct.cancer_type LIKE 'Secondary%'
				THEN 2
			WHEN ct.cancer_type LIKE '%other%' THEN 3 ELSE 4
		END AS cancerorder,
		ROW_NUMBER()
			OVER (
				PARTITION BY a.memberid
				ORDER BY cancerorder DESC, cl.claimlineservicestartdate ASC
			)
			AS cancerorder_rn
	FROM latestrecordmember AS a
		LEFT JOIN dev_dtx_gc.IC1.CLAIM AS c
			ON a.memberid = c.memberid
		LEFT JOIN dev_dtx_gc.IC1.CLAIMLINE AS cl
			ON c.claimid = cl.claimid AND cl.claimlinestatuscode = 'APRVD'
		LEFT JOIN dev_dtx_gc.staging.stg_seed_ocm_cancer_types AS ct
			ON cl.claimlineprincipaldiagnosiscode LIKE (ct.icd10code || '%')
)

SELECT DISTINCT
	a.memberid,
	c.cancerdiagnosisgroupcode,
	c.cancertype,
	a.memberkey,
	a.icsiteid,
	a.fileprocesseddatetime,
	a.attributedproviderid,
	a.attributednpiproviderid,
	a.attributedproviderfirstname,
	a.attributedproviderlastname,
	a.attributedproviderorganizationname,
	a.attributedproviderstreet1address,
	a.attributedproviderstreet2address,
	a.attributedprovidercityaddress,
	a.attributedproviderstateaddress,
	a.attributedproviderzipcodeaddress,
	a.attributionperiodbegindate,
	a.attributionperiodenddate,
	a.attributedprovidertaxid,
	a.providerentityname,
	a.programidentifier,
	a.attributionrecordtype,
	pp.perf_period_key,
	c.customcancercode,
	c.principalcancercode,
	INITCAP(a.lineofbusiness) AS lineofbusiness,
	CASE
		WHEN m.memberbirthdate < CURRENT_DATE()
			THEN FLOOR(
					(
						DATEDIFF(
							MONTH, m.memberbirthdate, a.attributionperiodbegindate
						)
						-
						TO_NUMERIC(
							DATE_PART(DAY, a.attributionperiodbegindate)
							< DATE_PART(DAY, m.memberbirthdate)
						)
					) / 12
				)
	END AS memberageonattributedmonth
FROM latestrecordmember AS a
	LEFT JOIN member_cancer_info AS c
		ON a.memberid = c.memberid
	LEFT JOIN dev_dtx_gc.staging.STG_MEMBER AS m
		ON a.memberid = m.memberid
	LEFT JOIN dev_dtx_gc.staging.stg_seed_performance_period AS pp
		ON
			a.attributionperiodbegindate >= pp.perf_period_start_date
			AND a.attributionperiodbegindate <= pp.perf_period_end_date
WHERE c.cancerorder_rn = 1