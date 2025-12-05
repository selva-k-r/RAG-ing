-- DBT Model: stg_medical_facility
-- Database: dev_dtx_gc
-- Schema: staging
-- Alias: stg_medical_facility



WITH distinctmedfac AS (
	SELECT
		providerentityname AS attributedproviderorganizationname,
		attributedproviderstreet1address,
		attributedproviderstreet2address,
		attributedprovidercityaddress,
		attributedproviderstateaddress,
		LPAD(attributedprovidertaxid, 9, 0) AS attributedprovidertaxid,
		LPAD(attributedproviderzipcodeaddress, 5, 0)
			AS attributedproviderzipcodeaddress,
		CONCAT(
			COALESCE(attributedproviderstreet1address, ''),
			COALESCE(CONCAT(', ', attributedproviderstreet2address), ''),
			COALESCE(CONCAT(', ', attributedprovidercityaddress), ''),
			COALESCE(CONCAT(', ', attributedproviderstateaddress), '')
		) AS medicalfacilitylocation,
		ROW_NUMBER()
			OVER (
				PARTITION BY attributedprovidertaxid
				ORDER BY fileprocesseddatetime DESC
			)
			AS recentdata
	FROM dev_dtx_gc.staging.stg_attribution
	WHERE
		attributedprovidertaxid IS NOT NULL
		OR LEN(TRIM(attributedprovidertaxid)) > 0
),

final_list AS (
	SELECT
		attributedprovidertaxid AS tin,
		attributedproviderorganizationname AS medicalfacilityorganizationname,
		attributedproviderstreet1address AS medicalfacilitystreet1address,
		attributedproviderstreet2address AS medicalfacilitystreet2address,
		attributedprovidercityaddress AS medicalfacilitycity,
		attributedproviderstateaddress AS medicalfacilitystate,
		attributedproviderzipcodeaddress AS medicalfacilityzipcodeaddress,
		medicalfacilitylocation,
		DATE_TRUNC('seconds', SYSDATE()) AS recordinsertiondate_utc
	FROM distinctmedfac
	WHERE recentdata = 1 AND attributedprovidertaxid IS NOT NULL

	UNION ALL

	SELECT DISTINCT
		LPAD(c.attributedprovidertaxid, 9, 0) AS tin,
		c.providergroupid AS medicalfacilityorganizationname,
		NULL AS medicalfacilitystreet1address,
		NULL AS medicalfacilitystreet2address,
		NULL AS medicalfacilitycity,
		NULL AS medicalfacilitystate,
		NULL AS medicalfacilityzipcodeaddress,
		NULL AS medicalfacilitylocation,
		DATE_TRUNC('seconds', SYSDATE()) AS recordinsertiondate_utc
	FROM dev_dtx_gc.staging.stg_care_coordination_fee AS c
	WHERE
		NOT EXISTS (
			SELECT 1 FROM distinctmedfac AS a
			WHERE
				LPAD(c.attributedprovidertaxid, 9, 0)
				= LPAD(a.attributedprovidertaxid, 9, 0)
		)
		AND c.attributedprovidertaxid IS NOT NULL
)

SELECT
	fl.*,
	map.tin_group_1,
	map.tin_group_2,
	map.tin_group_3
FROM final_list AS fl
	LEFT JOIN dev_dtx_gc.staging.stg_client_tin_mapping AS map
		ON fl.tin = map.tin