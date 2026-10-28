# SPDX-FileCopyrightText: 2026 MOD Audio UG
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Metadata kept next to user files, about where they come from.

A download from a known source (eg. a Tone3000 tone) gets one sidecar with the
extension of the source:

- a single file:            "NAM Models/Clean.nam"     -> "NAM Models/Clean.nam.t3k"
- a folder of many files:   "NAM Models/VOX AC 30/..." -> "NAM Models/VOX AC 30/metadata.t3k"

The sidecar holds the source data as JSON, with a "models" list that has one entry
per downloaded file, "file" being its (final) file name:

    {"toneId": 42, "title": "...", ..., "models": [{"file": "Clean.nam", "modelId": 7, ...}]}

No file list matches the sidecar extensions, so they never show up as files a plugin
can load.
"""

import json
import logging
import os

# metadata source -> sidecar extension, only these sources are written
SOURCES = {
    'T3K': '.t3k',
}

# sidecar name, plus the extension, of a folder of many files
FOLDER_SIDECAR = 'metadata'


def _read(sidecar: str) -> dict:
    try:
        with open(sidecar, 'r', encoding='utf-8') as fh:
            data = json.load(fh)
    except (IOError, OSError, ValueError) as e:
        logging.error("can't read the file metadata %s: %s", sidecar, e)
        return None
    return data if isinstance(data, dict) else None


def _for_file(data: dict, basename: str) -> dict:
    # the data of a download with the "model" entry of the file in place of all of them
    data = dict(data)
    models = data.pop('models', None)
    data['model'] = None
    if isinstance(models, list):
        for model in models:
            if isinstance(model, dict) and model.get('file') == basename:
                data['model'] = model
                break
    return data


def save(fullname: str, metadata: dict, folder: bool) -> dict:
    """Add the file fullname to the metadata saved for its download.

    folder tells whether the file is one of the many in the folder of the download,
    sharing the folder sidecar, or the single downloaded file, with its own sidecar.
    metadata = {'source': 'T3K', 'data': {..., 'models': [{...}]}}, the models entries
    are about fullname. Files of the same download (same toneId) are collected in one
    sidecar, anything else found there is replaced.

    Returns the metadata of the file as load() does, or None if it is not valid or
    can't be written.
    """
    filename = os.path.basename(fullname)

    if not isinstance(metadata, dict):
        return None

    source = metadata.get('source')
    data = metadata.get('data')

    if not isinstance(source, str) or source not in SOURCES or not isinstance(data, dict):
        logging.warning("file metadata for %s ignored, unknown source or no data", filename)
        return None

    models = data.get('models', [])
    if not isinstance(models, list) or not all(isinstance(model, dict) for model in models):
        logging.warning("file metadata for %s ignored, malformed models", filename)
        return None

    data = dict(data)
    data['models'] = [dict(model, file=filename) for model in models]

    if folder:
        sidecar = os.path.join(os.path.dirname(fullname), FOLDER_SIDECAR + SOURCES[source])
    else:
        sidecar = fullname + SOURCES[source]
    existing = _read(sidecar) if os.path.exists(sidecar) else None

    if existing is not None and existing.get('toneId') == data.get('toneId') and isinstance(existing.get('models'), list):
        data['models'] = [model for model in existing['models']
                          if not isinstance(model, dict) or model.get('file') != filename] + data['models']

    try:
        with open(sidecar, 'w', encoding='utf-8') as fh:
            json.dump(data, fh)
    except (IOError, OSError, TypeError, ValueError) as e:
        logging.error("can't write the file metadata %s: %s", sidecar, e)
        return None

    return {'source': source, 'data': _for_file(data, filename)}


def load(fullname: str, names: set) -> dict:
    """Read the metadata saved for the file fullname, or None if there is none.

    The file own sidecar first, then the one of its folder. The returned data has the
    "model" entry of fullname (None if missing) in place of the whole "models" list.
    names are the file names in the folder of fullname, so a file without metadata
    costs no filesystem access.
    """
    folder, basename = os.path.split(fullname)

    for source, ext in SOURCES.items():
        for sidecar in (basename + ext, FOLDER_SIDECAR + ext):
            if sidecar not in names:
                continue
            data = _read(os.path.join(folder, sidecar))
            if data is not None:
                return {'source': source, 'data': _for_file(data, basename)}

    return None
