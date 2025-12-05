-- DBT Model: stg_recon
-- Database: dev_dtx_gc
-- Schema: staging
-- Alias: stg_recon



WITH recon_source AS (

	SELECT *
	FROM dev_dtx_gc.staging.stg_ic1_recon_source

),

recon_population AS (
	-- This CTE will get the memberid from recon and the mapped TIN from the Seed file    
	SELECT
		mt.memberid,
		mt.attributedprovidertaxid,
		mt.performanceperiodstartdate,
		mt.performanceperiodenddate,
		mt.participatingprovidernpinumber,
		mb.membername AS patientname,
		mb.memberbirthdate AS patientbirthdate,
		mb.memberrace AS patientracetext,
		mb.subscriberid,
		pp.perf_period_key,
		mt.episodename AS cancer_type,
		CASE
			WHEN mb.memberbirthdate < CURRENT_DATE()
				THEN FLOOR(
						(
							DATEDIFF(MONTH, mb.memberbirthdate, CURRENT_DATE())
							-
							TO_NUMERIC(
								DATE_PART(DAY, CURRENT_DATE())
								< DATE_PART(DAY, mb.memberbirthdate)
							)
						) / 12
					)
		END AS patientagevalue,
		CASE
			WHEN mb.membergendercode = 'M' THEN 'MALE'
			WHEN mb.membergendercode = 'F' THEN 'FEMALE'
			ELSE 'UNKNOWN'
		END AS patientgendertext,
		COALESCE(c.icd10code, 'N/A') AS cancerdiagnosisgroupcode
	FROM recon_source AS mt
		INNER JOIN dev_dtx_gc.staging.STG_MEMBER AS mb
			ON mt.memberid = mb.memberid
		LEFT JOIN dev_dtx_gc.staging.stg_seed_ocm_cancer_types AS c
			-- all by two cancertypes match
			ON mt.episodename = REPLACE(c.cancer_type, ',', '')
		INNER JOIN dev_dtx_gc.staging.stg_seed_performance_period AS pp
			ON
				mt.performanceperiodstartdate BETWEEN pp.perf_period_start_date AND pp.perf_period_end_date

	QUALIFY
		ROW_NUMBER() OVER (
			PARTITION BY mt.memberid, mt.performanceperiodstartdate
			ORDER BY c.icd10code
		) = 1

),

attributedprovider AS (
	SELECT
		r.memberid,
		r.attributedprovidertaxid,
		a.attributednpiproviderid AS participatingprovidernpinumber
	FROM recon_population AS r
		LEFT JOIN dev_dtx_gc.IC1.ATTRIBUTION AS a
			ON r.memberid = a.memberid

	QUALIFY ROW_NUMBER() OVER (
			PARTITION BY r.memberid, r.attributedprovidertaxid
			ORDER BY
				IFF(r.attributedprovidertaxid = a.attributedprovidertaxid, 1, 2),
				a.attributednpiproviderid
		) = 1

),

recon_population_with_provider AS (
	SELECT
		r.memberid,
		r.attributedprovidertaxid,
		r.performanceperiodstartdate,
		r.performanceperiodenddate,
		a.participatingprovidernpinumber,
		r.patientname,
		r.patientbirthdate,
		r.patientagevalue,
		r.patientgendertext,
		r.patientracetext,
		r.subscriberid,
		r.perf_period_key,
		r.cancer_type,
		r.cancerdiagnosisgroupcode
	FROM recon_population AS r
		LEFT JOIN attributedprovider AS a
			ON
				r.memberid = a.memberid
				AND r.attributedprovidertaxid = a.attributedprovidertaxid
)

