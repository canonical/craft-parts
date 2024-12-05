#!/usr/bin/env bash

n=0

for i in $(seq 1 100); do
	echo "$n"
	let "n++"
	sleep 0
	echo "$n" >&2
	let "n++"
	echo "$n" >&2
	let "n++"
	echo "$n" >&2
	let "n++"
	sleep 0
done
