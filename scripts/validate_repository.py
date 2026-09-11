"""Validate the distributed review files; does not certify physical fit or Isaac physics."""
# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import hashlib
import json
import re
import subprocess
import xml.etree.ElementTree as ET
import zipfile

import numpy as np
import trimesh

ROOT = Path(__file__).resolve().parents[1]
OMITTED = {'IMU', 'ServoController', 'Buck_0', 'Buck_1'}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def validate():
    cad = ROOT / 'cad'
    assembly = json.loads((cad / 'assembly.json').read_text(encoding='utf-8'))
    records = assembly['parts']
    names = {r['name'] for r in records}
    require(len(names) == len(records), 'Duplicate public CAD names')
    require(not names & OMITTED, 'Supplier geometry in the public assembly')
    require(assembly.get('public_preview'), 'Missing public-preview scope')
    require({p.stem for p in (cad / 'meshes').glob('*.json')} == names, 'Stale or missing preview meshes')
    printables = {r['name'] for r in records if r['kind'] in ('print', 'coupon')}
    require(len(printables) == 16, 'Review printable allowlist when the design changes')
    for ext in ('stl', '3mf'):
        require({p.stem for p in (cad / ext).glob('*.' + ext)} == printables, 'Missing or extra ' + ext)
    for name in sorted(names):
        data = json.loads((cad / 'meshes' / (name + '.json')).read_text(encoding='utf-8'))
        vertices = np.asarray(data['positions'], dtype=float).reshape(-1, 3)
        indices = np.asarray(data['indices'])
        require(len(vertices) > 0 and np.isfinite(vertices).all(), 'Invalid vertices: ' + name)
        require(len(indices) > 0 and len(indices) % 3 == 0, 'Incomplete triangles: ' + name)
        require(np.equal(indices, indices.astype(int)).all() and indices.min() >= 0 and indices.max() < len(vertices), 'Invalid indices: ' + name)
        if data.get('groups'):
            end = 0
            for group in sorted(data['groups'], key=lambda g: g['start']):
                require(group['start'] == end and group['count'] > 0 and group['count'] % 3 == 0, 'Invalid material range: ' + name)
                require(0 <= group['materialIndex'] < len(data['materials']), 'Invalid material index: ' + name)
                end += group['count']
            require(end == len(indices), 'Uncovered material triangles: ' + name)
    for name in sorted(printables):
        mesh = trimesh.load_mesh(cad / 'stl' / (name + '.stl'))
        require(mesh.is_watertight and mesh.is_winding_consistent and mesh.volume > 0, 'Invalid printable STL: ' + name)
        require(len(mesh.split()) == 1, 'Disconnected STL: ' + name)
        with zipfile.ZipFile(cad / '3mf' / (name + '.3mf')) as archive:
            require(archive.testzip() is None, 'Corrupt 3MF: ' + name)
            model = ET.fromstring(archive.read('3D/3dmodel.model'))
            require(model.attrib.get('unit', 'millimeter') == 'millimeter', 'Unexpected 3MF units')
            ns = {'m': 'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'}
            models = model.findall('.//m:mesh', ns)
            require(len(models) == 1, 'Unexpected 3MF mesh count: ' + name)
            verts = [[float(v.attrib[a]) for a in ('x', 'y', 'z')] for v in models[0].findall('m:vertices/m:vertex', ns)]
            faces = [[int(t.attrib[a]) for a in ('v1', 'v2', 'v3')] for t in models[0].findall('m:triangles/m:triangle', ns)]
            other = trimesh.Trimesh(vertices=verts, faces=faces, process=True)
            require(other.is_watertight and other.is_winding_consistent and other.volume > 0, 'Invalid printable 3MF: ' + name)
            require(abs(other.volume - mesh.volume) / mesh.volume < 0.001, 'STL/3MF volume mismatch: ' + name)
    checks = json.loads((cad / 'public_export_checks.json').read_text(encoding='utf-8'))
    for filename, key in [('MicroDuckling_R05_mechanical.FCStd', 'native_sha256'), ('MicroDuckling_R05_printed.step', 'printed_step_sha256')]:
        require(hashlib.sha256((cad / filename).read_bytes()).hexdigest() == checks[key], 'Stale export check: ' + filename)
    provenance = json.loads((ROOT / 'assets/renders/render_provenance.json').read_text(encoding='utf-8'))
    require(set(provenance['mesh_sha256']) == {r['name'] for r in records if r['kind'] != 'coupon'}, 'Render scope mismatch')
    for name, expected in provenance['mesh_sha256'].items():
        require(hashlib.sha256((cad / 'meshes' / (name + '.json')).read_bytes()).hexdigest() == expected, 'Render uses stale geometry: ' + name)
    for filename in ['assets/brand/microduckling-mascot.png', 'assets/renders/assembled.png', 'assets/renders/exploded.png', 'LICENSE', 'NOTICE', 'THIRD_PARTY_NOTICES.md']:
        require((ROOT / filename).is_file(), 'Missing publication file: ' + filename)
    # Relative document links must remain usable on GitHub and in a clone.
    docs = [*ROOT.glob('*.md'), *(ROOT / 'docs').rglob('*.md'), *(ROOT / 'assets/brand').glob('*.md')]
    for doc in docs:
        text = doc.read_text(encoding='utf-8')
        require(not re.search(r'[A-Za-z]:[/\\](?:Users|Dev)[/\\]', text), 'Workstation path in ' + str(doc.relative_to(ROOT)))
        for target in re.findall(r'\]\(([^)]+)\)', text):
            target = target.strip('<>').split('#')[0]
            if not target or re.match(r'[a-z]+:', target):
                continue
            require((doc.parent / target).exists(), f'Broken link in {doc.relative_to(ROOT)}: {target}')
    # Check the actual tracked set: ignore rules alone cannot prevent a forced add.
    if (ROOT / '.git').exists():
        tracked = subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode('utf-8').split('\0')
        for name in filter(None, tracked):
            file = Path(name)
            require(not name.startswith(('build/', 'work/', 'references/components_r02/', 'viewer/public/', '.openai/')), 'Local/generated file tracked: ' + name)
            require(file.suffix.lower() not in ('.brd', '.sch', '.blend', '.pdf', '.zip'), 'Unreviewed binary/reference tracked: ' + name)
            require(file.suffix != '.FCStd' or name == 'cad/MicroDuckling_R05_mechanical.FCStd', 'Unreviewed native assembly tracked: ' + name)
            require(not (file.suffix == '.json' and file.stem in OMITTED), 'Vendor mesh tracked: ' + name)
    print(f'Validated {len(records)} public mesh records, 16 STL/3MF pairs, export hashes and document links.')
    print('These are file and mesh checks, not physical-build or simulation-runtime validation.')


if __name__ == '__main__':
    validate()
