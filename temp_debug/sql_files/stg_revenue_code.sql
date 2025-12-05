-- DBT Model: stg_revenue_code
-- Database: dev_dtx_gc
-- Schema: staging
-- Alias: stg_revenue_code



SELECT *
FROM PROD_INTELLIGENCE_DTX.IC_TO_ANTHEM.CONCEPT
WHERE domain_id = 'Revenue Code' AND vocabulary_id = 'Revenue Code'