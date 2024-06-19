#!/usr/bin/python3

import koji
import xml.etree.ElementTree as ET
import argparse
import re
import glob
import os.path
from subprocess import Popen, PIPE

def get_srpms_from_repos():
    p = Popen(["dnf", "-q", "repoquery", "-a", "--qf", "%{SOURCERPM}"], stdin=PIPE, stdout=PIPE, stderr=PIPE)
    output, err = p.communicate(b"")
    if p.returncode != 0:
        raise Exception(f'dnf repoquery failed with exit code {p.returncode}; stderr: {err}')
    return output.decode().split()

def get_srpms_from_system():
    p = Popen(["rpm", "-qa", "--qf", "%{SOURCERPM}\\n"], stdin=PIPE, stdout=PIPE, stderr=PIPE)
    output, err = p.communicate(b"")
    if p.returncode != 0:
        raise Exception(f'rpmquery failed with exit code {p.returncode}; stderr: {err}')
    return output.decode().split()

def name_from_nvra(str):
    m = re.match(r'^(.+)-([^-]+)-([^-]+)\.src.rpm$', str)
    if not m:
        raise Exception(f'bad SRPM NVRA: {str}')
    return m.group(1)

parser = argparse.ArgumentParser()
parser.add_argument("-plan", required=True, help="Path to Build Plan")
parser.add_argument("-hub", default="https://kojihub.stream.rdu2.redhat.com/kojihub", help="Koji hub API URL")
parser.add_argument("-lookaside", default="https://sources.stream.centos.org/sources/rpms", help="Lookaside cache base URL")
parser.add_argument("-artifacts", default="/tmp/test-artifacts", help="Directory with test artifacts")
args = parser.parse_args()

ks = koji.ClientSession(args.hub)

components = set(element.text for element in ET.parse(args.plan).findall('.//component'))

local_scm = {}
local_ref = {}
for path in glob.glob(f'{args.artifacts}/*.src.rpm'):
    srpm = os.path.basename(path)
    name = name_from_nvra(srpm)
    dg_path = f'/tmp/dist-git/{name}'
    os.makedirs(dg_path)
    p1 = Popen(["rpm2cpio", path], stdin=PIPE, stdout=PIPE, stderr=PIPE)
    output, err = p1.communicate(b"")
    if p1.returncode != 0:
        raise Exception(f'rpm2cpio failed with exit code {p1.returncode}; stderr: {err}')
    p2 = Popen(["cpio", "-id"], stdin=PIPE, stdout=PIPE, stderr=PIPE, cwd=dg_path)
    output, err = p2.communicate(output)
    if p2.returncode != 0:
        raise Exception(f'cpio failed with exit code {p2.returncode}; stderr: {err}')
    with open(f'{dg_path}/sources', 'w') as f:
        pass
    def run_git(cmd):
        p = Popen(["git", "-C", dg_path] + cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)
        output, err = p.communicate(b"")
        if p.returncode != 0:
            raise Exception(f'git failed with exit code {p.returncode}; stderr: {err}')
        return output
    run_git(["init"])
    run_git(["add", "*"])
    run_git(["commit", "-m", "init"])
    ref = run_git(["rev-parse", "HEAD"]).decode().split()[0]
    local_scm[name] = dg_path
    local_ref[name] = ref

srpms = get_srpms_from_system()
srpms.extend(get_srpms_from_repos())

component_nvrs = {}
for srpm in srpms:
    if srpm == '(none)':
        continue
    name = name_from_nvra(srpm)
    if name in components and name not in component_nvrs and name not in local_scm:
        component_nvrs[name] = srpm[:-8]

ks.multicall = True
for nvr in component_nvrs.values():
    ks.getBuild(nvr)
build_infos = ks.multiCall(strict=True)

builds = {}
for [build], (name, nvr) in zip(build_infos, component_nvrs.items()):
    if not build:
        raise Exception(f'build {nvr} not found in Koji')
    builds[name] = build

print(f'<subject>')

for component in sorted(components):
    if component in local_scm:
        scm_url = local_scm[component]
        scm_commit = local_ref[component]
    elif component in builds:
        build = builds[component]
        (scm_url, scm_commit) = build['source'][4:].split('#', 1)
    else:
        raise Exception(f'component {component} not found in the repos nor as a test artifact')
    lookaside_url = f'{args.lookaside}/{component}'
    print(f'  <component>')
    print(f'    <name>{component}</name>')
    print(f'    <scm>{scm_url}</scm>')
    print(f'    <commit>{scm_commit}</commit>')
    print(f'    <lookaside>{lookaside_url}</lookaside>')
    print(f'  </component>')

print(f'</subject>')
