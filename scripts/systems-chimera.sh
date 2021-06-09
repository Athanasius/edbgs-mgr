#!/bin/sh
curl 'https://elitebgs.app/api/ebgs/v5/factions?name=CHIMERA' | \
  jq '.docs[] | .faction_presence[] | .system_name' | \
  sort | \
  sed -e 's/"//g;' > CHIMERA-systems.txt
