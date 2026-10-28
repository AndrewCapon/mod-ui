#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 MOD Audio UG
# SPDX-License-Identifier: AGPL-3.0-or-later

"""mod.filemetadata: the sidecar saved for a downloaded file or folder.

Run with:  python3 -m unittest discover -s test -p 'test_*.py'
"""

import json
import os
import sys
import tempfile
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from mod import filemetadata


def t3k(model_id, tone_id=42):
    return {'source': 'T3K', 'data': {'toneId': tone_id, 'title': 'Vöx AC30', 'description': 'Clean and crunch',
                                      'gear': 'amp', 'format': 'nam',
                                      'models': [{'modelId': model_id, 'name': 'model %d' % model_id}]}}


class TestFileMetadata(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.folder = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def path(self, *parts):
        return os.path.join(self.folder, *parts)

    def names(self, *parts):
        return set(os.listdir(self.path(*parts)))

    def read(self, sidecar):
        with open(self.path(sidecar), encoding='utf-8') as fh:
            return json.load(fh)

    def test_single_file_sidecar_next_to_the_file(self):
        saved = filemetadata.save(self.path('Clean.nam'), t3k(7), False)
        self.assertEqual(saved, {'source': 'T3K', 'data': {
            'toneId': 42, 'title': 'Vöx AC30', 'description': 'Clean and crunch', 'gear': 'amp', 'format': 'nam',
            'model': {'modelId': 7, 'name': 'model 7', 'file': 'Clean.nam'}}})
        self.assertEqual(self.read('Clean.nam.t3k')['models'], [saved['data']['model']])
        self.assertEqual(filemetadata.load(self.path('Clean.nam'), self.names()), saved)

    def test_many_files_one_sidecar_inside_the_folder(self):
        os.mkdir(self.path('VOX AC 30'))
        for model_id, name in ((7, 'Clean.nam'), (8, 'Crunch.nam')):
            open(self.path('VOX AC 30', name), 'w').close()
            filemetadata.save(self.path('VOX AC 30', name), t3k(model_id), True)

        self.assertEqual(self.names('VOX AC 30'), {'Clean.nam', 'Crunch.nam', 'metadata.t3k'})
        data = self.read(os.path.join('VOX AC 30', 'metadata.t3k'))
        self.assertEqual(data['toneId'], 42)
        self.assertEqual([(m['file'], m['modelId']) for m in data['models']], [('Clean.nam', 7), ('Crunch.nam', 8)])
        # each file gets the tone data and its own model
        for model_id, name in ((7, 'Clean.nam'), (8, 'Crunch.nam')):
            loaded = filemetadata.load(self.path('VOX AC 30', name), self.names('VOX AC 30'))['data']
            self.assertEqual((loaded['toneId'], loaded['gear'], loaded['model']['modelId']), (42, 'amp', model_id))
            self.assertNotIn('models', loaded)

    def test_a_file_saved_again_replaces_its_entry(self):
        filemetadata.save(self.path('Clean.nam'), t3k(7), True)
        filemetadata.save(self.path('Clean.nam'), t3k(9), True)
        self.assertEqual([m['modelId'] for m in self.read('metadata.t3k')['models']], [9])

    def test_a_leftover_sidecar_of_another_tone_is_replaced(self):
        filemetadata.save(self.path('Old.nam'), t3k(1, tone_id=1), True)
        filemetadata.save(self.path('Clean.nam'), t3k(7), True)
        data = self.read('metadata.t3k')
        self.assertEqual((data['toneId'], [m['file'] for m in data['models']]), (42, ['Clean.nam']))

    def test_the_sidecar_is_not_a_file_of_the_same_type(self):
        open(self.path('Clean.nam'), 'w').close()
        filemetadata.save(self.path('Clean.nam'), t3k(7), False)
        self.assertEqual([n for n in self.names() if n.lower().endswith('.nam')], ['Clean.nam'])

    def test_save_ignores_unknown_or_malformed_metadata(self):
        for metadata in (None, 'T3K', [], {'source': 'X', 'data': {}}, {'source': ['T3K'], 'data': {}},
                         {'source': 'T3K'}, {'source': 'T3K', 'data': 'id'},
                         {'source': 'T3K', 'data': {'models': 'x'}}, {'source': 'T3K', 'data': {'models': [1]}}):
            self.assertIsNone(filemetadata.save(self.path('Clean.nam'), metadata, False), metadata)
        self.assertEqual(self.names(), set())

    def test_the_file_own_sidecar_comes_first(self):
        filemetadata.save(self.path('Clean.nam'), t3k(7, tone_id=1), False)
        filemetadata.save(self.path('Crunch.nam'), t3k(8), True)
        self.assertEqual(filemetadata.load(self.path('Clean.nam'), self.names())['data']['toneId'], 1)
        self.assertEqual(filemetadata.load(self.path('Crunch.nam'), self.names())['data']['toneId'], 42)

    def test_a_file_missing_from_the_models_has_the_tone_data_only(self):
        filemetadata.save(self.path('Clean.nam'), t3k(7), True)
        loaded = filemetadata.load(self.path('Renamed.nam'), self.names())['data']
        self.assertEqual((loaded['toneId'], loaded['model']), (42, None))

    def test_load_without_sidecar(self):
        self.assertIsNone(filemetadata.load(self.path('Clean.nam'), self.names()))

    def test_load_only_looks_at_the_listed_names(self):
        filemetadata.save(self.path('Clean.nam'), t3k(7), False)
        self.assertIsNone(filemetadata.load(self.path('Clean.nam'), {'Clean.nam'}))

    def test_load_skips_a_broken_or_unexpected_sidecar(self):
        for content in ('{not json', '[1, 2]'):
            with open(self.path('Clean.nam.t3k'), 'w') as fh:
                fh.write(content)
            self.assertIsNone(filemetadata.load(self.path('Clean.nam'), self.names()), content)


if __name__ == '__main__':
    unittest.main()
