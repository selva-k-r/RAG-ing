-- DBT Model: stg_pharmacy_provider
-- Database: dev_dtx_gc
-- Schema: staging
-- Alias: stg_pharmacy_provider



WITH distinctprovider AS (
	SELECT DISTINCT
		claimpharmacynationalprovideridentifier,
		medicalfacilitytin
	FROM dev_dtx_gc.staging.stg_claims
	WHERE medicalfacilitytin IS NOT NULL
)

SELECT
	p.claimpharmacynationalprovideridentifier AS npi,
	sp.provider_name,
	sp.provider_city_name,
	sp.provider_state_name,
	sp.provider_postal_code,
	sp.taxonomy_code,
	sp.npi_deactivation_date,
	sp.provider_specialty,
	p.medicalfacilitytin,
	map.tin_group_1,
	map.tin_group_2,
	map.tin_group_3,
	CONCAT(
		COALESCE(p.claimpharmacynationalprovideridentifier, ''),
		'_',
		p.medicalfacilitytin
	) AS pharmacynpi_attributedtin,
	DATE_TRUNC('seconds', SYSDATE()) AS recordinsertiondate_utc
FROM distinctprovider AS p
	LEFT JOIN dev_dtx_gc.staging.stg_provider AS sp
		ON p.claimpharmacynationalprovideridentifier = sp.npi
	LEFT JOIN dev_dtx_gc.staging.stg_client_tin_mapping AS map
		ON p.medicalfacilitytin = map.tin