-- DBT Model: stg_claims_ed_to_ip
-- Database: dev_dtx_gc
-- Schema: staging
-- Alias: stg_claims_ed_to_ip




WITH transedtoip AS (
	SELECT DISTINCT
		cl.claimlineservicestartdate,
		c.memberid
	FROM dev_dtx_gc.IC1.CLAIMLINE AS cl
		INNER JOIN dev_dtx_gc.IC1.CLAIM AS c
			ON cl.claimid = c.claimid
	WHERE cl.claimlinerevenuecode between '0100' AND '0249'
)

SELECT DISTINCT
	c.claimid,
	c.memberid,
	cl.claimlineid
FROM dev_dtx_gc.IC1.CLAIMLINE AS cl
	INNER JOIN dev_dtx_gc.IC1.CLAIM AS c
		ON cl.claimid = c.claimid
	INNER JOIN transedtoip AS edtoip
		ON
			c.memberid = edtoip.memberid
			AND cl.claimlineservicestartdate = edtoip.claimlineservicestartdate
WHERE
	cl.claimlineplaceofservicecode IN (22, 23)
	AND (
		cl.claimlinerevenuecode
		IN (
			'0450',
			'0451',
			'0452',
			'0453',
			'0454',
			'0455',
			'0457',
			'0458',
			'0459'
		)
		OR (
			cl.claimlinerevenuecode = '0456'
			AND cl.claimlinehealthservicecode IN (
				'99281', '99282', '99283', '99284', '99285'
			)
		)
	)