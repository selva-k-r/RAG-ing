-- DBT Model: stg_member
-- Database: dev_dtx_gc
-- Schema: staging
-- Alias: STG_MEMBER



/*
As per IC1 documentation ICsiteId + Member ID should be unique and it should be used for primary key,
The data right now has duplicate and added the below code to remove duplicates.
*/
WITH members AS (
	SELECT DISTINCT
		m.memberid,
		m.memberbirthdate,
		m.memberdeathdate,
		m.membergendercode,
		m.memberracecode,
		m.membermedicaidnumber,
		m.membermedicarenumber,
		NULL AS medicalrecordnumber,
		m.fileprocesseddatetime,
		m.subscriberid,
		COALESCE(m.memberlastname, '')
		|| ', '
		|| COALESCE(m.memberfirstname, '') AS membername,
		CASE
			WHEN
				CAST(GETDATE() AS date) >= CAST(m.memberbirthdate AS date)
				AND CAST('1900-01-01' AS date)
				<= CAST(m.memberbirthdate AS date)
				THEN 1
			ELSE 0
		END AS valid_dob,
		ROW_NUMBER()
			OVER (
				PARTITION BY m.memberid
				ORDER BY
					valid_dob DESC,
					m.subscriberid ASC,
					m.memberdeathdate ASC,
					m.membermedicaidnumber ASC,
					m.membermedicarenumber ASC,
					m.membermiddlename ASC,
					m.memberlastname ASC,
					m.memberfirstname ASC,
					m.memberbirthdate ASC,
					m.membergendercode ASC,
					m.memberracecode ASC
			)
			AS rn
	FROM dev_dtx_gc.IC1.MEMBER AS m
)

SELECT
	m.memberid,
	m.membername,
	m.memberbirthdate,
	m.memberdeathdate,
	m.membergendercode,
	r.description AS memberrace,
	m.membermedicaidnumber,
	m.membermedicarenumber,
	m.medicalrecordnumber,
	m.fileprocesseddatetime,
	m.subscriberid,
	FLOOR(
		(
			DATEDIFF(MONTH, m.memberbirthdate, CURRENT_DATE())
			-
			TO_NUMERIC(DATE_PART(DAY, CURRENT_DATE()) < DATE_PART(DAY, m.memberbirthdate))
		) / 12
	) AS memberagecurrent
FROM members AS m
	LEFT JOIN dev_dtx_gc.staging.stg_seed_racevalueset AS r
		ON m.memberracecode = REPLACE(r.code, '-', '')
WHERE rn = 1

UNION ALL

SELECT DISTINCT
	e.memberid,
	NULL AS membername,
	e.birth_date AS memberbirthdate,
	e.dod AS memberdeathdate,
	e.gender AS membergendercode,
	e.race AS memberrace,
	NULL AS membermedicaidnumber,
	NULL AS membermedicarenumber,
	NULL AS medicalrecordnumber,
	'01/01/1900' AS fileprocesseddatetime,
	e.subscriberid,
	NULL AS memberagecurrent
FROM dev_dtx_gc.IC1.MASTEREPISODE AS e
WHERE NOT EXISTS (
		SELECT 1 FROM dev_dtx_gc.IC1.MEMBER AS m
		WHERE m.memberid = e.memberid
	)
QUALIFY ROW_NUMBER() OVER (
		PARTITION BY e.memberid
		ORDER BY e.subscriberid
	) = 1

UNION ALL

SELECT DISTINCT
	c.memberid,
	NULL AS membername,
	NULL AS memberbirthdate,
	NULL AS memberdeathdate,
	NULL AS membergendercode,
	NULL AS memberrace,
	NULL AS membermedicaidnumber,
	NULL AS membermedicarenumber,
	NULL AS medicalrecordnumber,
	'01/01/1900' AS fileprocesseddatetime,
	c.subscriberid,
	NULL AS memberagecurrent
FROM dev_dtx_gc.IC1.CCF AS c
WHERE NOT EXISTS (
		 SELECT 1 FROM dev_dtx_gc.IC1.MEMBER AS m
		WHERE m.memberid = c.memberid
		UNION ALL
		SELECT 1 FROM dev_dtx_gc.IC1.MASTEREPISODE AS e
		WHERE e.memberid = c.memberid
	)
QUALIFY ROW_NUMBER() OVER (
		PARTITION BY c.memberid
		ORDER BY c.subscriberid
	) = 1

UNION ALL

SELECT DISTINCT
	a.memberid,
	NULL AS membername,
	NULL AS memberbirthdate,
	NULL AS memberdeathdate,
	NULL AS membergendercode,
	NULL AS memberrace,
	NULL AS membermedicaidnumber,
	NULL AS membermedicarenumber,
	NULL AS medicalrecordnumber,
	'01/01/1900' AS fileprocesseddatetime,
	NULL AS subscriberid,
	NULL AS memberagecurrent
FROM dev_dtx_gc.IC1.ATTRIBUTION AS a
WHERE NOT EXISTS (
		 SELECT 1 FROM dev_dtx_gc.IC1.MEMBER AS m
		WHERE m.memberid = a.memberid
		UNION ALL
		SELECT 1 FROM dev_dtx_gc.IC1.MASTEREPISODE AS e
		WHERE e.memberid = a.memberid
		UNION ALL
		SELECT 1 FROM dev_dtx_gc.IC1.CCF AS c
		WHERE c.memberid = a.memberid
	)