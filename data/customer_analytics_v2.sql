-- Customer Analytics Query - Version 2.0
-- Date: 2024-10-01
-- Status: Current Production Implementation
-- Performance: Optimized for datasets exceeding 1M records
-- Features: Window functions, CTEs, partitioning support

-- Enhanced customer analytics with CTE and window functions
WITH recent_orders AS (
    SELECT
        o.order_id,
        o.customer_id,
        o.total_amount,
        o.order_date,
        c.name AS customer_name,
        c.registration_date,
        ROW_NUMBER() OVER (PARTITION BY o.customer_id ORDER BY o.order_date DESC) as order_rank
    FROM orders AS o
    JOIN customers AS c ON c.customer_id = o.customer_id
    WHERE o.order_date >= DATE_SUB(CURDATE(), INTERVAL 12 MONTH)
),
customer_metrics AS (
    SELECT
        customer_id,
        customer_name,
        registration_date,
        COUNT(*) AS order_count,
        AVG(total_amount) AS avg_order_value,
        SUM(total_amount) AS total_spend,
        MAX(order_date) AS last_order_date,
        MIN(order_date) AS first_order_date,
        DATEDIFF(MAX(order_date), MIN(order_date)) AS customer_lifetime_days
    FROM recent_orders
    GROUP BY customer_id, customer_name, registration_date
),
customer_segments AS (
    SELECT 
        *,
        CASE 
            WHEN total_spend >= 10000 THEN 'Premium'
            WHEN total_spend >= 5000 THEN 'Gold'
            WHEN total_spend >= 1000 THEN 'Silver'
            ELSE 'Bronze'
        END as spending_tier,
        CASE 
            WHEN customer_lifetime_days <= 30 THEN 'New'
            WHEN customer_lifetime_days <= 365 THEN 'Regular'
            ELSE 'Loyal'
        END as loyalty_tier
    FROM customer_metrics
)
SELECT 
    customer_id,
    customer_name,
    order_count,
    ROUND(avg_order_value, 2) as avg_order_value,
    ROUND(total_spend, 2) as total_spend,
    spending_tier,
    loyalty_tier,
    last_order_date,
    customer_lifetime_days
FROM customer_segments
ORDER BY total_spend DESC, order_count DESC;

-- Advanced temporal analysis with window functions
WITH monthly_trends AS (
    SELECT 
        DATE_FORMAT(order_date, '%Y-%m') as order_month,
        COUNT(*) as monthly_orders,
        SUM(total_amount) as monthly_revenue,
        COUNT(DISTINCT customer_id) as active_customers
    FROM orders 
    WHERE order_date >= DATE_SUB(CURDATE(), INTERVAL 24 MONTH)
    GROUP BY DATE_FORMAT(order_date, '%Y-%m')
)
SELECT 
    order_month,
    monthly_orders,
    ROUND(monthly_revenue, 2) as monthly_revenue,
    active_customers,
    ROUND(monthly_revenue / monthly_orders, 2) as avg_order_value,
    ROUND(LAG(monthly_revenue) OVER (ORDER BY order_month), 2) as prev_month_revenue,
    ROUND(
        ((monthly_revenue - LAG(monthly_revenue) OVER (ORDER BY order_month)) / 
         LAG(monthly_revenue) OVER (ORDER BY order_month)) * 100, 2
    ) as revenue_growth_pct
FROM monthly_trends
ORDER BY order_month;

-- Customer cohort analysis
WITH customer_cohorts AS (
    SELECT 
        customer_id,
        DATE_FORMAT(MIN(order_date), '%Y-%m') as cohort_month,
        DATEDIFF(order_date, MIN(order_date) OVER (PARTITION BY customer_id)) as period_number
    FROM orders
    WHERE order_date >= '2023-01-01'
    GROUP BY customer_id, order_date
),
cohort_data AS (
    SELECT 
        cohort_month,
        period_number,
        COUNT(DISTINCT customer_id) as customers
    FROM customer_cohorts
    GROUP BY cohort_month, period_number
),
cohort_sizes AS (
    SELECT 
        cohort_month,
        customers as cohort_size
    FROM cohort_data
    WHERE period_number = 0
)
SELECT 
    cd.cohort_month,
    cs.cohort_size,
    cd.period_number,
    cd.customers,
    ROUND((cd.customers * 100.0 / cs.cohort_size), 2) as retention_rate
FROM cohort_data cd
JOIN cohort_sizes cs ON cd.cohort_month = cs.cohort_month
WHERE cd.period_number <= 12
ORDER BY cd.cohort_month, cd.period_number;

-- Production optimizations and table structure
/*
-- Partitioned orders table for improved performance
CREATE TABLE orders_partitioned (
    order_id BIGINT NOT NULL,
    customer_id BIGINT NOT NULL,
    total_amount DECIMAL(12,2) NOT NULL,
    order_date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_customer_date (customer_id, order_date),
    INDEX idx_date_amount (order_date, total_amount),
    PRIMARY KEY (order_id, order_date)
) PARTITION BY RANGE COLUMNS (order_date) (
    PARTITION p202301 VALUES LESS THAN ('2023-02-01'),
    PARTITION p202302 VALUES LESS THAN ('2023-03-01'),
    PARTITION p202303 VALUES LESS THAN ('2023-04-01'),
    PARTITION p202304 VALUES LESS THAN ('2023-05-01'),
    PARTITION p202305 VALUES LESS THAN ('2023-06-01'),
    PARTITION p202306 VALUES LESS THAN ('2023-07-01'),
    PARTITION p202307 VALUES LESS THAN ('2023-08-01'),
    PARTITION p202308 VALUES LESS THAN ('2023-09-01'),
    PARTITION p202309 VALUES LESS THAN ('2023-10-01'),
    PARTITION p202310 VALUES LESS THAN ('2023-11-01'),
    PARTITION p202311 VALUES LESS THAN ('2023-12-01'),
    PARTITION p202312 VALUES LESS THAN ('2024-01-01'),
    PARTITION p202401 VALUES LESS THAN ('2024-02-01'),
    PARTITION p202402 VALUES LESS THAN ('2024-03-01'),
    PARTITION p202403 VALUES LESS THAN ('2024-04-01'),
    PARTITION p202404 VALUES LESS THAN ('2024-05-01'),
    PARTITION p202405 VALUES LESS THAN ('2024-06-01'),
    PARTITION p202406 VALUES LESS THAN ('2024-07-01'),
    PARTITION p202407 VALUES LESS THAN ('2024-08-01'),
    PARTITION p202408 VALUES LESS THAN ('2024-09-01'),
    PARTITION p202409 VALUES LESS THAN ('2024-10-01'),
    PARTITION p202410 VALUES LESS THAN ('2024-11-01'),
    PARTITION p202411 VALUES LESS THAN ('2024-12-01'),
    PARTITION p202412 VALUES LESS THAN ('2025-01-01'),
    PARTITION p_future VALUES LESS THAN MAXVALUE
);

-- Covering indexes for optimal query performance
CREATE INDEX idx_covering_customer_analytics 
ON orders (customer_id, order_date, total_amount, order_id);

CREATE INDEX idx_covering_temporal_analysis 
ON orders (order_date, customer_id, total_amount);

-- Customer table optimizations
CREATE INDEX idx_customers_registration_name 
ON customers (registration_date, name, customer_id);
*/