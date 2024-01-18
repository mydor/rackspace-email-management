#!/bin/bash

case "$@" in
	-h|'-?')
		echo "$0 [-f]"
		echo "    -f  run a full sync"
		echo -e "\nDefault is to run only an incremental sync"
		;;
	-f)
		./sync.py
		;;
	*|-i)
		./split.py
		./sync-inc.py
		;;
esac

