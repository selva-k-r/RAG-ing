-- DBT Model: stg_participating_provider
-- Database: dev_dtx_gc
-- Schema: staging
-- Alias: stg_participating_provider



WITH distinctprovider AS (
	SELECT DISTINCT
		LPAD(participatingprovidernpi, 10, 0) AS participatingprovidernpi,
		tin
	FROM dev_dtx_gc.staging.stg_episodes
	WHERE tin IS NOT NULL

	UNION ALL

	SELECT DISTINCT
		LPAD(sa.attributednpiproviderid, 10, 0) AS participatingprovidernpi,
		sa.attributedprovidertaxid AS tin
	FROM dev_dtx_gc.staging.stg_attribution AS sa
	WHERE NOT EXISTS (
			SELECT DISTINCT
				se.participatingprovidernpi,
				se.tin
			FROM dev_dtx_gc.staging.stg_episodes AS se
			WHERE se.participatingprovidernpi = sa.attributednpiproviderid AND se.tin = sa.attributedprovidertaxid
		) AND sa.attributedprovidertaxid IS NOT NULL
)

SELECT
	p.participatingprovidernpi AS npi,
	sp.provider_name,
	sp.provider_city_name,
	sp.provider_state_name,
	sp.provider_postal_code,
	sp.taxonomy_code,
	sp.npi_deactivation_date,
	sp.provider_specialty,
	p.tin AS medicalfacilitytin,
	CONCAT(
		COALESCE(p.participatingprovidernpi, ''), '_', p.tin
	) AS participatingnpi_attributedtin,
	NULL AS region,
	DATE_TRUNC('seconds', SYSDATE()) AS recordinsertiondate_utc,
	map.tin_group_1,
	map.tin_group_2,
	map.tin_group_3
FROM distinctprovider AS p
	LEFT JOIN dev_dtx_gc.staging.stg_provider AS sp
		ON p.participatingprovidernpi = sp.npi
	LEFT JOIN dev_dtx_gc.staging.stg_client_tin_mapping AS map
		ON p.tin = map.tin