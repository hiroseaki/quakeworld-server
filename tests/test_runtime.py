import importlib.util
import os
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('entry', Path(__file__).resolve().parents[1] / 'runtime/entrypoint.py')
entry = importlib.util.module_from_spec(spec)
spec.loader.exec_module(entry)


class ConfigurationTests(unittest.TestCase):
    def test_password_file_precedence_and_unreadable_file(self):
        with tempfile.TemporaryDirectory() as directory:
            secret = Path(directory) / 'secret'
            secret.write_text('file-value\n')
            with patch.dict(os.environ, {'QW_ADMIN_PASSWORD': 'env-value', 'QW_ADMIN_PASSWORD_FILE': str(secret)}, clear=True):
                self.assertEqual(entry.password('QW_ADMIN_PASSWORD'), 'file-value')
                secret.unlink()
                with self.assertRaises(FileNotFoundError):
                    entry.password('QW_ADMIN_PASSWORD')

    def test_config_injection_rejected(self):
        for value in ['one\\two', 'one\ntwo', 'one"two', 'one;quit', '$rcon_password']:
            with patch.dict(os.environ, {'TEST': value}, clear=True):
                with self.assertRaises(ValueError):
                    entry.text('TEST')

    def test_pak_directory_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            pak = Path(directory) / 'pak0.pak'
            pak.write_bytes(struct.pack('<4sII', b'PACK', 12, 64) + struct.pack('<56sII', b'maps/e1m2.bsp', 12, 0))
            self.assertEqual(entry.pak_maps(Path(directory)), {'e1m2'})
            pak.write_bytes(struct.pack('<4sII', b'PACK', 12, 128))
            with self.assertRaises(ValueError):
                entry.pak_maps(Path(directory))

    def test_number_bounds(self):
        for value in ['0', '65536', '-1', '1;quit', '9999999999999999999']:
            with patch.dict(os.environ, {'PORT': value}, clear=True):
                with self.assertRaises(ValueError):
                    entry.number('PORT', 27500, 1, 65535)


if __name__ == '__main__':
    unittest.main()
