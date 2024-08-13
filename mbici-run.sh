#!/bin/sh
set -eu
echo "${PLAN}" | base64 -d | zcat >plan.xml
echo "${PLATFORM}" | base64 -d | zcat >platform.xml
echo "${SUBJECT}" | base64 -d | zcat >subject.xml

echo === CPU info ===
lscpu
echo
echo === Memory info ===
free -h
echo

set -x

mbici-wf generate \
	 --plan plan.xml \
	 --platform platform.xml \
	 --subject subject.xml \
	 --workflow workflow.xml

mbici-wf execute \
	 --batch-mode \
	 --max-checkout-tasks 10 \
	 --max-srpm-tasks 1 \
	 --max-rpm-tasks 1 \
	 --workflow workflow.xml \
	 --result-dir result \
	 --cache-dir cache \
	 --work-dir work

mbici-wf report \
	 --tmt \
	 --plan plan.xml \
	 --platform platform.xml \
	 --subject subject.xml \
	 --workflow workflow.xml \
	 --result-dir result \
	 --report-dir "${TMT_TEST_DATA}"
