select * from claims_data;
select * from providers_data;
select * from receivers_data;
select * from food_listings_data;

SELECT *FROM providers_data
WHERE city IS NULL;

SELECT *
FROM receivers_data
WHERE city IS NULL;

SELECT provider_id,
COUNT(*)
FROM providers_data
GROUP BY provider_id
HAVING COUNT(*) > 1;

-- QUERY-1
-- How many providers in each city?
SELECT city,
COUNT(*) AS providers
FROM providers_data
GROUP BY city;
-- QUERY-2
-- How many receivers in each city?
SELECT city,
COUNT(*) AS receivers
FROM receivers_data
GROUP BY city;

-- QUERY-3
-- Provider type contributes most food?
SELECT provider_type,
SUM(quantity) AS total_food
FROM food_listings_data
GROUP BY provider_type
ORDER BY total_food DESC;

-- QUERY -4
-- Providers in a specific city?
SELECT name,contact FROM providers_data
WHERE city='Richardfort';

-- QUERY-5
-- Receivers who claimed most food?
SELECT r.name,
COUNT(c.claim_id) claims
FROM receivers_data r
JOIN claims_data c
ON r.receiver_id=c.receiver_id
GROUP BY r.name
ORDER BY claims DESC;

-- QUERY-6
-- Total food available?
SELECT SUM(quantity) total_food
FROM food_listings_data;

-- QUERY-7
-- City with highest food listing?
SELECT location,
COUNT(*) listings
FROM food_listings_data
GROUP BY location
ORDER BY listings DESC;

-- QUERY-8
-- Most common food type?
SELECT food_type,
COUNT(*) total
FROM food_listings_data
GROUP BY food_type
ORDER BY total DESC;

-- QUERY-9
-- Food claims for each item?
SELECT f.food_name,
COUNT(c.claim_id)
FROM food_listings_data f
JOIN claims_data c
ON f.food_id=c.food_id
GROUP BY f.food_name;

-- QUERY-10
-- Provider with highest successful claims?
SELECT p.name,
COUNT(*) successful_claims
FROM providers_data p
JOIN food_listings_data f
ON p.provider_id=f.provider_id
JOIN claims_data c
ON f.food_id=c.food_id
WHERE status='Completed'
GROUP BY p.name
ORDER BY successful_claims DESC;

-- QUERY-11
-- percentage of claim status?
SELECT status,
ROUND(
COUNT(*)*100.0/
(SELECT COUNT(*) FROM claims_data),2) percentage
FROM claims_data
GROUP BY status;

-- QUERY-12
-- Average quantity claimed per receiver?
SELECT r.name,
AVG(f.quantity)
FROM receivers_data r
JOIN claims_data c
ON r.receiver_id=c.receiver_id
JOIN food_listings_data f
ON c.food_id=f.food_id
GROUP BY r.name;

-- QUERY-13
-- Most claimed meal type?
SELECT meal_type,
COUNT(*) claims
FROM food_listings_data f
JOIN claims_data c
ON f.food_id=c.food_id
GROUP BY meal_type
ORDER BY claims DESC;

-- QUERY-14
-- Food donated by each provider?
SELECT p.name,
SUM(f.quantity) total_donated
FROM providers_data p
JOIN food_listings_data f
ON p.provider_id=f.provider_id
GROUP BY p.name;

-- QUERY-15
-- Top 5 cities by food availability?
SELECT location,
SUM(quantity)
FROM food_listings_data
GROUP BY location
ORDER BY SUM(quantity) 
LIMIT 5