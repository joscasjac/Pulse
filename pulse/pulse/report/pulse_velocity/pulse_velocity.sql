SELECT
    s.name AS "Sprint",
    s.start_date AS "Start Date",
    s.end_date AS "End Date",
    s.planned_points AS "Planned Points",
    s.completed_points AS "Completed Points",
    s.completed_points AS "Velocity",
    ROUND(100 * s.completed_points / NULLIF(s.planned_points, 0), 1) AS "Attainment %%"
FROM `tabPulse Sprint` s
WHERE s.status = 'Completed'
  AND (%(project)s IS NULL OR %(project)s = '' OR s.project = %(project)s)
ORDER BY s.end_date DESC
LIMIT %(last_n_sprints)s
