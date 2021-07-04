#!/usr/bin/env python3
"""Identify systems with stale data."""

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime, timedelta, timezone

import yaml
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
__logger_formatter = logging.Formatter('%(asctime)s; %(name)s; %(levelname)s; %(module)s.%(funcName)s:%(lineno)s %(message)s')  # noqa: E501
__logger_formatter.default_time_format = '%Y-%m-%d %H:%M:%S'
__logger_formatter.default_msec_format = '%s.%03d'
__logger_ch.setFormatter(__logger_formatter)
logger.addHandler(__logger_ch)

"""
 " Command-Line Arguments
"""
__parser = argparse.ArgumentParser()
__parser.add_argument(
  '--loglevel',
  help='set the log level to one of: DEBUG, INFO (default), WARNING, ERROR, CRITICAL'
)

__age_args = __parser.add_mutually_exclusive_group(required=True)
__age_args.add_argument(
  '--age',
  type=int, help='How many hours ago is considered outdated.'
)
__age_args.add_argument(
  '--tick-plus',
  type=float, help='How many hours to add to last tick time to use as max age.'
)

__datasource = __parser.add_mutually_exclusive_group(required=True)
__datasource.add_argument(
  '--jsonfilename',
  help='Name of file containing elitebgs.app API output to process'
)
__datasource.add_argument(
  '--faction',
  help='Name of the Minor Faction to report on.'
)

# Selection of heuristics
__parser.add_argument(
  '--active-conflicts',
  action='store_true',
  help='Consider any system with a known conflict.'
)
__parser.add_argument(
  '--possible-losing-conflicts',
  action='store_true',
  help='Consider any system so old we could now be in a 0:3 conflict state.'
)
__parser.add_argument(
  '--danger-of-conflicts',
  action='store_true',
  help='Consider any system that could now be one tick away from a pending conflict.'
)

__spansh_sub = __parser.add_subparsers(
  title='Optional commands',
  description='Additional commands that may allow, or require, additional arguments.'
)
__spansh = __spansh_sub.add_parser(
  'spansh-route',
  help='Generate a spansh tourist route, requires additional arguments.'
)
__spansh.add_argument(
  '--range',
  type=float,
  required=True,
  help='Ship max jump range for routing'
)
__spansh.add_argument(
  '--start-system',
  type=str,
  required=True,
  help='Start system for tourist route'
)


args = __parser.parse_args()
if args.loglevel:
  level = getattr(logging, args.loglevel.upper())
  logger.setLevel(level)
  __logger_ch.setLevel(level)


def main() -> int:  # noqa: CCR001
  """
  Handle program invocation.

  :returns: Exit code.
  """
  db = ed_bgs.Database(config['database']['url'], logger)
  ebgs = ed_bgs.EliteBGS(logger, db)
  bgs = ed_bgs.BGS(logger, db, ebgs)

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
    return -1

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
        # print(f'{s["system_name"]:30} {updated}')
        tourist_systems.append(s['system_name'])

  elif args.faction:
    logger.info('Using current local data ...')

    faction_id = db.faction_id_from_name(args.faction)
    if faction_id is None:
      logger.error(f'Unknown faction: {args.faction} - CASE MATTERS!')
      return -3

    if args.active_conflicts:
      logger.info('Checking for stale systems with known active conflicts...')
      tourist_systems.extend(bgs.active_conflicts_needing_update(faction_id, since))

    if args.possible_losing_conflicts:
      logger.info('Checking for stale systems with possible losing active conflicts...')
      tourist_systems.extend(bgs.possible_losing_conflicts(since, faction_id=faction_id, tick_plus=args.tick_plus))

    # Anywhere that was last seen with 'close' inf% to another MF and not
    # updated this tick.
    if args.danger_of_conflicts:
      logger.info('Checking for stale systems with possible active conflicts...')
      tourist_systems.extend(bgs.stale_danger_of_conflicts(since, faction_id))

  else:
    logger.error("No data source was specified?")
    return -1

  # De-dupe tourist_systems
  tourist_systems = list(set(tourist_systems))

  if len(tourist_systems) > 0:
    if hasattr(args, 'range') and hasattr(args, 'start_system'):
      spansh = ed_bgs.Spansh(logger)
      route_url = spansh.tourist_route(args.start_system, args.range, tourist_systems, False)
      print(route_url)

    else:
      print('\n\nSystems to be updated:')
      for s in tourist_systems:
        print(s)

  else:
    logger.info('No systems to update!')
    return 1

  return 0


if __name__ == '__main__':
  sys.exit(main())
