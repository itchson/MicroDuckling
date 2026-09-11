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
COMPONENT_LICENSES = {
    'IMU': 'CC-BY-SA-3.0', 'Buck_0': 'Apache-2.0',
}
COMPONENT_PATHS = {name: f'components/meshes/{name}.json' for name in COMPONENT_LICENSES}
ADAFRUIT_NOTICES = {
    'IMU': ('adafruit-lsm6ds3', 'Adafruit_LSM6DS3.brd'),
    'ServoController': ('adafruit-pca9685', 'Adafruit PCA9685 rev C.brd'),
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_mesh(path, record=None):
    name = path.stem
    data = read_json(path)
    vertices = np.asarray(data['positions'], dtype=float).reshape(-1, 3)
    indices = np.asarray(data['indices'])
    require(len(vertices) > 0 and np.isfinite(vertices).all(), 'Invalid vertices: ' + name)
    require(indices.ndim == 1 and len(indices) > 0 and len(indices) % 3 == 0, 'Incomplete triangles: ' + name)
    require(np.equal(indices, indices.astype(int)).all() and indices.min() >= 0 and indices.max() < len(vertices), 'Invalid indices: ' + name)
    if data.get('groups'):
        end = 0
        for group in sorted(data['groups'], key=lambda g: g['start']):
            require(group['start'] == end and group['count'] > 0 and group['count'] % 3 == 0, 'Invalid material range: ' + name)
            require(isinstance(group['materialIndex'], int) and 0 <= group['materialIndex'] < len(data['materials']), 'Invalid material index: ' + name)
            end += group['count']
        require(end == len(indices), 'Uncovered material triangles: ' + name)
    if record is not None:
        require(data.get('groups') and record['material_groups'] == len(data['materials']), 'Missing component materials: ' + name)
        bounds = np.concatenate((vertices.min(axis=0), vertices.max(axis=0)))
        require(np.allclose(record['bbox'], bounds, rtol=0, atol=1e-5), 'Stale component bounds: ' + name)


def validate_components(root):
    folder = root / 'components'
    bundle = read_json(folder / 'records.json')
    records = bundle['parts']
    require(bundle.get('units') == 'mm' and bundle.get('mass_estimates_scope') == 'full_physical_assembly', 'Incorrect component units/mass scope')
    require(len(records) == 2 and {r['name'] for r in records} == set(COMPONENT_LICENSES), 'Missing, extra or duplicate component records')
    require({p.name for p in (folder / 'meshes').iterdir()} == {name + '.json' for name in COMPONENT_LICENSES}, 'Unexpected component mesh files')
    notices = read_json(folder / 'NOTICE.json')['assets']
    require(len(notices) == 2 and {n['name'] for n in notices} == set(COMPONENT_LICENSES), 'Missing, extra or duplicate component notices')
    by_name = {notice['name']: notice for notice in notices}
    inputs = {item['path']: item for item in read_json(root / 'references/inputs.json')['files']}
    for record in records:
        name = record['name']
        notice = by_name[name]
        relative_mesh = f'meshes/{name}.json'
        require(record['mesh_path'] == notice['mesh_path'] == relative_mesh, 'Unexpected component mesh path: ' + name)
        require(record['mesh_license'] == notice['license'] == COMPONENT_LICENSES[name], 'Incorrect component license: ' + name)
        require(record.get('visual_geometry_only') is True and record.get('mass_estimates_scope') == 'full_physical_assembly', 'Missing visual/physical distinction: ' + name)
        require(record.get('link') == 'body' and record.get('kind') == 'hardware', 'Unexpected electronics attachment: ' + name)
        require(np.isfinite(record['mass_g']) and record['mass_g'] > 0 and np.asarray(record['com_mm']).shape == (3,) and np.isfinite(record['com_mm']).all(), 'Invalid component physical estimate: ' + name)
        mesh = folder / relative_mesh
        require(sha256(mesh) == notice['mesh_sha256'], 'Component hash mismatch: ' + name)
        validate_mesh(mesh, record)
        require(notice.get('title') and notice.get('author'), 'Missing component attribution: ' + name)
        if name in ADAFRUIT_NOTICES:
            directory, board = ADAFRUIT_NOTICES[name]
            require(notice['source_board_file'] == board and notice['source_board_sha256'] == inputs[board]['sha256'], 'Adafruit source identity mismatch: ' + name)
            require(notice.get('source_url', '').startswith('https://github.com/adafruit/') and notice.get('adaptation_changes') and notice.get('adaptation_author'), 'Missing Adafruit source/change notice: ' + name)
            require(notice['license_url'] == 'https://creativecommons.org/licenses/by-sa/3.0/' and notice['upstream_notice_directory'] == 'licenses/' + directory, 'Incorrect Adafruit notice location: ' + name)
            filenames = ['README.md', 'license.txt', 'LICENSE'] if name == 'IMU' else ['README.md', 'license.txt']
            for filename in filenames:
                reference = inputs[f'notices/{directory}/{filename}']
                require(sha256(folder / 'licenses' / directory / filename) == reference['sha256'], 'Changed/missing upstream notice: ' + directory + '/' + filename)
        else:
            require(notice.get('source_urls_for_facts_and_visual_reference') and notice.get('creation_method') and notice.get('trademark_note'), 'Missing regulator provenance: ' + name)
            require(notice['license_url'] == 'https://www.apache.org/licenses/LICENSE-2.0', 'Incorrect regulator license URL: ' + name)
    require((folder / 'licenses/Apache-2.0.txt').read_text(encoding='utf-8') == (root / 'LICENSE').read_text(encoding='utf-8'), 'Component Apache license differs from repository license')
    return records


def validate_tracked_names(tracked):
    for name in filter(None, tracked):
        file = Path(name)
        require(not name.startswith(('build/', 'work/', 'references/components_r02/', 'viewer/public/', '.openai/')), 'Local/generated file tracked: ' + name)
        require(file.suffix.lower() not in ('.brd', '.sch', '.blend', '.pdf', '.zip'), 'Unreviewed binary/reference tracked: ' + name)
        require(file.suffix.lower() != '.fcstd' or name == 'cad/MicroDuckling_R05_mechanical.FCStd', 'Unreviewed native assembly tracked: ' + name)
        require(file.suffix.lower() not in ('.step', '.stp') or name == 'cad/MicroDuckling_R05_printed.step', 'Unreviewed STEP tracked: ' + name)
        if file.stem.casefold() in {'imu', 'servocontroller', 'buck_0', 'buck_1'}:
            require(name in COMPONENT_PATHS.values(), 'Electronics mesh outside approved component path: ' + name)


def validate():
    cad = ROOT / 'cad'
    assembly = json.loads((cad / 'assembly.json').read_text(encoding='utf-8'))
    records = assembly['parts']
    names = {r['name'] for r in records}
    require(len(names) == len(records) == 90, 'Review the 90-record mechanical manifest when the design changes')
    require(not names & COMPONENT_LICENSES.keys(), 'Electronics geometry in the mechanical-only assembly')
    require(assembly.get('public_preview'), 'Missing public-preview scope')
    require({p.stem for p in (cad / 'meshes').glob('*.json')} == names, 'Stale or missing preview meshes')
    printables = {r['name'] for r in records if r['kind'] in ('print', 'coupon')}
    require(len(printables) == 17, 'Review printable allowlist when the design changes')
    for ext in ('stl', '3mf'):
        require({p.stem for p in (cad / ext).glob('*.' + ext)} == printables, 'Missing or extra ' + ext)
    for name in sorted(names):
        validate_mesh(cad / 'meshes' / (name + '.json'))
    components = validate_components(ROOT)
    physical = [r for r in records if r['kind'] != 'coupon'] + components
    require(np.isclose(sum(r['mass_g'] for r in physical), assembly['mass_g'], rtol=0, atol=1e-6), 'Restored component records do not match the intended assembly mass')
    physics = read_json(ROOT / 'simulation/browser/robot-physics.json')
    require(physics['provenance']['sourceCadSha256'] == assembly['public_preview']['source_cad_sha256'], 'Browser physics derives from a different CAD revision')
    require(np.isclose(physics['totalMassKg'] * 1000, assembly['mass_g'], rtol=0, atol=1e-6), 'Stale browser assembly mass')
    require(np.isclose(sum(link['massKg'] for link in physics['links']), physics['totalMassKg'], rtol=0, atol=1e-10), 'Browser link mass accounting mismatch')
    neutral_com = sum(link['massKg'] * (np.array(link['comM']) + physics['cadZeroOriginsM'][link['name']]) for link in physics['links']) / physics['totalMassKg']
    require(np.allclose(neutral_com * 1000, assembly['com_mm'], rtol=0, atol=1e-6), 'Stale browser centre of mass')
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
    render_paths = {r['name']: f"cad/meshes/{r['name']}.json" for r in records if r['kind'] != 'coupon'} | COMPONENT_PATHS
    require(provenance['assembled_part_count'] == 90 and provenance['mechanical_part_count'] == 88 and provenance['component_part_count'] == 2, 'Render part count mismatch')
    require(provenance['coupons_rendered'] is False and provenance['omitted_components'] == [], 'Render exclusions mismatch')
    require(provenance['license'] == 'CC-BY-SA-3.0' and provenance['license_url'] == 'https://creativecommons.org/licenses/by-sa/3.0/', 'Missing composite render license')
    require(sha256(ROOT / 'assets/renders/LICENSE-CC-BY-SA-3.0.txt') == sha256(ROOT / 'components/licenses/adafruit-lsm6ds3/license.txt'), 'Missing or changed composite render license text')
    require(provenance['attribution']['notice'] == 'components/NOTICE.json' and provenance['attribution'].get('original_designers') and provenance['attribution'].get('adaptation_credit'), 'Missing composite render attribution')
    require(provenance['mesh_paths'] == render_paths and set(provenance['mesh_sha256']) == set(render_paths), 'Render scope mismatch')
    for name, expected in provenance['mesh_sha256'].items():
        require(sha256(ROOT / render_paths[name]) == expected, 'Render uses stale geometry: ' + name)
    sources = provenance['source_manifest_sha256']
    require(set(sources) == {'cad/assembly.json', 'components/records.json', 'components/NOTICE.json'}, 'Render manifest scope mismatch')
    for path, expected in sources.items():
        require(sha256(ROOT / path) == expected, 'Render uses stale manifest: ' + path)
    for filename in ['assets/brand/microduckling-mascot.png', 'assets/renders/assembled.png', 'assets/renders/exploded.png', 'LICENSE', 'NOTICE', 'THIRD_PARTY_NOTICES.md']:
        require((ROOT / filename).is_file(), 'Missing publication file: ' + filename)
    # Relative document links must remain usable on GitHub and in a clone.
    docs = [*ROOT.glob('*.md'), *(ROOT / 'docs').rglob('*.md'), *(ROOT / 'assets/brand').glob('*.md'), *(ROOT / 'assets/renders').glob('*.md'), ROOT / 'components/README.md']
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
        validate_tracked_names(tracked)
    print(f'Validated {len(records)} mechanical and {len(components)} component mesh records, {len(printables)} STL/3MF pairs, licenses, render/export hashes and document links.')
    print('These are file and mesh checks, not physical-build or simulation-runtime validation.')


if __name__ == '__main__':
    validate()
