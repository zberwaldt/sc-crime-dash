COUNTY_GEO_SQL = 'SELECT county_name, geometry FROM sc_counties'

TOP_OFFENSES_SQL = """
SELECT c.county_name, l.offense_type AS category, COUNT(DISTINCT l.incident_id) AS incidents
FROM target_data l
JOIN sc_county_law_info c ON c.fips = l.fips
WHERE c.county_name = :county
GROUP BY c.county_name, l.offense_type
ORDER BY incidents DESC
LIMIT :top
"""

TOP_LOCATIONS_SQL = """
SELECT c.county_name, l.location AS category, COUNT(DISTINCT l.incident_id) AS incidents
FROM target_data l
JOIN sc_county_law_info c ON c.fips = l.fips
WHERE c.county_name = :county
GROUP BY c.county_name, l.location
ORDER BY incidents DESC
LIMIT :top
"""
