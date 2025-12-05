-- DBT Model: stg_seed_hcc_mapping_hcc_and_rxhcc
-- Database: dev_dtx_gc
-- Schema: staging
-- Alias: stg_seed_hcc_mapping_hcc_and_rxhcc



--this is needed to see which diagnosis have both HCC and RxHCC
SELECT
	s.diagnosis_code,
	s.description,
	s.cms_hcc_v24_2022,
	s.rxhcc_v08_2022,
	'HCC' || s.cms_hcc_v24 AS hcc_code,
	'RxHCC' || s.rxhcc_v08 AS rxhcc_code
FROM dev_dtx_gc.anthemreporting_seed.seed_hccmapping AS s