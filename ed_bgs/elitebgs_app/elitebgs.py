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
    :returns: The elitebgs.app 'document' for the faction.
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

    faction_id = self.faction_name_only(faction_name)

    # First ensure all the presence data, particularly active/pending/recovering
    # states is recorded.
    for s in f['faction_presence']:
      # Ensure the system is in our database.
      s_data = self.system(s['system_name'])

      # Record any active states
      self.db.record_faction_active_states(faction_id, s_data['systemaddress'], [active['state'] for active in s.get('active_states', [])])
      # Record any pending states
      self.db.record_faction_pending_states(faction_id, s_data['systemaddress'], [pending['state'] for pending in s.get('pending_states', [])])
      # Record any recovering states
      self.db.record_faction_recovering_states(faction_id, s_data['systemaddress'], [recovering['state'] for recovering in s.get('recovering_states', [])])

      # Conflicts
      for c in s['conflicts']:
        # Ensure the opponent faction is known
        opponent_id = self.db.record_faction(c['opponent_name'])
        # Record these details of the conflict
        self.db.record_conflicts(faction_id, opponent_id, s_data['systemaddress'], c)

    return f

  def faction_in_system(self, faction_name: str, system_id: int, data: dict):
    """
    Store information about the given faction in the given system.

    :param faction_name: Name of the faction.
    :param system_id: Our DB id of the system.
    :param data: elitebgs.app API 'faction_presence' dict.
    """
    faction_id = self.faction_name_only(faction_name)

    set_data = {
      'systemaddress': system_id,
      'state': data['state'],
      'influence': data['influence'],
      'happiness': data['happiness'],
    }
    f = self.db.record_faction_presence(faction_id, set_data)

    return f

  def faction_name_only(self, faction_name: str):
    """
    Ensure a faction name is in the database.

    :param faction_name:
    :returns:
    """
    faction_id = self.db.record_faction(faction_name)
    self.logger.debug(f'{faction_name} is id "{faction_id}"')

    return faction_id

  def system(self, system_name: str):
    """
    Retrieve, and store, available data about the specified system.

    :param system_name: System to query.
    :returns: The system 'document'.
    """
    try:
      r = self.session.get(
        f'{self.SYSTEMS_URL}?name={system_name}&factionDetails=true'
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

    # Now we have the system, record *all* the factions present in it
    for f in system_data['factions']:
      self.faction_in_system(
        f['name'],
        system['systemaddress'],
        f['faction_details']['faction_presence'],
      )


    # TODO: Record the 'other' side of conflicts.
    #       The per-faction conflicts list only contains days_won, for
    #       days_lost we need the other faction's days_won from system data.
    return system

  def system_conflicts(self, data: dict):
    """Record any conflicts data."""
    for c in data.get('conflicts', []):
      for f in ('faction1', 'faction2'):
        # The faction names must exist in our DB
        faction_id = self.db.record_faction(c[f]['name'])
        self.logger.debug(f'Recorded conflict faction {c[f]["name"]} under id {faction_id}')
        
      # Now ensure this conflict is in our DB
      conflict_id = self.db.record_conflict(c)

