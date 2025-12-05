-- DBT Model: stg_qm2
-- Database: dev_dtx_gc
-- Schema: staging
-- Alias: stg_qm2



WITH calendar_months AS (
	SELECT DISTINCT DATE_TRUNC(MONTH, date) AS month_first_date
	FROM dev_dtx_gc.staging.stg_dates
),

qm2_raw_emetics_details AS (       --- IC-16505: Getting Highest Emetic risk available for each patient
	SELECT * FROM (
		SELECT
			c.memberid,
			ep.perf_period_key,
			e.code AS emetic_code,
			CONCAT_WS(' - ', e.code, e.agents) AS emetic_desc,
			cl.claimlineservicestartdate AS emetic_date,
			e.emetic_risk,
			CASE WHEN emetic_risk = 'HIGH' THEN 4
				WHEN emetic_risk = 'MODERATE 2' THEN 3
				WHEN emetic_risk = 'MODERATE 1' THEN 2
				ELSE 1
			END AS emetic_risk_number
		FROM dev_dtx_gc.IC1.CLAIM AS c
			INNER JOIN dev_dtx_gc.IC1.CLAIMLINE AS cl
				ON c.claimid = cl.claimid
			INNER JOIN dev_dtx_gc.staging.stg_episodes AS ep
				ON c.memberid = ep.memberid
					AND cl.claimlineservicestartdate >= ep.episode_start_date
					AND cl.claimlineservicestartdate <= ep.episode_end_date
			INNER JOIN dev_dtx_gc.staging.stg_seed_chemo_w_emeticrisk_codes AS e
				ON cl.claimlinehealthservicecode = e.code AND e.code_type = 'HCPCS'
		UNION ALL
		SELECT
			cp.memberid,
			ep.perf_period_key,
			e.code AS emetic_code,
			CONCAT_WS(' - ', e.code, e.agents) AS emetic_desc,
			cp.claimprescriptionfilleddate AS emetic_date,
			e.emetic_risk,
			CASE WHEN emetic_risk = 'HIGH' THEN 4
				WHEN emetic_risk = 'MODERATE 2' THEN 3
				WHEN emetic_risk = 'MODERATE 1' THEN 2
				ELSE 1
			END AS emetic_risk_number
		FROM dev_dtx_gc.IC1.CLAIMPHARMACY AS cp
			INNER JOIN dev_dtx_gc.staging.stg_episodes AS ep
				ON cp.memberid = ep.memberid
					AND cp.claimprescriptionfilleddate >= ep.episode_start_date
					AND cp.claimprescriptionfilleddate <= ep.episode_end_date
			INNER JOIN dev_dtx_gc.staging.stg_seed_chemo_w_emeticrisk_codes AS e
				ON e.code = LEFT(cp.claimpharmacygenericproductidentifier, 10) AND e.code_type = 'GPI10'
	)
),

qualified_chemo AS (   --- Getting only one emetic record per patient based on Risk rank
	SELECT e.*
	FROM qm2_raw_emetics_details AS e
	QUALIFY ROW_NUMBER() OVER (
			PARTITION BY e.memberid, e.perf_period_key
			ORDER BY e.emetic_risk_number DESC, e.emetic_date ASC
		) = 1
),

qualified_emetic_desc AS (   --- Getting all emetic records on Qualified Date to get consolidated Qualified Emetic desc
	SELECT
		qc.memberid,
		qc.perf_period_key,
		LISTAGG(DISTINCT re.emetic_desc, ', ') WITHIN GROUP (
			ORDER BY re.emetic_desc
		) AS qualified_emetic_desc
	FROM qualified_chemo AS qc
		LEFT OUTER JOIN qm2_raw_emetics_details AS re
			ON qc.memberid = re.memberid AND qc.emetic_date = re.emetic_date AND qc.emetic_desc = re.emetic_desc
	GROUP BY qc.memberid, qc.perf_period_key
),

consolidated_emetic_desc AS (   --- Getting all emetic records other than Qualified Date to get Consolidated Emetic desc
	SELECT
		qc.memberid,
		qc.perf_period_key,
		LISTAGG(DISTINCT re.emetic_desc, ', ') WITHIN GROUP (
			ORDER BY re.emetic_desc
		) AS consolidated_emetic_desc
	FROM qm2_raw_emetics_details AS re
		LEFT OUTER JOIN qualified_chemo AS qc
			ON re.memberid = qc.memberid AND re.emetic_date = qc.emetic_date AND re.emetic_desc <> qc.emetic_desc
	GROUP BY qc.memberid, qc.perf_period_key
),

