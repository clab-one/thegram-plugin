#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--agents', required=True, type=Path)
    parser.add_argument('--workspace', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    workspace = args.workspace.resolve()
    workspace.mkdir(parents=True, exist_ok=False)
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise FileExistsError(output)
    report = {'passed': False, 'workspace': str(workspace), 'commands': [],
              'coverage': 'Native CLI parsers and shared workflow bytes; no account installation, OAuth, or model invocation'}
    env = {'PATH': os.environ['PATH'], 'LANG': 'en_US.UTF-8',
           'HOME': str(workspace / 'home'), 'TMPDIR': str(workspace / 'tmp'),
           'CODEX_HOME': str(workspace / 'codex'),
           'CLAUDE_CONFIG_DIR': str(workspace / 'claude'),
           'XDG_CONFIG_HOME': str(workspace / 'xdg'),
           'CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC': '1',
           'PYTHONDONTWRITEBYTECODE': '1'}
    for name in ('home', 'tmp', 'codex', 'claude', 'xdg'):
        (workspace / name).mkdir()

    def run(command):
        result = subprocess.run(command, cwd=root, env=env, capture_output=True,
                                text=True, timeout=90)
        report['commands'].append({'argv': command, 'exitCode': result.returncode,
                                   'stdout': result.stdout, 'stderr': result.stderr})
        if result.returncode:
            raise RuntimeError(f'Command failed: {command}')
        return result.stdout

    try:
        version = json.loads((root / 'plugin.json').read_text())['version']
        lock = json.loads((root / 'skill-source.lock.json').read_text())
        report.update(version=version, canonical=lock['source'], archives={}, workflow=[])
        run(['claude', '--version'])
        run(['codex', '--version'])
        destinations = {'chatgpt': workspace / 'marketplace/plugins/thegram-cloud',
                        'claude': workspace / 'packages/claude'}
        archives = {}
        for host, destination in destinations.items():
            archive = workspace / f'thegram-{host}-{version}.zip'
            run([sys.executable, 'scripts/package_plugin.py', 'build', '--host', host,
                 '--output', str(archive), '--expected-version', version])
            run([sys.executable, 'scripts/package_plugin.py', 'validate', str(archive),
                 '--host', host, '--expected-version', version])
            archives[host] = archive
            report['archives'][host] = {'file': str(archive),
                                       'sha256': hashlib.sha256(archive.read_bytes()).hexdigest()}
            destination.mkdir(parents=True)
            with zipfile.ZipFile(archive) as package:
                package.extractall(destination)
        for relative, expected in lock['files'].items():
            canonical = (args.agents / 'skills/thegram-memory' / relative).read_bytes()
            digests = {'canonical': hashlib.sha256(canonical).hexdigest(), 'pin': expected}
            for host, archive in archives.items():
                with zipfile.ZipFile(archive) as package:
                    content = package.read('skills/thegram-cloud/' + relative)
                if relative == 'SKILL.md':
                    content = content.replace(b'\nname: thegram-cloud\n',
                                              b'\nname: thegram-memory\n', 1)
                digests[host] = hashlib.sha256(content).hexdigest()
            if any(value != expected for value in digests.values()):
                raise RuntimeError(f'Shared workflow differs: {relative}')
            report['workflow'].append({'file': relative, 'sha256': digests})
        claude = json.loads(run(['claude', 'plugin', 'validate', '--strict', '--json',
                                 str(destinations['claude'])]))
        if not claude['success']:
            raise RuntimeError('Claude strict validation failed')
        marketplace = workspace / 'marketplace'
        catalog = marketplace / '.agents/plugins/marketplace.json'
        catalog.parent.mkdir(parents=True)
        catalog.write_text(json.dumps({'name': 'thegram-host-package-validation', 'plugins': [{
            'name': 'thegram-cloud', 'source': {'source': 'local', 'path': './plugins/thegram-cloud'},
            'policy': {'installation': 'AVAILABLE', 'authentication': 'ON_INSTALL'},
            'category': 'Productivity'}]}, indent=2) + '\n')
        run(['codex', 'plugin', 'marketplace', 'add', str(marketplace), '--json'])
        discovery = json.loads(run(['codex', 'plugin', 'list', '--available', '--marketplace',
                                    'thegram-host-package-validation', '--json']))
        available = discovery['available']
        if (discovery['installed'] or len(available) != 1
                or available[0]['name'] != 'thegram-cloud'
                or available[0]['version'] != version or available[0]['installed']):
            raise RuntimeError('Codex did not discover the exact uninstalled native package')
        report['passed'] = True
    except Exception as error:
        report['error'] = str(error)
    finally:
        output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'passed': report['passed'], 'evidence': str(output)}))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
