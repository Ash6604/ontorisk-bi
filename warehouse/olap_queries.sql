-- OntoRisk BI - example OLAP queries over the DuckDB star schema
-- Run with the DuckDB CLI:   duckdb warehouse/ontorisk.duckdb < warehouse/olap_queries.sql
-- or from Python:            duckdb.connect("warehouse/ontorisk.duckdb").sql(open(...).read())

-- 1. ROLL-UP: events and average impact by region -> risk type, with subtotals
SELECT region, risk_type, COUNT(*) AS events, ROUND(AVG(impact_score), 2) AS avg_impact
FROM V_RISK_EVENTS
GROUP BY ROLLUP (region, risk_type)
ORDER BY region NULLS LAST, events DESC;

-- 2. DRILL-DOWN: one region down to state and place
SELECT state, place, COUNT(*) AS events, ROUND(SUM(impact_score), 1) AS total_impact
FROM V_RISK_EVENTS
WHERE region = 'West'
GROUP BY state, place
ORDER BY events DESC;

-- 3. CUBE over time: every combination of year x quarter (incl. totals)
SELECT year, quarter, COUNT(*) AS events
FROM V_RISK_EVENTS
GROUP BY CUBE (year, quarter)
ORDER BY year NULLS LAST, quarter NULLS LAST;

-- 4. SLICE + DICE: High-severity weather events in the monsoon months, by state
SELECT state, month_name, COUNT(*) AS events
FROM V_RISK_EVENTS
WHERE risk_type = 'weather' AND severity = 'High' AND month BETWEEN 6 AND 9
GROUP BY state, month, month_name
ORDER BY month, events DESC;

-- 5. Risk Exposure Index (dashboard KPI) by sector
SELECT sector,
       ROUND(SUM(impact_score * CASE severity WHEN 'High' THEN 3 WHEN 'Medium' THEN 2 ELSE 1 END), 1) AS risk_exposure_index
FROM V_RISK_EVENTS
GROUP BY sector
ORDER BY risk_exposure_index DESC;

-- 6. HYBRID: from a fact row to its RDF triples through the semantic bridge
SELECT f.event_id, f.entity_name, b.subject, b.predicate, b.object
FROM FACT_RISKEVENT f
JOIN BRIDGE_SEMANTIC_LINK b USING (event_id)
WHERE f.severity = 'High'
ORDER BY f.impact_score DESC
LIMIT 10;
