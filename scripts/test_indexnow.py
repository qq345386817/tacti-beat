#!/usr/bin/env python3
"""Offline tests: no requests or URL submissions are made."""
import unittest
from unittest.mock import patch

import submit_indexnow as indexnow


class IndexNowTests(unittest.TestCase):
    def test_payload_contains_only_sitemap_canonicals(self):
        data = indexnow.payload()
        self.assertEqual(len(data['urlList']), 64)
        self.assertEqual(len(set(data['urlList'])), 64)
        self.assertTrue(all(u.startswith(indexnow.ORIGIN + '/') for u in data['urlList']))
        self.assertEqual(data['keyLocation'], indexnow.ORIGIN + '/' + indexnow.KEY_FILE.name)

    def test_wrong_live_key_prevents_submission(self):
        with patch.object(indexnow, 'request', return_value=(200, b'wrong key')) as request:
            with self.assertRaisesRegex(RuntimeError, 'No URLs submitted'):
                indexnow.submit(indexnow.payload())
            self.assertEqual(request.call_count, 1)

    def test_old_sitemap_prevents_submission(self):
        data = indexnow.payload()
        with patch.object(indexnow, 'request', side_effect=[(200, data['key'].encode()), (200, b'old sitemap')]) as request:
            with self.assertRaisesRegex(RuntimeError, 'No URLs submitted'):
                indexnow.submit(data)
            self.assertEqual(request.call_count, 2)

    def test_pending_verification_is_accepted(self):
        with patch.object(indexnow, 'wait_for_production'), patch.object(indexnow, 'request', return_value=(202, b'')):
            indexnow.submit(indexnow.payload())

    def test_api_rejection_is_not_success(self):
        with patch.object(indexnow, 'wait_for_production'), patch.object(indexnow, 'request', return_value=(403, b'Invalid key')):
            with self.assertRaisesRegex(RuntimeError, 'HTTP 403'):
                indexnow.submit(indexnow.payload())


if __name__ == '__main__':
    unittest.main()