qm2_emetics_details AS (
	SELECT
		e.*,
		qe.qualified_emetic_desc,
		COALESCE(ce.consolidated_emetic_desc, 'None') AS consolidated_emetic_desc
	FROM qualified_chemo AS e
		LEFT OUTER JOIN qualified_emetic_desc AS qe
			ON e.memberid = qe.memberid AND e.perf_period_key = qe.perf_period_key
		LEFT OUTER JOIN consolidated_emetic_desc AS ce
			ON e.memberid = ce.memberid AND e.perf_period_key = ce.perf_period_key
),

qm2_eme_antieme_details AS (       --- IC-16505: Getting first Antiemetic per class on or after Highest Emetic risk for each patient
	SELECT
		e.memberid,
		e.perf_period_key,
		e.emetic_code,
		e.qualified_emetic_desc AS emetic_desc,
		e.consolidated_emetic_desc,
		e.emetic_date,
		e.emetic_risk,
		e.emetic_risk_number,
		ae.antiemetic_code,
		ae.antiemetic_desc,
		ae.antiemetic_class,
		ae.antiemetic_date,
		ae.ht3_desc,
		ae.cort_desc,
		ae.dop_desc,
		ae.nk1_desc,
		ae.olz_desc
	FROM qm2_emetics_details AS e
		LEFT JOIN
			(
				SELECT
					e.memberid,
					a.code AS antiemetic_code,
					CONCAT_WS(' - ', a.code, a.generic) AS antiemetic_desc,
					CASE WHEN a.class = '5-HT3' THEN CONCAT_WS(' - ', a.code, a.generic) END AS ht3_desc,
					CASE WHEN a.class = 'CORT' THEN CONCAT_WS(' - ', a.code, a.generic) END AS cort_desc,
					CASE WHEN a.class = 'DOP' THEN CONCAT_WS(' - ', a.code, a.generic) END AS dop_desc,
					CASE WHEN a.class = 'NK1' THEN CONCAT_WS(' - ', a.code, a.generic) END AS nk1_desc,
					CASE WHEN a.class = 'OLZ' THEN CONCAT_WS(' - ', a.code, a.generic) END AS olz_desc,
					cl.claimlineservicestartdate AS antiemetic_date,
					a.class AS antiemetic_class,
					ep.perf_period_key
				FROM qm2_emetics_details AS e
					INNER JOIN dev_dtx_gc.IC1.CLAIM AS c
						ON e.memberid = c.memberid
					INNER JOIN dev_dtx_gc.IC1.CLAIMLINE AS cl
						ON c.claimid = cl.claimid
							AND e.emetic_date <= cl.claimlineservicestartdate
					INNER JOIN dev_dtx_gc.staging.stg_episodes AS ep
						ON c.memberid = ep.memberid
							AND cl.claimlineservicestartdate >= ep.episode_start_date
							AND cl.claimlineservicestartdate <= ep.episode_end_date
					INNER JOIN dev_dtx_gc.staging.stg_seed_antiemetics AS a
						ON cl.claimlinehealthservicecode = a.code
							AND a.code_type = 'HCPCS'
				UNION ALL
				SELECT
					e.memberid,
					a.code AS antiemetic_code,
					CONCAT_WS(' - ', a.code, a.generic) AS antiemetic_desc,
					CASE WHEN a.class = '5-HT3' THEN CONCAT_WS(' - ', a.code, a.generic) END AS ht3_desc,
					CASE WHEN a.class = 'CORT' THEN CONCAT_WS(' - ', a.code, a.generic) END AS cort_desc,
					CASE WHEN a.class = 'DOP' THEN CONCAT_WS(' - ', a.code, a.generic) END AS dop_desc,
					CASE WHEN a.class = 'NK1' THEN CONCAT_WS(' - ', a.code, a.generic) END AS nk1_desc,
					CASE WHEN a.class = 'OLZ' THEN CONCAT_WS(' - ', a.code, a.generic) END AS olz_desc,
					cp.claimprescriptionfilleddate AS antiemetic_date,
					a.class AS antiemetic_class,
					ep.perf_period_key
				FROM qm2_emetics_details AS e
					INNER JOIN dev_dtx_gc.IC1.CLAIMPHARMACY AS cp
						ON e.memberid = cp.memberid
							AND e.emetic_date <= cp.claimprescriptionfilleddate
					INNER JOIN dev_dtx_gc.staging.stg_episodes AS ep
						ON ep.memberid = cp.memberid
							AND ep.episode_start_date <= cp.claimprescriptionfilleddate
							AND ep.episode_end_date >= cp.claimprescriptionfilleddate
					INNER JOIN dev_dtx_gc.staging.stg_seed_antiemetics AS a
						ON a.code = LEFT(cp.claimpharmacygenericproductidentifier, 8)
							AND a.code_type = 'GPI_8_DIGITS'
			) AS ae
			ON e.memberid = ae.memberid
				AND e.perf_period_key = ae.perf_period_key
	QUALIFY ROW_NUMBER() OVER (
			PARTITION BY e.memberid, e.perf_period_key, ae.antiemetic_class
			ORDER BY ae.antiemetic_date ASC
		) = 1
),

