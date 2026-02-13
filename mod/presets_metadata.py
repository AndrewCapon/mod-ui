#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2012-2023 MOD Audio UG
# SPDX-License-Identifier: AGPL-3.0-or-later

import os
import json
import logging
from tornado import gen
from mod import (
  safe_json_load,
  TextFileFlusher
)


class PresetsMetadata(object):
    def __init__(self):
        self.waiting_for_cc = False
        self.waiting_for_cc_cbs = []

    def _dont_wait_for_cc(self):
        self.waiting_for_cc = False
        for cb in self.waiting_for_cc_cbs:
            cb()
        self.waiting_for_cc_cbs = []

    @gen.coroutine
    def load(self, bundlepath: str, instances, abort_catcher):
        """
        Load presets metadata from bundlepath.
        Metadata contains pedalboard information about presets selection for addressing, etc...
        """

        self.data = dict()
        # Check if pedalboard contains presets metadata first
        datafile = os.path.join(bundlepath, "presets-metadata.json")
        print('*****', instances, bundlepath, datafile)
        if not os.path.exists(datafile):
            self._dont_wait_for_cc()
            return

        # Load presets meta
        logging.info("******* loading presets metadata...")
        self.data = safe_json_load(datafile, dict)

        print("Loaded presets metadata:", self.data)
        # Load all plugin preset metadata possible
        for plugin_uri, preset in self.data.items():
            if abort_catcher is not None and abort_catcher.get('abort', False):
                print("WARNING: Abort triggered during presets-metadata.load requests, caller:", abort_catcher['caller'])
                return

        return

    def save(self, bundlepath):
        """Save presets metadata to bundlepath."""

        print("Saving presets metadata to:", bundlepath)
        with TextFileFlusher(os.path.join(bundlepath, "presets-metadata.json")) as fh:
            json.dump(self.data, fh, indent=4)

        return

    def get(self, preset_uri: str):
        """Get metadata for a given preset URI."""

        meta = self.data.get(preset_uri, None)
        print("Getting preset metadata for", preset_uri, meta)
        if (meta is None):
            # if no metadata is found for the preset, return a default values
            meta = {
                'enabled': True
            }

        return meta

    def set(self, preset_uri: str, metadata: dict, callback):
        """Set metadata for a given preset URI."""
        self.data[preset_uri] = metadata

        print("Setting preset metadata for", preset_uri, self.data[preset_uri])
        if (callback is not None):
            callback(True)
            
        return metadata
