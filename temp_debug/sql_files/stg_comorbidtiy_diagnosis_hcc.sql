-- DBT Model: stg_comorbidtiy_diagnosis_hcc
-- Database: dev_dtx_gc
-- Schema: staging
-- Alias: stg_comorbidtiy_diagnosis_hcc


/*
    The result of this transform will provide a table, with structure:
        COMORBIDITY
        ,COMORBIDITY_DIAGNOSIS_CODE
        ,HCC_CODEs AS HCC_CODE
        ,HCC_CODES AS RxHCC_CODE,
        ,EFFECTIVE_START_DATE
        ,Effective_End_Date

    Any Cormbidity/Diagnosis pairs that have both HCC and RxHCC will be in one row.
    All Others will have a blank HHC code or blank RxHCC code

*/

-- first get the all the diagnosis and comorbidities that match up

WITH comorbidity_diagnosis_matches AS (
	SELECT DISTINCT
		c.comorbidity,
		h.description,
		h.diagnosis_code AS comorbidity_diagnosis_code,
		h.hcc_codes
	FROM dev_dtx_gc.staging.stg_seed_comorbidtiy_hcc AS c
		INNER JOIN dev_dtx_gc.staging.stg_hcc_mapping AS h
			ON c.hcc_codes = h.hcc_codes
),
-- find by Comorbidity the Diagnosis that have both HCC codes and RxHcc codes so they can be deplayed together
-- Comorbidity_Diagnosis_has_HCC_and has the structure we want to end up with

comorbidity_diagnosis_has_hcc_and_rxhcc AS (
	SELECT DISTINCT
		h.comorbidity,
		h.description,
		h.comorbidity_diagnosis_code,
		h.hcc_codes AS hcc_code,
		r.hcc_codes AS rxhcc_code
	FROM dev_dtx_gc.staging.stg_seed_hcc_mapping_hcc_and_rxhcc AS s
		INNER JOIN comorbidity_diagnosis_matches AS h
			ON
				s.diagnosis_code = h.comorbidity_diagnosis_code
				AND s.hcc_code = h.hcc_codes
		INNER JOIN
			comorbidity_diagnosis_matches
				AS r
			ON s.diagnosis_code = r.comorbidity_diagnosis_code
				AND s.rxhcc_code = r.hcc_codes
				AND h.comorbidity = r.comorbidity
),

-- now we need to get the rest of the "Comorbidity_Diagnosis_Matches" that did not have both HCC and RxHCC code
-- this is done but putting Comorbidity_Diagnosis_has_HCC_and_RxHCC back into the form of Comorbidity_Diagnosis_Matches
-- then do an except
hcc_and_rxhcc AS (

	SELECT
		comorbidity,
		description,
		comorbidity_diagnosis_code,
		hcc_code
	FROM comorbidity_diagnosis_has_hcc_and_rxhcc
	UNION DISTINCT
	SELECT
		comorbidity,
		description,
		comorbidity_diagnosis_code,
		rxhcc_code AS hcc_code
	FROM comorbidity_diagnosis_has_hcc_and_rxhcc
),

-- now an except is done to remove the matches with both HCC and RXHCC
comorbidity_diagnosis_single_hcc_or_rxhcc AS (
	SELECT
		comorbidity,
		description,
		comorbidity_diagnosis_code,
		hcc_codes
	FROM comorbidity_diagnosis_matches
	EXCEPT
	SELECT
		comorbidity,
		description,
		comorbidity_diagnosis_code,
		hcc_code
	FROM hcc_and_rxhcc

),

alltogether AS (
	SELECT
		comorbidity,
		description,
		comorbidity_diagnosis_code,
		IFF(hcc_codes LIKE 'HCC%', hcc_codes,NULL) AS hcc_code,
		IFF(hcc_codes LIKE 'RxHCC%', hcc_codes,NULL) AS rxhcc_code
	FROM comorbidity_diagnosis_single_hcc_or_rxhcc
	UNION DISTINCT
	SELECT
		comorbidity,
		description,
		comorbidity_diagnosis_code,
		hcc_code,
		rxhcc_code
	FROM comorbidity_diagnosis_has_hcc_and_rxhcc

)

SELECT *,
	comorbidity
	|| comorbidity_diagnosis_code
	|| COALESCE(hcc_code, '')
	|| COALESCE(rxhcc_code, '') AS comorbidity_key
FROM alltogether