SELECT
	p.memberid,
	a.perf_period_key,
	a.subscriberid,
	p.filerunid,
	p.contractid,
	p.lineofbusinessidentifier AS lob,
	p.administrativetaxidnumber,
	p.contractstatecode,
	p.performanceperiodstartdate,
	p.performanceperiodenddate,
	p.contractperiodstartdate,
	p.contractperiodenddate,
	p.programid,
	p.providergroupingidentifier,
	p.contractname,
	p.episodecount,
	p.budgetamount,
	p.trenddescription,
	p.noveladjustmentdescription,
	p.benchmarkpriceamount,
	p.administrativediscountpercent,
	p.targetpriceamount,
	p.totalallowedactualcostamount,
	p.episodeactualtotargetdifferenceamount,
	p.sharedsavingspercent,
	p.savingspoolamount,
	p.sharedsavingsmultipliervalue,
	p.sharedsavingsexpenseamount,
	p.episodeid,
	a.participatingprovidernpinumber,
	a.attributedprovidertaxid,
	--participatingprovidername from Dim_Participating_Provider
	a.patientname,
	a.patientbirthdate,
	a.patientagevalue,
	a.patientgendertext,
	a.patientracetext,
	p.patientstatename,
	a.cancerdiagnosisgroupcode AS cancerdiagnosiscode,
	a.cancer_type AS cancerdiagnosisdescriptiontext,
	p.timeperioddates,
	p.episodename AS cancertype,
	p.qm1code,
	p.qm1performanceratevalue,
	p.qm1numeratorvalue,
	p.qm1denominatorvalue,
	p.qm2code,
	p.qm2performanceratevalue,
	p.qm2numeratorvalue,
	p.qm2denominatorvalue,
	p.qm3code,
	p.qm3performanceratevalue,
	p.qm3numeratorvalue,
	p.qm3denominatorvalue,
	p.qm4code,
	p.qm4performanceratevalue,
	p.qm4numeratorvalue,
	p.qm4denominatorvalue,
	p.qm5code,
	p.qm5pointsvalue,
	p.qm5performanceratevalue,
	p.qm5numeratorvalue,
	p.qm5denominatorvalue,
	p.qm6code,
	p.qm6pointsvalue,
	p.qm6performanceratevalue,
	p.qm6numeratorvalue,
	p.qm6denominatorvalue,
	p.qm7code,
	p.qm7pointsvalue,
	p.qm7performanceratevalue,
	p.qm7numeratorvalue,
	p.qm7denominatorvalue,
	p.qm8code,
	p.qm8pointsvalue,
	p.qm8performanceratevalue,
	p.qm8numeratorvalue,
	p.qm8denominatorvalue,
	p.qm9code,
	p.qm9pointsvalue,
	p.qm9performanceratevalue,
	p.qm9numeratorvalue,
	p.qm9denominatorvalue,
	p.qm10code,
	p.qm10pointsvalue,
	p.qm10performanceratevalue,
	p.qm10numeratorvalue,
	p.qm10denominatorvalue,
	p.qm11code,
	p.qm11pointsvalue,
	p.qm11performanceratevalue,
	p.qm11numeratorvalue,
	p.qm11denominatorvalue,
	p.qmtotalpointsvalue,
	COALESCE(p.qm1pointsvalue, 0) AS qm1pointsvalue,
	COALESCE(p.qm2pointsvalue, 0) AS qm2pointsvalue,
	COALESCE(p.qm3pointsvalue, 0) AS qm3pointsvalue,
	COALESCE(p.qm4pointsvalue, 0) AS qm4pointsvalue,
	COALESCE(p.qmaggregatequalityscorevalue, 0) AS qmaggregatequalityscorevalue,
	hm.ishospicemember,
	map.tin_group_1,
	map.tin_group_2,
	map.tin_group_3,
	CONCAT(p.memberid, '_', a.attributedprovidertaxid)
		AS memberid_attributedtin,
	CONCAT(
		COALESCE(TO_VARCHAR(a.participatingprovidernpinumber), ''),
		'_',
		a.attributedprovidertaxid
	) AS participatingnpi_attributedtin,
	DATE_TRUNC('seconds', SYSDATE()) AS recordinsertiondate_utc,
		p.all_other_medical,
		p.all_other_medical_count,
		p.amb_surg,
		p.amb_surg_count,
		p.attributed_oncologist,
		p.avoid_ed_ane_allowed,
		p.avoid_ed_ane_count,
		p.avoid_ed_deh_allowed,
		p.avoid_ed_deh_count,
		p.avoid_ed_die_allowed,
		p.avoid_ed_die_count,
		p.avoid_ed_eme_allowed,
		p.avoid_ed_eme_count,
		p.avoid_ed_fev_allowed,
		p.avoid_ed_fev_count,
		p.avoid_ed_nau_allowed,
		p.avoid_ed_nau_count,
		p.avoid_ed_neu_allowed,
		p.avoid_ed_neu_count,
		p.avoid_ed_pai_allowed,
		p.avoid_ed_pai_count,
		p.avoid_ed_pne_allowed,
		p.avoid_ed_pne_count,
		p.avoid_ed_sep_allowed,
		p.avoid_ed_sep_count,
		p.avoid_ip_ane_allowed,
		p.avoid_ip_deh_allowed,
		p.avoid_ip_deh_count,
		p.avoid_ip_die_allowed,
		p.avoid_ip_die_count,
		p.avoid_ip_eme_allowed,
		p.avoid_ip_eme_count,
		p.avoid_ip_fev_allowed,
		p.avoid_ip_fev_count,
		p.avoid_ip_nau_allowed,
		p.avoid_ip_nau_count,
		p.avoid_ip_neu_allowed,
		p.avoid_ip_neu_count,
		p.avoid_ip_pai_allowed,
		p.avoid_ip_pai_count,
		p.avoid_ip_pne_allowed,
		p.avoid_ip_pne_count,
		p.avoid_ip_sep_allowed,
		p.avoid_ip_sep_count,
		p.avoidable_admits_allowed,
		p.avoidable_ed_allowed,
		p.avoidable_ed_count,
		p.birth_date,
		p.ccf_paid,
		p.chemo_allowed,
		p.chemo_count,
		p.chemo_drugs_medical,
		p.chemo_drugs_medical_count,
		p.chemotherapy_type,
		p.dod,
		p.ed_allowed,
		p.ed_visits,
		p.emergencyroomtotalvisits,
		p.eol_chemo_allowed,
		p.eol_chemo_count,
		p.eol_ed_allowed,
		p.eol_ed_visits,
		p.eol_icu_allowed,
		p.eol_icu_count,
		p.episode_end_date,
		p.episode_start_date,
		p.er,
		p.er_count,
		p.gender,
		p.home,
		p.inpatient,
		p.home_count,
		p.hospice_allowed,
		p.hospice_claim_admits,
		p.hospice_los,
		p.icu_allowed,
		p.icu_claim_admits,
		p.icu_los,
		p.inpatient__all_other_inpatient,
		p.inpatient__cardiology,
		p.inpatient__detailed_coded_drugs,
		p.inpatient__emergency_room,
		p.inpatient__icu,
		p.inpatient__imaging,
		p.inpatient__lab_pathology,
		p.inpatient__med_surg_supplies,
		p.inpatient__operation,
		p.inpatient__pharmacy,
		p.inpatient__other,
		p.inpatient__radiation_therapy,
		p.inpatient__respiratory_pt_ot_st,
		p.inpatient__room_and_board,
		p.inpatient_count,
		p.inpatient_count__all_other_inpatient,
		p.inpatient_count__cardiology,
		p.inpatient_count__detailed_coded_drugs,
		p.inpatient_count__emergency_room,
		p.inpatient_count__icu,
		p.inpatient_count__imaging,
		p.inpatient_count__lab_pathology,
		p.inpatient_count__med_surg_supplies,
		p.inpatient_count__operation,
		p.inpatient_count__other,
		p.inpatient_count__pharmacy,
		p.inpatient_count__radiation_therapy,
		p.inpatient_count__respiratory_pt_ot_st,
		p.inpatient_count__room_and_board,
		p.avoidable_admits_count,
		p.inpatient_drugs_requiring_coding,
		p.avoid_ip_ane_count,
		p.ip_allowed,
		p.ip_claim_admits,
		p.ip_clusters,
		p.ip_los,
		p.lab,
		p.lab_count,
		p.min_risk_corridor,
		p.novel_allowed,
		p.office,
		p.office__all_other_office,
		p.office__cardiovascular_procedures,
		p.office__drug_admin,
		p.office__e_and_m,
		p.office__radioactive_agents,
		p.office__other,
		p.office__radiology_mammography,
		p.office__pathology_and_lab,
		p.office__psychiatry,
		p.office__radiation_treatment,
		p.office__radiology_diagnostic,
		p.office__radiology_guidance,
		p.office__radiology_nuclear_medicine,
		p.office__radiology_other,
		p.office__radiology_rad_onc_treatment,
		p.office__surgery,
		p.office__therapeutic_activities,
		p.office_count,
		p.office_count__all_other_office,
		p.office_count__cardiovascular_procedures,
		p.office_count__drug_admin,
		p.office_count__e_and_m,
		p.office_count__other,
		p.office_count__pathology_and_lab,
		p.office_count__psychiatry,
		p.office_count__radiation_treatment,
		p.office_count__radioactive_agents,
		p.office_count__radiology_diagnostic,
		p.office_count__radiology_guidance,
		p.office_count__radiology_mammography,
		p.office_count__radiology_nuclear_medicine,
		p.office_count__radiology_other,
		p.office_count__radiology_rad_onc_treatment,
		p.office_count__surgery,
		p.office_count__therapeutic_activities,
		p.operating_room_services_count,
		p.outpatient,
		p.outpatient__all_other_outpatient,
		p.outpatient__chemo_admin,
		p.outpatient__detailed_coded_drugs,
		p.outpatient__gastrointestinal,
		p.outpatient__imaging,
		p.outpatient__iv_therapy,
		p.outpatient__lab_pathology,
		p.outpatient__med_surg_supplies,
		p.outpatient__nuclear_medicine,
		p.outpatient__operation,
		p.outpatient__other,
		p.outpatient__pharmacy,
		p.outpatient__radiation_therapy,
		p.outpatient_count,
		p.outpatient_count__all_other_outpatient,
		p.outpatient_count__chemo_admin,
		p.outpatient_count__detailed_coded_drugs,
		p.outpatient_count__gastrointestinal,
		p.outpatient_count__imaging,
		p.outpatient_count__iv_therapy,
		p.outpatient_count__lab_pathology,
		p.outpatient_count__med_surg_supplies,
		p.outpatient_count__nuclear_medicine,
		p.outpatient_count__operation,
		p.outpatient_count__other,
		p.outpatient_count__pharmacy,
		p.outpatient_count__radiation_therapy,
		p.practice,
		p.prediction,
		p.retail_pharm,
		p.retail_pharm_count,
		p.ssav_expns_amt_no_cap,
		p.telehealth,
		p.telehealth_count,
		p.total_allowed_wind,
		p.totalallowedamtcostall,
		p.transportation,
		p.transportation_count,
		p.uc,
		p.uc_count
FROM recon_source AS p
	INNER JOIN recon_population_with_provider AS a
		ON
			p.memberid = a.memberid
			AND p.performanceperiodstartdate = a.performanceperiodstartdate
	LEFT JOIN
		dev_dtx_gc.staging.stg_member_hospice_mapping AS hm
		ON p.memberid = hm.memberid AND a.perf_period_key = hm.perf_period_key AND p.lineofbusinessidentifier = hm.lineofbusiness
	LEFT JOIN dev_dtx_gc.staging.stg_client_tin_mapping AS map
		ON a.attributedprovidertaxid = map.tin