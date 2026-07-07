# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: GPL-3.0-or-later
import io
import json
import os
import tarfile

from openpyxl import Workbook

from lumi_batcher_service.common.output_naming import (
    build_output_file_name,
    next_available_filename,
)


def read_packaged_filenames(archive_path: str) -> list[str] | None:
    """
    如果压缩包已存在，直接读取包内的真实文件名（已经过实际的截断/去重处理），
    避免脱离打包流程重新计算截断结果时产生的偏差。
    读取失败或压缩包不存在时返回 None，调用方需回退到重新计算的文件名。
    """
    if not archive_path or not os.path.isfile(archive_path):
        return None
    try:
        with tarfile.open(archive_path) as archive:
            return [
                os.path.basename(member.name)
                for member in archive.getmembers()
                if member.isfile()
            ]
    except Exception:
        return None


def flatten_params_config(params_config: list[dict]) -> dict:
    """
    将参数配置展开为 {参数名称: 参数值} 的映射
    """
    flat = {}
    for config in params_config:
        t = config.get("type", "")
        if t == "group":
            for v in config.get("values", []):
                name = v.get("name") or v.get("internal_name") or ""
                if name:
                    flat[name] = v.get("value", "")
        else:
            name = config.get("name") or config.get("internal_name") or ""
            if name:
                flat[name] = config.get("value", "")
    return flat


def build_params_sheet_rows(
    results: list[dict], dir: str, archive_path: str = ""
) -> list[dict]:
    """
    独立于打包流程，直接基于任务结果生成 文件名 -> 完整参数 的查找表数据。
    不依赖打包结果是否存在，也不会写入/复制任何文件。

    文件名推导复用与打包下载时完全相同的两个函数
    (build_output_file_name / next_available_filename)，避免两处实现漂移。

    如果压缩包已经打包完成 (archive_path 存在)，会改用包内的真实文件名
    覆盖计算结果，因为真实打包时是基于当时的临时目录长度截断的，事后无法
    100% 精确重现；条目数一致时用包内真实文件名，能保证与压缩包完全一致。
    """
    rows = []
    name_count_cache: dict = {}

    for item in results:
        params_config = json.loads(item.get("ParamsConfig", "[]"))
        output_file_name = build_output_file_name(params_config, dir)
        flat_params = flatten_params_config(params_config)

        for output in item.get("list", []):
            value_type = output.get("type")
            value = output.get("value")

            if value_type in ("image", "video", "audio"):
                _, file_extension = os.path.splitext(str(value or ""))
            elif value_type == "text":
                file_extension = ".txt"
            else:
                continue

            filename = next_available_filename(
                name_count_cache, output_file_name, file_extension
            )

            rows.append({"filename": filename, **flat_params})

    packaged_filenames = read_packaged_filenames(archive_path)
    if packaged_filenames and len(packaged_filenames) == len(rows):
        for row, real_filename in zip(rows, packaged_filenames):
            row["filename"] = real_filename

    return rows


def rows_to_xlsx_bytes(rows: list[dict]) -> bytes:
    """
    将行数据写成 xlsx 并以字节流返回，不落盘
    """
    columns = ["filename"]
    for row in rows:
        for key in row.keys():
            if key not in columns:
                columns.append(key)

    wb = Workbook()
    ws = wb.active
    ws.append(columns)
    for row in rows:
        ws.append([row.get(col, "") for col in columns])

    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()
