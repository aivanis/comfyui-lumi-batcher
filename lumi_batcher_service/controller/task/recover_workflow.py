# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: GPL-3.0-or-later
import json
import os

from lumi_batcher_service.common.file import get_file_absolute_path
from lumi_batcher_service.dao.batch_sub_task import SubTaskStatus


def recover_workflow_from_results(sub_task_rows, output_directory) -> dict | None:
    """
    从已成功子任务的PNG结果中恢复内嵌的workflow
    （创建任务时通过extra_pnginfo写入，重试时无法从数据库获取原始workflow）
    """
    from PIL import Image

    for row in sub_task_rows or []:
        if row.get("status") != SubTaskStatus.SUCCESS.value:
            continue

        try:
            output_items = json.loads(row.get("output") or "[]")
        except Exception:
            continue

        for item in output_items:
            for value_item in item.get("values", []):
                if value_item.get("type") != "image":
                    continue

                value = value_item.get("value", "")
                if not value.lower().endswith(".png"):
                    continue

                file_path = os.path.join(output_directory, value)
                if not os.path.isfile(file_path):
                    new_file_path = get_file_absolute_path(file_path)
                    if os.path.isfile(new_file_path):
                        file_path = new_file_path
                    else:
                        continue

                try:
                    with Image.open(file_path) as img:
                        workflow_str = img.info.get("workflow")
                    if workflow_str:
                        return json.loads(workflow_str)
                except Exception:
                    continue

    return None
