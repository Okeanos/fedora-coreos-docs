#!/usr/bin/python3
#
# Find all shell scripts in the doc tree, use shellcheck
# to verify them, and fail on any errors.
#
# A shell script is fenced with one of the following options:
#
# [source,bash]
# [source,sh]

import argparse
import os
import re
import subprocess
import sys
import tempfile
import textwrap

ERR = '\x1b[1;31m'
WARN = '\x1b[1;33m'
RESET = '\x1b[0m'

container = os.getenv('SHELLCHECK_CONTAINER', 'koalaman/shellcheck:stable')
matcher = re.compile(r'^\[source,\s*(bash|sh)\]\n----\n(.+?\n)----$',
                     re.MULTILINE | re.DOTALL)

parser = argparse.ArgumentParser(description='Run validations on docs.')
parser.add_argument('-v', '--verbose', action='store_true',
                    help='log all detected shell scripts')
args = parser.parse_args()


def handle_error(e):
    raise e


ret = 0
for dirpath, dirnames, filenames in os.walk('.', onerror=handle_error):
    dirnames.sort()  # walk in sorted order
    for filename in sorted(filenames):
        filepath = os.path.join(dirpath, filename)
        if not filename.endswith('.adoc'):
            continue
        with open(filepath) as fh:
            filedata = fh.read()
        # Iterate over YAML source blocks
        for match in matcher.finditer(filedata):
            script = match.group(2)
            scriptline = filedata.count('\n', 0, match.start(1)) + 1
            if args.verbose:
                print(f'Checking shell script at {filepath}:{scriptline}')
            with tempfile.NamedTemporaryFile(delete=False, mode="w", encoding="utf-8") as tmpscript:
                tmpscript.write(script)
                tmpscript.flush()
                tmpscript.close()
                result = subprocess.run(
                    ['podman', 'run', '--rm', '-v=' + tmpscript.name + ':/shell-script.sh', container, '/shell-script.sh'],
                    universal_newlines=True,  # can be spelled "text" on >= 3.7
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE)
                if result.returncode != 0:
                    formatted = textwrap.indent(result.stderr.strip(), '  ')
                    # Not necessary for ANSI terminals, but required by GitHub's
                    # log renderer
                    formatted = ERR + formatted.replace('\n', '\n' + ERR)
                    print(f'{ERR}Invalid shell script at {filepath}:{scriptline}:\n{formatted}{RESET}')
                    ret = 1
                os.unlink(tmpscript.name)
sys.exit(ret)
