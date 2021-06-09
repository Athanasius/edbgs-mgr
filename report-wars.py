#!/usr/bin/env python3

import argparse
import logging
import os
import time
import yaml

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
args = __parser.parse_args()
if args.loglevel:
  level = getattr(logging, args.loglevel.upper())
  logger.setLevel(level)
  __logger_ch.setLevel(level)


def main():
  """Handle program invocation."""
  logger.info('Initialising Database Connection')
  db = ed_bgs.database(config['database']['url'], logger)

  ebgs = ed_bgs.EliteBGS(logger, db)
  # return None
  # Looping over monitored factions
  for f in config['monitor_factions']:
    logger.info(f'Checking faction: {f}')
    # Fetch elitebgs.app data for this faction
    faction = ebgs.faction(f)
    # For each system with a conflict, fetch the system as well
    # Record(/update?) the state of each conflict

if __name__ == '__main__':
  main()
