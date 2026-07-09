UPDATE batch_sub_task
SET
    id = ?,
    prompt_id = ?,
    status = 'pending',
    reason = '',
    output = '[]',
    update_time = ?
WHERE
    id = ?
