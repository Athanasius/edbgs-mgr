#!/bin/sh
# vim: tabstop=2 shiftwidth=2 expandtab wrapmargin=0 textwidth=0

if [ -z "$1" -o -z "$2" ];
then
  echo "spansh-tourist-planner <start system> <jump range>"
  exit 1
fi
start=$( echo "$1" | sed -e 's/ /%20/g;' )
range=$2

# curl --data <post data> https://www.spansh.co.uk/api/tourist/route
#
# data:
#  range=<x>&loop=0&source=<start system>&destination=<system>&destination=<system>...

data='range=32&loop=0'
data="${data}&source=${start}"
for s in $(fgrep -v "${start}" CHIMERA-systems.txt | sed -e 's/ /%20/g;');
do
  # s=$(echo "$s" | sed -e 's/ /%20/g;')
  data="${data}&destination=${s}"
done

echo $data
echo
curl --data "${data}" https://www.spansh.co.uk/api/tourist/route > spansh-tourist.out
echo "https://www.spansh.co.uk/tourist/results/$(jq -r '.job' spansh-tourist.out)"
