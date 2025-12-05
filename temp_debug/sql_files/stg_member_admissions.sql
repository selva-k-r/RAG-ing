-- DBT Model: stg_member_admissions
-- Database: dev_dtx_gc
-- Schema: staging
-- Alias: stg_member_admissions



WITH member_admission AS(
    SELECT
        c.memberid,
        cl.claimid,
        cl.claimlineid,
        cl.claimlineservicestartdate AS dateofservice,
        cl.claimlineserviceenddate AS dateofserviceend,
        cl.claimlineplaceofservicecode,
        cl.claimlineprincipaldiagnosiscode,
        cl.claimlinerevenuecode,
        cl.claimlinehealthservicecode,
        c.claimtypeofbillcode,
        MAX(CASE 
                WHEN cl.claimlinerevenuecode BETWEEN 100 AND 249 THEN 2
                WHEN cl.claimlineplaceofservicecode IN (22, 23)
                    AND (
                        cl.claimlinerevenuecode IN ('0450', '0451', '0452', '0453', '0454', '0455', '0457', '0458', '0459')
                        OR (cl.claimlinerevenuecode = '0456' AND cl.claimlinehealthservicecode IN ('99281', '99282', '99283', '99284', '99285'))
                    )
                    THEN 1
                    ELSE 0
                END) OVER(PARTITION BY c.claimid) AS max_admission_code,
        CASE max_admission_code
            WHEN 2 THEN 'IP'
            WHEN 1 THEN 'ED'
            ELSE NULL
        END AS admission_type
    FROM dev_dtx_gc.staging.STG_MEMBER AS m
    INNER JOIN dev_dtx_gc.IC1.CLAIM AS c
        ON m.memberid = c.memberid
    INNER JOIN dev_dtx_gc.IC1.CLAIMLINE AS cl
        ON c.claimid = cl.claimid
    WHERE cl.claimlineplaceofservicecode > 0
)
,
distinctipadmissions        -- all Distinct IP records
AS (
    SELECT DISTINCT
        ma.memberid,
        ma.dateofservice
    FROM member_admission AS ma
    WHERE ma.admission_type = 'IP'
)
,
-- Splitting individual records into group admissions based on continuous dates 
ipadmissiongroup AS (
    SELECT
        ipa.memberid,
        ipa.dateofservice,
        DATEDIFF(
            DAY,
            MIN(ipa.dateofservice) OVER (PARTITION BY ipa.memberid),
            ipa.dateofservice
        )
        - (
        ROW_NUMBER() OVER (
            PARTITION BY ipa.memberid
            ORDER BY ipa.dateofservice ASC
            ) - 1
        ) AS admission_group
    FROM distinctipadmissions AS ipa
)
SELECT ma.*,
    ipa.admission_group,
    CASE ma.admission_type
        WHEN 'IP' THEN MIN(ma.dateofservice) OVER(PARTITION BY ma.memberid, ipa.admission_group)
        WHEN 'ED' THEN MIN(ma.dateofservice) OVER(PARTITION BY ma.memberid, ma.claimid)
        ELSE ma.dateofservice
    END AS admission_start_date,
    CASE WHEN ma.admission_type = 'IP' THEN CONCAT(ma.memberid, ipa.admission_group) ELSE NULL END AS ipdateid,
    CASE WHEN ma.admission_type = 'ED' THEN CONCAT(ma.memberid, admission_start_date) ELSE NULL END AS eddateid
FROM member_admission ma
    LEFT OUTER JOIN ipadmissiongroup AS ipa
        ON ma.memberid = ipa.memberid AND ma.dateofservice = ipa.dateofservice and ma.admission_type = 'IP'