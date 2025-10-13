-- Customer Analytics Query - Version 1.0
-- Date: 2024-01-15
-- Status: Production Implementation
-- Performance: Optimized for datasets up to 500K records

-- Main customer analytics query
SELECT c.customer_id, c.name, 
       COUNT(o.order_id) as order_count,
       AVG(o.total_amount) as avg_order_value,
       MAX(o.order_date) as last_order_date
FROM customers c
LEFT JOIN orders o ON c.customer_id = o.customer_id
WHERE o.order_date >= '2023-01-01'
GROUP BY c.customer_id, c.name
ORDER BY order_count DESC;

-- Supporting query: Monthly order trends
SELECT 
    DATE_FORMAT(order_date, '%Y-%m') as order_month,
    COUNT(*) as total_orders,
    SUM(total_amount) as monthly_revenue
FROM orders 
WHERE order_date >= '2023-01-01'
GROUP BY DATE_FORMAT(order_date, '%Y-%m')
ORDER BY order_month;

-- Customer segmentation query
SELECT 
    CASE 
        WHEN order_count >= 10 THEN 'High Value'
        WHEN order_count >= 5 THEN 'Medium Value'
        ELSE 'Low Value'
    END as customer_segment,
    COUNT(*) as customer_count,
    AVG(avg_order_value) as segment_avg_order_value
FROM (
    SELECT c.customer_id,
           COUNT(o.order_id) as order_count,
           AVG(o.total_amount) as avg_order_value
    FROM customers c
    LEFT JOIN orders o ON c.customer_id = o.customer_id
    WHERE o.order_date >= '2023-01-01'
    GROUP BY c.customer_id
) customer_stats
GROUP BY customer_segment
ORDER BY segment_avg_order_value DESC;

-- Index recommendations for v1.0
-- CREATE INDEX idx_orders_customer_date ON orders(customer_id, order_date);
-- CREATE INDEX idx_orders_date ON orders(order_date);
-- CREATE INDEX idx_customers_name ON customers(name);