-- DBT Model: stg_billing_provider
-- Database: dev_dtx_gc
-- Schema: staging
-- Alias: stg_billing_provider



WITH distinctprovider AS (
	SELECT DISTINCT
		claimbillingprovidernpinumber,
		medicalfacilitytin
	FROM dev_dtx_gc.staging.stg_claims
	WHERE medicalfacilitytin IS NOT NULL
)

SELECT
	sp.npi,
	sp.provider_name,
	sp.provider_city_name,
	sp.provider_state_name,
	sp.taxonomy_code,
	sp.npi_deactivation_date,
	sp.provider_specialty,
	p.medicalfacilitytin,
	NULL AS region,
	map.tin_group_1,
	map.tin_group_2,
	map.tin_group_3,
	CASE
		WHEN
			LEN(sp.provider_postal_code) > 5
			THEN
				SUBSTR(sp.provider_postal_code, 1, 5)
				|| '-'
				|| SUBSTR(
					sp.provider_postal_code,
					6,
					(LEN(sp.provider_postal_code) - 5)
				)
		ELSE sp.provider_postal_code
	END AS provider_postal_code,
	CONCAT(
		COALESCE(p.claimbillingprovidernpinumber, ''), '_', p.medicalfacilitytin
	) AS billingnpi_attributedtin,
	DATE_TRUNC('seconds', SYSDATE()) AS recordinsertiondate_utc
FROM distinctprovider AS p
	LEFT JOIN dev_dtx_gc.staging.stg_provider AS sp
		ON p.claimbillingprovidernpinumber = sp.npi
	LEFT JOIN dev_dtx_gc.staging.stg_client_tin_mapping AS map
		ON p.medicalfacilitytin = map.tin