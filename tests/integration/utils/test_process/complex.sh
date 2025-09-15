#!/usr/bin/env bash

n=0

for _ in $(seq 1 100); do
	echo "$n"
	(( n++ )) || true
	sleep 0
	echo "$n" >&2
	(( n++ )) || true
	echo "$n" >&2
	(( n++ )) || true
	echo "$n" >&2
	(( n++ )) || true
	sleep 0
done
