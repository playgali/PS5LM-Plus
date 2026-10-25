#!/usr/bin/env python3
"""Exercise the real logger against a full pipe on a POSIX development host.

Requires a C++17 compiler and initialized llama.cpp submodule. No PS5 SDK needed.
"""
import os
from pathlib import Path
import shlex
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent.parent
LLAMA = ROOT / 'third_party/llama.cpp'
PATCH = ROOT / 'patches/0006-log-never-blocks.patch'


def run(args, **kwargs):
    return subprocess.run(args, check=True, timeout=120, **kwargs)


def main():
    # Refuse an unpatched tree rather than accidentally testing the wrong policy.
    run(['git', '-C', str(LLAMA), 'apply', '--reverse', '--check', str(PATCH)])
    with tempfile.TemporaryDirectory(prefix='ps5lm-log-test-') as tmp:
        tmp = Path(tmp)
        original = tmp / 'original'
        original.mkdir()
        (original / 'log.cpp').write_bytes(subprocess.check_output(
            ['git', '-C', str(LLAMA), 'show', 'HEAD:common/log.cpp']))
        for policy, ps5, source in [('ps5', True, LLAMA / 'common'),
                                    ('native', False, LLAMA / 'common'),
                                    ('original-ps5', True, original)]:
            exe = tmp / policy
            command = shlex.split(os.environ.get('CXX', 'c++'))
            command += ['-std=c++17', '-pthread']
            if ps5:
                command += ['-D__PROSPERO__']
            for directory in [source, LLAMA / 'common', LLAMA / 'include',
                              LLAMA / 'ggml/include', LLAMA / 'vendor']:
                command += ['-I' + str(directory)]
            command += [str(ROOT / 'tests/log-backpressure.cpp'),
                        str(LLAMA / 'common/json.cpp'), '-o', str(exe)]
            run(command)
            for mode in [[], ['json']]:
                result = subprocess.run([str(exe), *mode], capture_output=True,
                                        text=True, timeout=15)
                expected = 1 if policy == 'original-ps5' else 0
                if result.returncode != expected:
                    raise RuntimeError(f'{policy} {mode}: {result.stdout} {result.stderr}')
                label = 'negative control (expected failure)' if expected else policy
                print(f'{label}: {result.stdout.strip()}')
    print('All backpressure checks passed; unpatched PS5 control reproduced blocking.')


if __name__ == '__main__':
    main()
