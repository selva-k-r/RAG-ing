-- DBT Model: stg_seed_quality_measures
-- Database: dev_dtx_gc
-- Schema: staging
-- Alias: stg_seed_quality_measures



SELECT
	qmid,
	qmname,
	decsription,
	targetscore,
	measureid,
	custommeasureid,
	-- Demo Report process 
	
		measurename,
	
	-- Demo Report process 
	group1score,
	group2score,
	group3score,
	group4score,
	group5score,
	qmsort,
	quintile_1,
	quintile_2,
	quintile_3,
	quintile_4,
	quintile_5,
	quintile_1_ma,
	quintile_2_ma,
	quintile_3_ma,
	quintile_4_ma,
	quintile_5_ma,
	qmweight,
	qmhoverdesc,
	qmshortdesc
FROM dev_dtx_gc.anthemreporting_seed.seed_quality_measures