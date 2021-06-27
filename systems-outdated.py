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
logger = logging.getLogger('systems-outdated')
logger.setLevel(__default_loglevel)
__logger_ch = logging.StreamHandler()
__logger_ch.setLevel(__default_loglevel)
__logger_formatter = logging.Formatter('%(asctime)s; %(name)s; %(levelname)s; %(module)s.%(funcName)s:%(lineno)s %(message)s')
__logger_formatter.default_time_format = '%Y-%m-%d %H:%M:%S';
__logger_formatter.default_msec_format = '%s.%03d'
__logger_ch.setFormatter(__logger_formatter)
logger.addHandler(__logger_ch)

"""
 " Command-Line Arguments
"""
__parser = argparse.ArgumentParser()
__parser.add_argument('--loglevel', help='set the log level to one of: DEBUG, INFO (default), WARNING, ERROR, CRITICAL')

__age_args = __parser.add_mutually_exclusive_group(required=True)
__age_args.add_argument('--age', type=int, help='How many hours ago is considered outdated.')
__age_args.add_argument('--tick-plus', type=int, help='How many hours to add to last tick time to use as max age.')

__datasource = __parser.add_mutually_exclusive_group(required=True)
__datasource.add_argument('--jsonfilename', help='Name of file containing elitebgs.app API output to process')
__datasource.add_argument('--faction', help='Name of the Minor Faction to report on.')

__spansh_sub = __parser.add_subparsers(title='Optional commands', description='Additional commands that may allow, or require, additional arguments.')
__spansh = __spansh_sub.add_parser('spansh-route', help='Generate a spansh tourist route, requires additional arguments.')
#__spansh.add_argument('--spansh-route', action='store_true', help='Generate a spansh tourist route')
__spansh.add_argument('--range', type=float, required=True, help='Ship max jump range for routing')
__spansh.add_argument('--start-system', type=str, required=True, help='Start system for tourist route')


args = __parser.parse_args()
if args.loglevel:
  level = getattr(logging, args.loglevel.upper())
  logger.setLevel(level)
  __logger_ch.setLevel(level)


def main():
  db = ed_bgs.database(config['database']['url'], logger)
  ebgs = ed_bgs.EliteBGS(logger, db)

  tourist_systems = []
  if args.tick_plus is not None:
    last_tick = ebgs.last_tick()
    logger.info(f'Last tick allegedly around: {last_tick}')
    since = last_tick + timedelta(hours=args.tick_plus)
  
  elif args.age:
    hours_ago = args.age if args.age else config.get('outdated_hours', 24)
    since = datetime.now(tz=timezone.utc) - timedelta(hours=hours_ago)

  else:
    logger.error('Neither --age or --tick-plus specified')
    exit(-1)

  logger.info(f'Comparing system data age against: {since}')

  if args.jsonfilename:
    logger.info('Using provided static file data...')
    with open(args.jsonfilename, 'r', encoding='utf-8') as f:
      j = json.load(f)
      data = j['docs'][0]

    # We only have static file data, so do the simple check.
    for s in data['faction_presence']:
      updated = isoparse(s['updated_at'])
      if (updated < since):
        #print(f'{s["system_name"]:30} {updated}')
        tourist_systems.append(s['system_name'])

  elif args.faction:
    logger.info('Using current local data ...')

    faction_id = db.faction_id_from_name(args.faction)
    if faction_id is None:
      logger.error(f'Unknown faction: {args.faction} - CASE MATTERS!')
      exit(-3)

    # Anywhere we know there was a conflict already and not updated since
    # the last known tick + fuzz.
    systems = db.systems_conflicts_older_than(since, faction_id=faction_id)
    for s in systems:
      logger.debug(f'Adding system because of on-going conflict: {s.name}')
      tourist_systems.append(s.name)

    # Anywhere that was last seen with 'close' inf% to another MF and not
    # updated this tick.

    # How many days could a system go until we could *just* pull back a
    # conflict we're losing?
    #
    # 5: Last Data
    # 4: Conflict goes Pending
    # 3: Lost Day 1
    # 2: Lost Day 2
    # 1: Lost Day 3
    # 0: <today>
    ticks = ebgs.ticks_since(datetime.now(tz=timezone.utc) - timedelta(days=6))
    since = ticks[3]
    systems = db.systems_older_than(since + timedelta(hours=args.tick_plus))
    for s in systems:
      logger.debug(f'Adding system because too old: {s.name}')
      tourist_systems.append(s.name)

  else:
    logger.error("No data source was specified?")
    exit(-1)

  if len(tourist_systems) > 0:
    if hasattr(args, 'range') and hasattr(args, 'start_system'):
      spansh = ed_bgs.Spansh(logger)
      route_url = spansh.tourist_route(args.start_system, args.range, tourist_systems, False)
      print(route_url)

    else:
      print('Systems to be updated:')
      for s in tourist_systems:
        print(s)

  else:
    logger.info('No systems to update!')
    exit(1)

if __name__ == '__main__':
  main()
