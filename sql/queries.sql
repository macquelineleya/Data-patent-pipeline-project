-- ============================================
-- GLOBAL PATENT INTELLIGENCE DATA PIPELINE
-- Required SQL Queries
-- ============================================

-- Q1: Top Inventors
SELECT
    i.inventor_id,
    i.name,
    COUNT(DISTINCT pir.patent_id) AS patent_count
FROM inventors i
JOIN patent_inventor_relationships pir
    ON i.inventor_id = pir.inventor_id
GROUP BY i.inventor_id, i.name
ORDER BY patent_count DESC
LIMIT 10;

-- Q2: Top Companies
SELECT
    c.company_id,
    c.name,
    COUNT(DISTINCT pcr.patent_id) AS patent_count
FROM companies c
JOIN patent_company_relationships pcr
    ON c.company_id = pcr.company_id
GROUP BY c.company_id, c.name
ORDER BY patent_count DESC
LIMIT 10;

-- Q3: Countries
SELECT
    l.country,
    COUNT(DISTINCT pir.patent_id) AS patent_count
FROM patent_inventor_relationships pir
JOIN locations l
    ON pir.location_id = l.location_id
WHERE l.country IS NOT NULL
GROUP BY l.country
ORDER BY patent_count DESC
LIMIT 10;

-- Q4: Trends Over Time
SELECT
    year,
    COUNT(*) AS patent_count
FROM patents
WHERE year IS NOT NULL
GROUP BY year
ORDER BY year;

-- Q5: JOIN Query
SELECT
    p.patent_id,
    p.title,
    p.year,
    i.name AS inventor_name,
    c.name AS company_name
FROM patents p
LEFT JOIN patent_inventor_relationships pir
    ON p.patent_id = pir.patent_id
LEFT JOIN inventors i
    ON pir.inventor_id = i.inventor_id
LEFT JOIN patent_company_relationships pcr
    ON p.patent_id = pcr.patent_id
LEFT JOIN companies c
    ON pcr.company_id = c.company_id
LIMIT 20;

-- Q6: CTE Query
WITH inventor_patent_counts AS (
    SELECT
        i.inventor_id,
        i.name,
        COUNT(DISTINCT pir.patent_id) AS patent_count
    FROM inventors i
    JOIN patent_inventor_relationships pir
        ON i.inventor_id = pir.inventor_id
    GROUP BY i.inventor_id, i.name
)
SELECT *
FROM inventor_patent_counts
ORDER BY patent_count DESC
LIMIT 10;

-- Q7: Ranking Query
SELECT
    inventor_id,
    name,
    patent_count,
    RANK() OVER (ORDER BY patent_count DESC) AS inventor_rank
FROM (
    SELECT
        i.inventor_id,
        i.name,
        COUNT(DISTINCT pir.patent_id) AS patent_count
    FROM inventors i
    JOIN patent_inventor_relationships pir
        ON i.inventor_id = pir.inventor_id
    GROUP BY i.inventor_id, i.name
) ranked_inventors
ORDER BY inventor_rank
LIMIT 10;