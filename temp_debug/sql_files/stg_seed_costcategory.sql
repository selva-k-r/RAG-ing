-- DBT Model: stg_seed_costcategory
-- Database: dev_dtx_gc
-- Schema: staging
-- Alias: stg_seed_costcategory



SELECT DISTINCT place_of_service_name AS costcategory
FROM dev_dtx_gc.staging.stg_seed_place_of_service_mapping
UNION ALL
SELECT 'Chemo & Drugs (Medical)'
UNION ALL
SELECT 'Retail Pharmacy'