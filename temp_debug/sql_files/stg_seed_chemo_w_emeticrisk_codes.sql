-- DBT Model: stg_seed_chemo_w_emeticrisk_codes
-- Database: dev_dtx_gc
-- Schema: staging
-- Alias: stg_seed_chemo_w_emeticrisk_codes



WITH concept AS (
	SELECT DISTINCT
		s.code,
		-- Upper to be consistent and TRIM to remove trailing Balnks
		s.code_type,
		COALESCE(s.agents, c.concept_name)
			AS agents,
		TRIM(UPPER(s.emetic_risk)) AS emetic_risk,
		ROW_NUMBER() OVER (
			PARTITION BY s.code
			ORDER BY
				c.valid_end_date DESC,
				c.concept_id ASC,
				c.concept_name DESC
		) AS row_no
	FROM dev_dtx_gc.anthemreporting_seed.seed_chemo_w_emeticrisk_codes AS s
		LEFT JOIN prod_intelligence_dtx.ic_to_anthem.concept AS c
			ON
				s.code = c.concept_code
				AND c.vocabulary_id = 'HCPCS'
-- DO-2081, 1st priority is the EndDate, 2nd is Low ConceptID, 3rd is Name
)

SELECT
	agents,
	emetic_risk,
	code,
	code_type
FROM concept
WHERE row_no = 1