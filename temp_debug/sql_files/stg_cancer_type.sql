-- DBT Model: stg_cancer_type
-- Database: dev_dtx_gc
-- Schema: staging
-- Alias: stg_Cancer_Type



SELECT DISTINCT
	cancerdiagnosisgroupcode,
	cancertype,
	DATE_TRUNC('seconds', SYSDATE()) AS recordinsertiondate_utc
FROM dev_dtx_gc.staging.stg_attribution