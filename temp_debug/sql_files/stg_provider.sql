-- DBT Model: stg_provider
-- Database: dev_dtx_gc
-- Schema: staging
-- Alias: stg_provider



WITH distinctParticipatingProvider as (
   SELECT DISTINCT memberid,
   participatingprovidernpi
   FROM dev_dtx_gc.staging.stg_episodes
   UNION ALL
   SELECT DISTINCT sa.memberid,
   sa.attributednpiproviderid as participatingprovidernpi
   FROM dev_dtx_gc.staging.stg_attribution sa 
   WHERE NOT EXISTS (
      SELECT DISTINCT se.memberid, se.participatingprovidernpi 
      FROM dev_dtx_gc.staging.stg_episodes se 
      WHERE se.memberid = sa.memberid AND se.participatingprovidernpi = sa.attributednpiproviderid
      )
)
, qualified_providers as (
    SELECT DISTINCT
    c.claimbillingprovidernpinumber,
    c.claimrenderingprovidernpinumber,
    p.claimpharmacynationalprovideridentifier,
    p.claimprescribingprovidernpinumber,
    e.participatingprovidernpi
    FROM distinctParticipatingProvider e
    LEFT JOIN dev_dtx_gc.IC1.CLAIM c 
    ON e.memberid = c.memberid
    LEFT JOIN dev_dtx_gc.IC1.CLAIMPHARMACY p
    ON e.memberid = p.memberid    
),

npilist AS (
	SELECT DISTINCT npi FROM
		(
			SELECT claimbillingprovidernpinumber AS npi FROM qualified_providers
			UNION ALL
			SELECT claimrenderingprovidernpinumber AS npi FROM qualified_providers
			UNION ALL
			SELECT claimpharmacynationalprovideridentifier AS npi FROM qualified_providers
			UNION ALL
			SELECT claimprescribingprovidernpinumber AS npi FROM qualified_providers
			UNION ALL
			SELECT participatingprovidernpi AS npi FROM qualified_providers
			UNION ALL
			SELECT aimprovidernpinumber FROM dev_dtx_gc.IC1.ANTHEMAIM    -- IC-16752:will pick NPI's missing from attribution and present in AIM data
		) AS npi
),

taxonomy_specialty_mapping AS (
	SELECT
		concept_name AS provider_specialty,
		concept_code
	FROM PROD_INTELLIGENCE_DTX.IC_TO_ANTHEM.CONCEPT
	WHERE domain_id = 'Provider Specialty'
		AND concept_class_id = 'NUCC'
)

SELECT
	nl.npi,
	UPPER(IFF(
		nd.entity_type_code = 2, nd.provider_organization_name_legal_business_name,
		COALESCE(nd.provider_last_name_legal_name, '') || ', ' || COALESCE(nd.provider_first_name, '')
	)) AS provider_name,
	nd.provider_business_practice_location_address_city_name AS provider_city_name,
	nd.provider_business_practice_location_address_state_name AS provider_state_name,
	nd.provider_business_practice_location_address_postal_code AS provider_postal_code,
	nd.healthcare_provider_taxonomy_code_1 AS taxonomy_code,
	nd.npi_deactivation_date,
	ts.provider_specialty
FROM npilist AS nl
	LEFT JOIN
		
			PROD_INTELLIGENCE_DTX.IC_TO_ANTHEM.NPIDATA AS nd
		
		ON nl.npi = nd.npi
	LEFT JOIN taxonomy_specialty_mapping AS ts
		ON ts.concept_code = nd.healthcare_provider_taxonomy_code_1
WHERE nl.npi IS NOT NULL