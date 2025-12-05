-- DBT Model: stg_hcc_mapping
-- Database: dev_dtx_gc
-- Schema: staging
-- Alias: stg_hcc_mapping



-- this process the HCCMappingFY2021FY2022.csv file to fix into  the REFERENCE.HCC_MAPPING table
--REFERENCE.HCC_MAPPING
--      DIAGNOSIS_CODE VARCHAR(10) NOT NULL COLLATE 'en-ci',
--      DESCRIPTION  VARCHAR(300) NOT NULL COLLATE 'en-ci',
--      HCC_CODES CHAR(10) NOT NULL COLLATE 'en-ci',
--	    Model_Version VARCHAR(10) NOT NULL COLLATE 'en-ci',
--	    EFFECTIVE_START_DATE DATE NOT NULL 'en-ci','
--	    EFFECTIVE_END_DATE DATE NOT NULL 'en-ci'
-- Assume all the EFFECTIVE_START_DATE and EFFECTIVE_End_DATE are teh same
--

WITH hcc_mapping_transform AS (
SELECT
	diagnosis_code,
	description,
	hcc_code AS hcc_codes,
	'CMS HCC V24 2022' AS model_version
FROM dev_dtx_gc.staging.stg_seed_hcc_mapping_hcc_and_rxhcc
WHERE cms_hcc_v24_2022 = 'Yes'

UNION DISTINCT

SELECT
	diagnosis_code,
	description,
	rxhcc_code AS hcc_codes,
	'RxHCC V08 2022' AS model_version
FROM dev_dtx_gc.staging.stg_seed_hcc_mapping_hcc_and_rxhcc
WHERE rxhcc_v08_2022 = 'Yes'
)

SELECT
	diagnosis_code,
	description,
	hcc_codes,
	model_version
FROM hcc_mapping_transform