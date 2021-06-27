"""
Functions related to operating on the BGS data, including heuristics and the
like.
"""
from datetime import datetime, timedelta, timezone

class BGS:
  """Container class for BGS related functions."""

  def __init__(self, logger, db, ebgs):
    """Initilised the BGS class instance."""
    self.logger = logger
    self.db = db
    self.ebgs = ebgs

  def active_conflicts_needing_update(self, faction_id: int, since: datetime) -> list:
    """
    Determine systems in need of data update due to active conflict.

    :param faction_id: Our DB id of the faction of interest.
    :param since: `datetime.datetime` of newest data that's OK.
    :returns: list of system names.
    """
    # Anywhere we know there was a conflict already and not updated since
    # the last known tick + fuzz.
    systems = self.db.systems_conflicts_older_than(since, faction_id=faction_id)
    to_update = []
    for s in systems:
      self.logger.debug(f'Adding system because of on-going conflict: {s.name}')
      to_update.append(s.name)

    return to_update

  def possible_losing_conflicts(self, since: datetime, tick_plus: int = 2, faction_id: int = None) -> list:
    """
    Determine systems that might now be in 0:3 losing state in need of new data.

    :param faction_id: Optional faction to filter on.
    :returns: list of system names.
    """
    # How many days could a system go until we could *just* pull back a
    # conflict we're losing?
    #
    # Days Ago   State        (Tick) Time  Tick
    #       0    ?            08:42        0 (assuming update after)
    #       1    0:3          23:00        1
    #       2    0:2          22:55        2
    #       3    0:1          22:57        3
    #       4    0:0          23:05        4
    #       5    pending      22:50        5
    #       6    <none/other> 22:45        6
    ticks = self.ebgs.ticks_since(datetime.now(tz=timezone.utc) - timedelta(days=7))
    since = ticks[5]

    systems = self.db.systems_older_than(since + timedelta(hours=tick_plus))
    to_update = []
    for s in systems:
      logger.debug(f'Adding system because faction could now be losing 0:3 in unknown conflict: {s.name}')
      to_update.append(s.name)

    return to_update