summarized_emetic_claims AS (          --- IC-16505: Summerizing Emetic and AntiEmetic records on patient level
	SELECT
		memberid,
		perf_period_key,
		LISTAGG(DISTINCT emetic_desc, ', ') WITHIN GROUP (
			ORDER BY emetic_desc
		) AS chemocode,  -- IC-16356 Emetics as chemocodes  and AntiEmetics as Drugs
		LISTAGG(DISTINCT consolidated_emetic_desc, ', ') WITHIN GROUP (
			ORDER BY consolidated_emetic_desc
		) AS consolidated_emetic_desc,
		LISTAGG(DISTINCT emetic_date, ', ') WITHIN GROUP (
			ORDER BY emetic_date
		) AS chemodate,
		LISTAGG(DISTINCT antiemetic_desc, ', ') WITHIN GROUP (
			ORDER BY antiemetic_desc
		) AS drugsadministered,
		LISTAGG(DISTINCT antiemetic_date, ', ') WITHIN GROUP (
			ORDER BY antiemetic_date
		) AS drugsadministereddates,
		MAX(ht3_desc) AS ht3_desc,
		MAX(cort_desc) AS cort_desc,
		MAX(dop_desc) AS dop_desc,
		MAX(nk1_desc) AS nk1_desc,
		MAX(olz_desc) AS olz_desc,
		SUM(CASE WHEN antiemetic_class = '5-HT3' THEN 1 ELSE 0 END) AS hte_count,
		SUM(CASE WHEN antiemetic_class = 'CORT' THEN 1 ELSE 0 END) AS cort_count,
		SUM(CASE WHEN antiemetic_class = 'DOP' THEN 1 ELSE 0 END) AS dop_count,
		SUM(CASE WHEN antiemetic_class = 'NK1' THEN 1 ELSE 0 END) AS nk1_count,
		SUM(CASE WHEN antiemetic_class = 'OLZ' THEN 1 ELSE 0 END) AS olz_count,
		SUM(CASE WHEN antiemetic_class IS NOT NULL THEN 1 ELSE 0 END) AS antiemetic_count,
		MAX(emetic_risk_number) AS max_emetic_risk
	FROM qm2_eme_antieme_details
	GROUP BY memberid, perf_period_key
),

memberwithemeticrisk AS (
	SELECT
		ec.memberid,
		ec.perf_period_key,
		CASE WHEN ec.nk1_count = 0 THEN 1 ELSE 0 END AS low_risk_numerator, /*JIRA:IC-16504 | Antiemitics of class NK1 should not be there in the claim to qualify for low risk numerator*/
		CASE WHEN ec.nk1_count = 0 AND (LEAST(ec.hte_count, 1) + LEAST(ec.cort_count, 1) + LEAST(ec.dop_count, 1)) >= 1 THEN 1 ELSE 0 END AS moderate1_risk_numerator,
		/*JIRA:IC-14187 | Antiemitics of class NK1 should not be there, at least one of the three antiemitics (5-HT3, CORT, DOP) should be there in the claim to qualify for moderate risk numerator without carboplatin*/
		CASE WHEN LEAST(ec.nk1_count, 1) + LEAST(ec.hte_count, 1) + LEAST(ec.cort_count, 1) + LEAST(ec.dop_count, 1) + LEAST(ec.olz_count, 1) >= 2
				THEN 1
			ELSE 0
		END AS moderate2_risk_numerator, /*JIRA:IC-14187 | At least two of the five antiemitics (NK1, 5-HT3, CORT, DOP, OLZ) should be there in the claim to qualify for moderate risk numerator without carboplatin*/
		CASE WHEN ec.nk1_count <> 0 AND ec.hte_count <> 0 AND ec.cort_count <> 0 THEN 1 ELSE 0 END AS high_risk_numerator,/*All the three antiemetics (NK1, 5-HT3, CORT) should be there in a claim to qualify for high risk numerator.*/
		NULLIF(chemocode, '') AS chemocode,
		ec.consolidated_emetic_desc,
		NULLIF(chemodate, '') AS chemodate,
		NULLIF(drugsadministered, '') AS drugsadministered,
		NULLIF(drugsadministereddates, '') AS drugsadministereddates,
		ec.nk1_count,
		ec.hte_count,
		ec.cort_count,
		ec.dop_count,
		ec.olz_count,
		ec.max_emetic_risk, /*JIRA:IC-14187 | emetic risk would decide whether a member would qualify for low/moderate/high risk denominator*/
		ec.ht3_desc,
		ec.cort_desc,
		ec.dop_desc,
		ec.nk1_desc,
		ec.olz_desc
	FROM summarized_emetic_claims AS ec
),

