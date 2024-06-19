#!/bin/sh
set -eu

echo === CPU info ===
lscpu
echo
echo === Memory info ===
free -h
echo

rm -rf /tmp/dist-git/
./subject-from-repos.py -plan plan.xml >subject.xml

set -x

mbici-wf generate \
	 -plan plan.xml \
	 -platform platform.xml \
	 -subject subject.xml \
	 -workflow workflow.xml

mbici-wf run \
	 -batch \
	 -maxCheckoutTasks 10 \
	 -maxSrpmTasks 1 \
	 -maxRpmTasks 1 \
	 -workflow workflow.xml \
	 -resultDir result \
	 -cacheDir cache \
	 -workDir work

mbici-wf report \
	 -full \
	 -plan plan.xml \
	 -platform platform.xml \
	 -subject subject.xml \
	 -workflow workflow.xml \
	 -resultDir result \
	 -reportDir "${TMT_TEST_DATA}"
