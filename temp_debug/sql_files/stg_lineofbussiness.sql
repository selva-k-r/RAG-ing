-- DBT Model: stg_lineofbussiness
-- Database: dev_dtx_gc
-- Schema: staging
-- Alias: stg_lineofbussiness




SELECT
	lineofbusiness,
	CASE
		WHEN
			lineofbusiness IN ('Grp_Medicare', 'Medicare', 'MEDICARE')
			THEN 'Medicare Advantage'
		WHEN
			lineofbusiness IN ('Commercial', 'COMMERCIAL')
			THEN 'Commercial'
		ELSE lineofbusiness
	END AS display_lob
FROM
	(
		SELECT DISTINCT lineofbusinessidentifier AS lineofbusiness
		FROM dev_dtx_gc.IC1.MASTEREPISODE
		UNION DISTINCT
		SELECT DISTINCT INITCAP(lineofbusinessidentifier) AS lineofbusiness,
		FROM dev_dtx_gc.IC1.ATTRIBUTION
		UNION DISTINCT
		SELECT DISTINCT COALESCE(INITCAP(lineofbusinessidentifier), 'NA') AS lineofbusiness
		FROM dev_dtx_gc.IC1.CCF
		ORDER BY lineofbusiness
	) AS unionlist