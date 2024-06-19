#!/usr/bin/python3

import koji
import xml.etree.ElementTree as ET
import argparse
import re

parser = argparse.ArgumentParser()
parser.add_argument("-plan", required=True, help="Path to Build Plan")
parser.add_argument("-hub", default="https://kojihub.stream.rdu2.redhat.com/kojihub", help="Koji hub API URL")
parser.add_argument("-tag", default="c9s-pending", help="Koji tag to get builds from")
parser.add_argument("-event", type=int, default=None, help="Koji event to query historical data")
parser.add_argument("-lookaside", default="https://sources.stream.centos.org/sources/rpms", help="Lookaside cache base URL")
parser.add_argument("builds", nargs='*', help="Builds to override the ones tagged in Koji")
args = parser.parse_args()
    
ks = koji.ClientSession(args.hub)

components = set(element.text for element in ET.parse(args.plan).findall('.//component'))

tagged_builds = ks.listTagged(args.tag, args.event, latest=True, inherit=True)

ks.multicall = True
for build in tagged_builds:
    if build['name'] in components:
        ks.getBuild(build['id'])
for override in args.builds:
    m = re.match(r'^(.+)-([^-]+)-([^-]+)$', override)
    name =  m.group(1)
    if name in components:
        ks.getBuild(override)
build_infos = ks.multiCall(strict=True)

builds = {}
for [build] in build_infos:
    component = build['name']
    builds[component] = build

print(f'<subject>')

for component in sorted(components):
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
