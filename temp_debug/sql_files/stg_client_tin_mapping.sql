-- DBT Model: stg_client_tin_mapping
-- Database: dev_dtx_gc
-- Schema: staging
-- Alias: stg_client_tin_mapping



WITH group_tin AS (
	SELECT
		map.groupid AS role,
		map.individualid AS tin,
		ROW_NUMBER() OVER (
			PARTITION BY tin
			ORDER BY role
		) AS group_number,
		CASE WHEN group_number = 1 THEN role END AS tin_group_1,
		CASE WHEN group_number = 2 THEN role END AS tin_group_2,
		CASE WHEN group_number = 3 THEN role END AS tin_group_3
	FROM DEV_INTELLIGENCE_WEB.IC_TO_ANTHEM.ANTHEM_CLIENT_TIN_MAPPING AS map
)

SELECT
	gt.tin,
	MAX(gt.tin_group_1) AS tin_group_1,
	MAX(gt.tin_group_2) AS tin_group_2,
	MAX(gt.tin_group_3) AS tin_group_3
FROM group_tin AS gt
GROUP BY gt.tin