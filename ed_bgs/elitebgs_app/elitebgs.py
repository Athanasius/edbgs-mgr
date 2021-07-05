"""
Mediate access to the API provided by https://elitebgs.app/ .

See: https://elitebgs.app/ebgs/docs/V5/
"""

import datetime
import json
from typing import TYPE_CHECKING, Optional

import requests
from dateutil.parser import isoparse

# isort off
if TYPE_CHECKING:
  import logging

  import ed_bgs.database as database
# isort on


class EliteBGS:
  """Access to the elitebgs.app API."""

  FACTIONS_URL = 'https://elitebgs.app/api/ebgs/v5/factions'
  SYSTEMS_URL = 'https://elitebgs.app/api/ebgs/v5/systems'
  TICKS_URL = 'https://elitebgs.app/api/ebgs/v5/ticks'

  def __init__(self, logger: 'logging.Logger', db: 'database'):
    """
    Initialise access to elitebgs.app API.

    :param logger: `logging.Logger` instance.
    :param db: `ed_bgs.database` instance.
    """
    self.logger = logger
    self.db = db

    self.session = requests.Session()

  def faction(self, faction_name: str) -> Optional[dict]:
    """
    Retrieve, and store, available data about the specified faction.

    :param faction_name:
    :returns: The elitebgs.app 'document' for the faction.
    """
    self.logger.debug('Attempting to retrieve and store all data for {faction_name}')

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
      self.logger.debug(f'Faction "{faction_name}" - system "{s["system_name"]}"')

      # Ensure the system is in our database.
      s_data = self.system(s['system_name'])
      if s_data is None:
        # TODO: Should start using Exceptions for this
        return None

      # Record any active states
      self.db.record_faction_active_states(
        faction_id,
        s_data['system_address'],
        [active['state'] for active in s.get('active_states', [])]
      )
      # Record any pending states
      self.db.record_faction_pending_states(
        faction_id,
        s_data['system_address'],
        [pending['state'] for pending in s.get('pending_states', [])]
      )
      # Record any recovering states
      self.db.record_faction_recovering_states(
        faction_id,
        s_data['system_address'],
        [recovering['state'] for recovering in s.get('recovering_states', [])]
      )

      # Conflicts
      for c in s_data['conflicts']:
        # Record details of the conflict
        self.db.record_conflict(s_data['system_address'], s_data['updated_at'], c)

    return f

  def faction_in_system(self, faction_name: str, system_id: int, data: dict) -> None:
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
    self.db.record_faction_presence(faction_id, set_data)

  def factions_in_system(self, elitebgs_system_id: int, system_id: int, factions: dict) -> None:
    """
    Store information about the given faction in the given system.

    :param elitebgs_system_id: EliteBGS's id for the system.
    :param system_id: Our DB id of the system.
    :param factions: elitebgs.app system factions dictionary.
    """
    fs = []
    for f in factions:
      faction_id = self.faction_name_only(f['name'])

      # It should be a single dict, not a list of dicts.
      if isinstance(f['faction_details']['faction_presence'], list):
        self.logger.warning(f"A list was seen for {system_id}/{f['faction_details']['name']}!"
                            f"Aborting updating this system's factions!")
        return

      # And the EliteBGS system id should match what we asked for.
      if f['faction_details']['faction_presence']['system_id'] != elitebgs_system_id:
        self.logger.warning(f"faction_presence 'system_id' did not match the system's _id for "
                            f"{f['faction_details']['name']} in {system_id} !"
                            f"Aborting updating this system's factions!")
        return

      fs.append(
        {
          'faction_id': faction_id,
          'systemaddress': system_id,
          'state': f['faction_details']['faction_presence']['state'],
          'influence': f['faction_details']['faction_presence']['influence'],
          'happiness': f['faction_details']['faction_presence']['happiness'],
        }
      )

    self.db.record_factions_presences(system_id, fs)

  def faction_name_only(self, faction_name: str) -> int:
    """
    Ensure a faction name is in the database.

    :param faction_name: Name of faction to record.
    :returns:
    """
    faction_id = self.db.record_faction(faction_name)
    self.logger.debug(f'{faction_name} is id "{faction_id}"')

    return faction_id

  def system(self, system_name: str) -> Optional[dict]:
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
    # self.logger.debug(f'Recorded controlling faction {system_data["controlling_minor_faction_cased"]}'
    #                   f' under id {controlling_faction_id}')

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
      'last_updated':               system_data['updated_at'],
    }
    system = self.db.record_system(system_db)

    # Now we have the system, record *all* the factions present in it
    self.factions_in_system(
      system_data['_id'],
      system['systemaddress'],
      system_data['factions'],
    )

    return system_data

  def last_tick(self) -> Optional[datetime.datetime]:
    """
    Retrieve the time of the last declared tick.

    :returns: `datetime.datetime` of latest tick, on success, else `None`.
    """
    try:
      r = self.session.get(
        self.TICKS_URL,
      )

    except requests.exceptions.HTTPError as e:
      self.logger.warning(f'Error retrieving tick: {e!r}')
      return None

    try:
      data = r.json()

    except json.JSONDecodeError as e:
      self.logger.warning(f'Error decoding JSON for tick: {e!r}')
      return None

    # [{"_id":"60d266ede6bdf9696a4e0cc8","time":"2021-06-22T22:15:43.000Z","updated_at":"2021-06-22T22:40:45.726Z","__v":0}]
    self.logger.debug(f'Returning: isoparse("{data[0]["time"]}")')
    return isoparse(data[0]['time'])

  def ticks_since(self, since: datetime.datetime) -> Optional[list]:
    """
    Retrieve the ticks since given datetime.

    :param since: Oldest time of ticks to consider.
    :return: `list` of `datetime.datetime` on success, else `None`.
    """
    self.logger.debug(f'{since=}')
    timemin = int(since.timestamp()) * 1000
    url = f'{self.TICKS_URL}?timeMin={timemin}'
    try:
      r = self.session.get(
        url,
      )

    except requests.exceptions.HTTPError as e:
      self.logger.warning(f'Error retrieving ticks: {e!r}')
      return None

    try:
      data = r.json()

    except json.JSONDecodeError as e:
      self.logger.warning(f'Error decoding JSON for ticks: {e!r}')
      return None

    ticks = []
    for t in data:
      self.logger.debug(f'Including tick "{isoparse(t["time"])}"')
      ticks.append(isoparse(t['time']))

    # self.logger.debug(f'Returning ticks:\n{ticks}\n')
    return ticks
