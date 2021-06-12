"""
Mediate access to the API provided by https://elitebgs.app/

See: https://elitebgs.app/ebgs/docs/V5/
"""

import json
import requests

class EliteBGS:
  """Access to the elitebgs.app API."""
  FACTIONS_URL = 'https://elitebgs.app/api/ebgs/v5/factions'
  SYSTEMS_URL = 'https://elitebgs.app/api/ebgs/v5/systems'

  def __init__(self, logger, db):
    """
    Initialise access to elitebgs.app API.

    :param logger: `logging.Logger` instance.
    :param db: `ed_bgs.database` instance.
    """
    self.logger = logger
    self.db = db

    self.session = requests.Session()

  def faction(self, faction_name: str):
    """
    Retrieve, and store, available data about the specified faction.

    :param faction_name:
    :returns:
    """
    try:
      r = self.session.get(
        f'{self.FACTIONS_URL}?name={faction_name}'
      )

    except requests.exceptions.HTTPError as e:
      self.logger.warning(f'Error retrieving faction {faction_name}: {e!r}')
      return None

    # print(r.content.decode())

    try:
      data = r.json()
      f = data['docs'][0]

    except json.JSONDecodeError as e:
      self.logger.warning(f'Error decoding JSON for faction {faction_name}: {e!r}')
      return None

    faction_id = self.db.record_faction(f['name'])
    self.logger.info(f'{faction_name} is id "{faction_id}"')

    for s in f['faction_presence']:
      s_data = self.system(s['system_name'])
      # This will contain the other side of any conflict we're involved in.

  def faction_name_only(self, faction_name: str):
    """
    Ensure a faction name is in the database.

    :param faction_name:
    :returns:
    """
    faction_id = self.db.record_faction(f['name'])
    self.logger.info(f'{faction_name} is id "{faction_id}"')

  def system(self, system_name: str):
    """
    Retrieve, and store, available data about the specified system.

    :param system_name: System to query.
    :returns: The system 'document'.
    """
    try:
      r = self.session.get(
        f'{self.SYSTEMS_URL}?name={system_name}'
      )

    except requests.exceptions.HTTPError as e:
      self.logger.warning(f'Error retrieving system {system_name}: {e!r}')
      return None

    # print(r.content.decode())

    try:
      data = r.json()
      system_data = data['docs'][0]

    except json.JSONDecodeError as e:
      self.logger.warning(f'Error decoding JSON for system {system_name}: {e!r}')
      return None

    # Record any conflicts data
    for c in system_data.get('conflicts', []):
      for f in ('faction1', 'faction2'):
        # The faction names must exist in our DB
        faction_id = self.db.record_faction(c[f]['name'])
        self.logger.debug(f'Recorded conflict faction {c[f]["name"]} under id {faction_id}')
        
      # Now ensure this conflict is in our DB
      conflict_id = self.db.record_conflict(c)

    # Record the controlling faction
    controlling_faction_id = self.db.record_faction(system_data['controlling_minor_faction_cased'])
    self.logger.debug(f'Recorded controlling faction {system_data["controlling_minor_faction_cased"]} under id {controlling_faction_id}')

    system_db = {
      'systemaddress':              system_data['system_address'],
      'name':                       system_data['name'],
      'starpos_x':                  system_data['x'],
      'starpos_y':                  system_data['y'],
      'starpos_z':                  system_data['z'],
      'system_allegiance':          system_data['allegiance'],
      'system_economy':             system_data['primary_economy'],
      'system_secondary_economy':   system_data['secondary_economy'],
      'system_controlling_faction': controlling_faction_id,
      'system_government':          system_data['government'],
      'system_security':            system_data['security'],
    }
    system = self.db.record_system(system_db)

    return system
