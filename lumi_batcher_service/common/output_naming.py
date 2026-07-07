# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: GPL-3.0-or-later
from lumi_batcher_service.constant.task import Category
from lumi_batcher_service.common.file import file_processor


def build_output_file_name(params_config: list[dict], dir: str) -> str:
    """
    根据参数配置推导输出文件名（不含扩展名）。
    与打包下载时使用的是同一条规则，供两处复用，避免实现漂移。
    """
    config_values: list[str] = []
    for config in params_config:
        if config.get("category", None) != Category.SYSTEM.value:
            t = config.get("type", "")
            if t == "group":
                for v in config.get("values", []):
                    config_values.append(v.get("value", ""))
            else:
                config_values.append(config.get("value", ""))

    output_file_name = "_".join(str(x) for x in config_values)
    return file_processor.sanitize_filename(dir, output_file_name)


def next_available_filename(
    name_count_cache: dict, output_file_name: str, file_extension: str
) -> str:
    """
    对同名文件追加 (n) 后缀去重，与打包下载时使用的是同一条规则。
    """
    key = f"{output_file_name}{file_extension}"
    count = name_count_cache.get(key, 0)

    if count == 0:
        filename = f"{output_file_name}{file_extension}"
    else:
        filename = f"{output_file_name}({count}){file_extension}"

    name_count_cache[key] = count + 1
    return filename
