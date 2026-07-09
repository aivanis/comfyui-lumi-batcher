SELECT
    status,
    COUNT(*)
FROM
    batch_sub_task
WHERE
    batch_task_id = ?
GROUP BY
    status
