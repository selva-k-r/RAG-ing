-- DBT Model: stg_dates
-- Database: dev_dtx_gc
-- Schema: staging
-- Alias: stg_dates



WITH seq (n) AS (
	SELECT DATEADD(DAY, 1 * SEQ4(), '1/1/2018')
	FROM TABLE(GENERATOR(ROWCOUNT => (3288)))
),

d (d) AS (
	SELECT n FROM seq
),

src AS (
	SELECT
		DATE(d) AS thedate,
		DAY(d) AS theday,
		DAYNAME(d) AS thedayname,
		WEEK(d) AS theweek,
		WEEKISO(d) AS theisoweek,
		DAYOFWEEK(d) AS thedayofweek,
		MONTH(d) AS themonth,
		MONTHNAME(d) AS themonthname,
		QUARTER(d) AS thequarter,
		YEAR(d) AS theyear,
		DATE_TRUNC('month', D) AS thefirstofmonth,
		DATEADD(
			'day', -1,
			DATEADD(
				'year', 1,
				DATE_TRUNC('year', D)
			)
		) AS thelastofyear,
		DAYOFYEAR(d) AS thedayofyear
	FROM d
),

dim AS (
	SELECT
		thedate AS date,
		thedayname AS dayofweek,
		thedayofweek,
		thedayofyear AS dayofyear,
		theweek AS weekofyear,
		themonth AS month,
		themonthname AS monthname,
		thequarter AS quarter,
		theyear AS year,
		TO_CHAR(thedate, 'YYYYMMDD') AS dimdatekey,
		RIGHT('0' + TO_VARCHAR(theday), 2) AS day,
		TO_VARCHAR(CASE
			WHEN theday / 10 = 1 THEN 'th' ELSE
				CASE RIGHT(
					theday, 1)
					WHEN '1' THEN 'st' WHEN '2' THEN 'nd'
					WHEN '3' THEN 'rd' ELSE 'th'
				END
		END) AS daysuffix,
		TO_NUMERIC(
			ROW_NUMBER()
				OVER
				(
					PARTITION BY thefirstofmonth, thedayofweek
					ORDER BY thedate
				)
		) AS dowinmonth,
		TO_NUMERIC(
			DENSE_RANK()
				OVER
				(
					PARTITION BY theyear, themonth
					ORDER BY theweek
				)
		) AS weekofmonth,
		CASE thequarter
			WHEN 1 THEN 'First' WHEN 2 THEN 'Second'
			WHEN 3 THEN 'Third' WHEN 4 THEN 'Fourth'
		END AS quartername,
		TO_CHAR(thedate, 'MM/DD/YYYY') AS standarddate,
		TO_CHAR(thedate, 'MON-YYYY') AS monthyear,
		TO_NUMERIC(TO_CHAR(thedate, 'YYYYMM')) AS monthyearkey
	FROM src
)

SELECT
	*,
	CONVERT_TIMEZONE('UTC', 'US/Eastern', SYSDATE()) AS last_refresh_date
FROM dim