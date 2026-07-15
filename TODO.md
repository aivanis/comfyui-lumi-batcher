# TODO

## Bug: same-named input images across tasks overwrite each other

**Symptom:** If two batch tasks are created with *different* images that share a
filename (e.g. both called `photo.png`), the second upload silently overwrites
the first in ComfyUI's shared `input/` directory. Any sub-task that executes
after the overwrite generates with the wrong image.

**Why it happens:**

- The batcher's param upload endpoint `/resolve-file`
  (`lumi_batcher_service/handler/batch_tools.py`, `resolve_file` route) copies
  uploaded files into `input/` under their **original filename**, overwriting
  existing files — see `resolve_single_file` and `resolve_zip_file` in
  `lumi_batcher_service/common/resolve_file.py`. No dedup, unlike ComfyUI's own
  LoadImage upload widget which appends `(1)`, `(2)`, ….
- Queued prompts load `input/<filename>` at **execution time**, not creation
  time. So a task whose sub-tasks are still in the queue is affected by any
  later upload that reuses one of its filenames.
- The per-task resource snapshots (UUID-named copies in the plugin's resources
  dir, `resource_upload.py`) are only used for the detail-page preview
  (`resources_map`) and delete-cleanup — they are **not** used by generation.

**Also affected — retry:** `/batch-task/retry`
(`batch_tools.py`, `retryTask`) rebuilds prompts from the stored params config
and re-queues them, reading whatever is *currently* in `input/` under that
name. Retrying an old task after a same-named upload runs with the new image
instead of restoring from the UUID snapshot.

**Not affected:** resource snapshots, results preview, download archive
(`{batchTaskId}.tar`), and the params lookup sheet are all per-task; the sheet
records the filename param value faithfully (though the pixels behind it may be
wrong per the above). Identical files sharing a name are harmless.

**Fix ideas:**

1. Dedupe on upload in `resolve_single_file` / `resolve_zip_file`: if a
   different file with that name already exists in `input/`, write under a
   suffixed/unique name and return that name so the param value points at the
   right content (mirrors ComfyUI's native upload behavior).
2. Make retry restore inputs from the per-task UUID resource snapshots
   (copy them back into `input/`, or rewrite the prompt to reference the
   snapshot path) instead of trusting current `input/` contents.
