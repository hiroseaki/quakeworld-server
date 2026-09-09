import base64
import contextlib
import importlib.util
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('upstream', Path(__file__).resolve().parents[1] / 'scripts/check-upstream.py')
upstream = importlib.util.module_from_spec(spec)
spec.loader.exec_module(upstream)


class UpstreamTests(unittest.TestCase):
    def test_development_commit_and_version_are_updated_together(self):
        commit = 'b' * 40
        def api(path):
            if path in ('mvdsv', 'qtv'):
                return {'default_branch': 'master'}
            if path in ('ktx/releases/latest', 'qwfwd/releases/latest'):
                return {'tag_name': '1.47'}
            if '/commits/' in path:
                return {'sha': commit}
            if path == f'mvdsv/contents/src/version.h?ref={commit}':
                return {'content': base64.b64encode(b'#define SERVER_VERSION "1.21-dev"\n').decode()}
            self.fail(f'Unexpected API request: {path}')
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dockerfile = root / 'Dockerfile'
            dockerfile.write_text(''.join(f'ARG {name}_COMMIT={"a" * 40}\nARG {name}_VERSION=1.11\n' for name in ('MVDSV', 'KTX', 'QWFWD', 'QTV')))
            with patch.object(upstream, 'ROOT', root), patch.object(upstream, 'api', side_effect=api), patch('sys.argv', ['check-upstream.py', '--write']), patch.dict('os.environ', {}, clear=True), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(upstream.main(), 0)
            updated = dockerfile.read_text()
            self.assertIn(f'ARG MVDSV_COMMIT={commit}', updated)
            self.assertIn('ARG MVDSV_VERSION=1.21-dev', updated)
            self.assertIn('ARG KTX_VERSION=1.47', updated)


if __name__ == '__main__':
    unittest.main()