qm2_data_episode_mapping AS (
	SELECT
		e.memberid,
		ep.participatingprovidernpi,
		ep.tin,
		ep.principalcancercode,
		ep.cancerdiagnosisgroupcode,
		ep.lineofbusiness,
		ep.perf_period_key,
		cm.month_first_date,
		ep.episode_start_date,
		ep.episode_end_date
	FROM memberwithemeticrisk AS e
		INNER JOIN dev_dtx_gc.staging.stg_episodes AS ep
			ON e.memberid = ep.memberid
				AND e.chemodate >= ep.episode_start_date
				AND e.chemodate <= ep.episode_end_date
		INNER JOIN calendar_months AS cm
			ON cm.month_first_date = DATE_TRUNC(MONTH, TO_DATE(e.chemodate))
	QUALIFY ROW_NUMBER() OVER (
			PARTITION BY e.memberid, ep.perf_period_key
			ORDER BY
				ABS(TO_DATE(e.chemodate) - cm.month_first_date) ASC, --to pick the closest attribution data to chemo
				cm.month_first_date DESC
		) = 1-- if incase chemo happened exactly between to attribution date, pick the latest (highly unlikely but got to cover) 
)

SELECT
	m.memberid,
	1 AS denominator, /*Attributed members with Emetic risk would qualify for denominator*/
	COALESCE(m.low_risk_numerator, 1) AS low_risk_numerator,
	COALESCE(m.moderate1_risk_numerator, 0) AS moderate1_risk_numerator,
	COALESCE(m.moderate2_risk_numerator, 0) AS moderate2_risk_numerator,
	COALESCE(m.high_risk_numerator, 0) AS high_risk_numerator,
	COALESCE(m.nk1_count, 0) AS nk1_count,
	COALESCE(m.hte_count, 0) AS hte_count,
	COALESCE(m.cort_count, 0) AS cort_count,
	COALESCE(m.dop_count, 0) AS dop_count,
	COALESCE(m.olz_count, 0) AS olz_count,
	COALESCE(ht3_desc, 'No 5-HT3 Drugs found') AS ht3_desc,
	COALESCE(cort_desc, 'No CORT Drugs found') AS cort_desc,
	COALESCE(dop_desc, 'No DOP Drugs found') AS dop_desc,
	COALESCE(nk1_desc, 'No NK1 Drugs found') AS nk1_desc,
	COALESCE(olz_desc, 'No OLANZAPINE Drugs found') AS olz_desc,
	COALESCE(m.max_emetic_risk, 1) AS max_emetic_risk,
	COALESCE(m.chemocode, 'No Emetic Drugs found') AS chemocode,
	m.consolidated_emetic_desc,
	m.chemodate,
	COALESCE(m.drugsadministered, 'No Anti-emetic Drugs found') AS drugsadministered,
	m.drugsadministereddates,
	em.participatingprovidernpi,
	em.perf_period_key,
	em.episode_start_date,
	em.episode_end_date,
	em.month_first_date AS contextdate,
	em.tin,
	em.principalcancercode,
	em.cancerdiagnosisgroupcode,
	em.lineofbusiness
FROM memberwithemeticrisk AS m
	INNER JOIN qm2_data_episode_mapping AS em
		ON m.memberid = em.memberid AND m.perf_period_key = em.perf_period_key