#!/usr/bin/env python3

import argparse
import json
import logging
import os
import time
import yaml
from datetime import datetime, timedelta, timezone
from dateutil.parser import isoparse

import ed_bgs

"""
 " Configuration
"""
__configfile_fd = os.open("ed-bgs_config.yaml", os.O_RDONLY)
__configfile = os.fdopen(__configfile_fd)
config = yaml.load(__configfile, Loader=yaml.CLoader)

"""
 " Logging
"""
os.environ['TZ'] = 'UTC'
time.tzset()
__default_loglevel = logging.INFO
logger = logging.getLogger('report-wars')
logger.setLevel(__default_loglevel)
__logger_ch = logging.StreamHandler()
__logger_ch.setLevel(__default_loglevel)
__logger_formatter = logging.Formatter('%(asctime)s; %(name)s; %(levelname)s; %(module)s.%(funcName)s: %(message)s')
__logger_formatter.default_time_format = '%Y-%m-%d %H:%M:%S';
__logger_formatter.default_msec_format = '%s.%03d'
__logger_ch.setFormatter(__logger_formatter)
logger.addHandler(__logger_ch)

"""
 " Command-Line Arguments
"""
__parser = argparse.ArgumentParser()
__parser.add_argument('--loglevel', help='set the log level to one of: DEBUG, INFO (default), WARNING, ERROR, CRITICAL')
__parser.add_argument('--age', type=int, help='How many hours ago is considered outdated.')

__datasource = __parser.add_mutually_exclusive_group(required=True)
__datasource.add_argument('--jsonfilename', help='Name of file containing elitebgs.app API output to process')
__datasource.add_argument('--faction', help='Name of the Minor Faction to report on.')

args = __parser.parse_args()
if args.loglevel:
  level = getattr(logging, args.loglevel.upper())
  logger.setLevel(level)
  __logger_ch.setLevel(level)


def main():
  hours_ago = args.age if args.age else config.get('outdated_hours', 24)

  if args.jsonfilename:
    with open(args.jsonfilename, 'r', encoding='utf-8') as f:
      j = json.load(f)
      data = j['docs'][0]

  elif args.faction:
    db = ed_bgs.database(config['database']['url'], logger)
    ebgs = ed_bgs.EliteBGS(logger, db)
    data = ebgs.faction(args.faction)

  else:
    logger.error("No data source was specified?")
    exit(-1)

  since = datetime.now(tz=timezone.utc) - timedelta(hours=hours_ago)
  for s in data['faction_presence']:
    updated = isoparse(s['updated_at'])
    if (updated < since):
      #print(f'{s["system_name"]:30} {updated}')
      print(s["system_name"])

if __name__ == '__main__':
  main()
