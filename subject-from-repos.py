#!/usr/bin/python3

import koji
import xml.etree.ElementTree as ET
import argparse
import re
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
args = parser.parse_args()

ks = koji.ClientSession(args.hub)

components = set(element.text for element in ET.parse(args.plan).findall('.//component'))

srpms = get_srpms_from_system()
srpms.extend(get_srpms_from_repos())

component_nvrs = {}
for srpm in srpms:
    if srpm == '(none)':
        continue
    name = name_from_nvra(srpm)
    if name in components and name not in component_nvrs:
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
    if component not in builds:
        raise Exception(f'component {component} not found in the repos')
    build = builds[component]
    (scm_url, scm_commit) = build['source'][4:].split('#', 1)
    lookaside_url = f'{args.lookaside}/{component}'
    print(f'  <component>')
    print(f'    <name>{component}</name>')
    print(f'    <scm>{scm_url}</scm>')
    print(f'    <commit>{scm_commit}</commit>')
    print(f'    <lookaside>{lookaside_url}</lookaside>')
    print(f'  </component>')

print(f'</subject>')
