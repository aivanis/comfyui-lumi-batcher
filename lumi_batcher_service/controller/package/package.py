# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: GPL-3.0-or-later
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os
import shutil
import tempfile
import traceback
import folder_paths
from lumi_batcher_service.handler.batch_tools import BatchToolsHandler
from lumi_batcher_service.controller.output.process import process_output
from lumi_batcher_service.constant.package import PackageStatus
from lumi_batcher_service.common.homeless import get_max_workers
from lumi_batcher_service.common.file import file_processor, get_file_absolute_path
from lumi_batcher_service.common.output_naming import (
    build_output_file_name,
    next_available_filename,
)


async def execute_package_batch_task(
    batchToolsHandler: BatchToolsHandler, batchTaskId: str
):
    """
    执行单个批量任务的打包任务
    """
    try:
        loop = asyncio.get_running_loop()

        file_type = "tar"
        file_path = f"{batchTaskId}"
        output_path = os.path.join(
            batchToolsHandler.workSpaceManager.getDirectory(
                batchToolsHandler.download_path
            ),
            file_path,
        )

        batchToolsHandler.batchTaskDao.update_property(
            batchTaskId,
            "package_info",
            json.dumps(
                {
                    "result": "",
                    "status": PackageStatus.PACKAGING.value,
                    "message": "",
                }
            ),
        )

        async def generateZip():
            with tempfile.TemporaryDirectory() as tmp_dir:
                result = batchToolsHandler.batchSubTaskDao.get_result(batchTaskId)
                results = process_output(result)

                await loop.run_in_executor(None, resolve_results, results, tmp_dir)

                def make_tar_archive():
                    shutil.make_archive(output_path, file_type, tmp_dir)

                # 生成压缩包
                await loop.run_in_executor(None, make_tar_archive)

        task = asyncio.create_task(generateZip())

        await task

        status = PackageStatus.PACKAGING.value

        final_path = f"{batchTaskId}.{file_type}"

        if (
            os.path.exists(
                os.path.join(
                    batchToolsHandler.workSpaceManager.getDirectory(
                        batchToolsHandler.download_path
                    ),
                    final_path,
                )
            )
            is True
        ):
            status = PackageStatus.SUCCESS.value
        else:
            status = PackageStatus.FAILED.value

        batchToolsHandler.batchTaskDao.update_property(
            batchTaskId,
            "package_info",
            json.dumps(
                {
                    "result": final_path,
                    "status": status,
                    "message": "",
                }
            ),
        )
    except Exception as e:
        print("打包失败", e)
        batchToolsHandler.batchTaskDao.update_property(
            batchTaskId,
            "package_info",
            json.dumps(
                {
                    "result": file_path,
                    "status": PackageStatus.FAILED.value,
                    "message": "打包失败 {}".format(e),
                }
            ),
        )
        traceback.print_exc()
        pass


def resolve_results(results: list[dict], dir: str):
    """
    解析结果
    """
    img_id_cache = {}
    max_workers = get_max_workers("io")

    print(f"------max workers------: {max_workers}")

    # 文件名必须在单线程里按数据库顺序依次分配：img_id_cache 无锁，并发分配
    # 会让去重序号 (n) 随线程调度随机分布（参数查找表无法与包内文件对应），
    # 且两个线程可能拿到同一个文件名导致互相覆盖、丢失结果
    copy_jobs: list[tuple[str, str]] = []
    text_jobs: list[tuple[str, str]] = []

    for item in results:
        params_config = json.loads(item.get("ParamsConfig", "[]"))
        output_file_name = build_output_file_name(params_config, dir)

        for rl in item.get("list", []):
            type = rl.get("type")
            value = rl.get("value")

            if type in ["image", "video", "audio"]:
                output_directory = folder_paths.get_output_directory()
                path = os.path.join(output_directory, value)

                if not os.path.isfile(path):
                    new_file_path = get_file_absolute_path(path)
                    if os.path.exists(new_file_path):
                        path = new_file_path
                if not os.path.isfile(path):
                    print(f"File not found: {path}")
                    continue

                # 获取文件后缀
                _, file_extension = os.path.splitext(os.path.basename(path))

                temp_full_name = next_available_filename(
                    img_id_cache, output_file_name, file_extension
                )
                copy_jobs.append((path, os.path.join(dir, temp_full_name)))
            elif type == "text":
                # 处理文本类的结果
                temp_full_name = next_available_filename(
                    img_id_cache, output_file_name, ".txt"
                )
                text_jobs.append((temp_full_name, value))

    # 使用 ThreadPoolExecutor 并行复制文件到临时文件夹
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(shutil.copy2, src, dst) for src, dst in copy_jobs
        ] + [
            executor.submit(file_processor.save_json_array_to_txt, dir, name, value)
            for name, value in text_jobs
        ]
        for future in as_completed(futures):
            # 确保所有任务完成
            future.result()
