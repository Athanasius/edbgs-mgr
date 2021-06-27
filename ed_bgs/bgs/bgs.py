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
    :param faction_id: Optional faction to filter systems for presence.
    :returns: list of system names.
    """
    # How many days could a system go until we could *just* pull back a
    # conflict we're losing?
    #
    # Days Ago   State        (Tick) Time  Applicable Tick
    #       0    ?            08:42        0 (assuming update after)
    #       1    0:3          23:00        1
    #       2    0:2          22:55        2
    #       3    0:1          22:57        3
    #       4    0:0          23:05        4
    #       5    pending      22:50        5
    #       6    <none/other> 22:45        6
    ticks = self.ebgs.ticks_since(datetime.now(tz=timezone.utc) - timedelta(days=7))
    # Older than the oldest possible pending is what we want
    since = ticks[5]

    systems = self.db.systems_older_than(since + timedelta(hours=tick_plus), faction_id=faction_id)
    to_update = []
    for s in systems:
      logger.debug(f'Adding system because faction could now be losing 0:3 in unknown conflict: {s.name}')
      to_update.append(s.name)

    return to_update

  def stale_danger_of_conflicts(self, since: datetime, faction_id: int) -> list:
    """
    Determine systems with data stale enough to be in danger of a conflict.

    :param faction_id: Our DB id of the faction of interest.
    :param since: `datetime.datetime` of newest data that's OK.
    :returns: list of system names.
    """
    # What we'll return
    to_update = []

    # Need to consider every system the given faction is in that doesn't have
    # data since the given time (likely last tick plus 'fuzz').
    systems = self.db.systems_older_than(since, faction_id=faction_id)

    # The systems are sorted in ascending (oldest first) last_updated order,
    # thus the first one has the oldest data.  So use that to get ticks *once*
    # for use in the loop below.
    ticks = self.ebgs.ticks_since(systems[0].last_updated.astimezone(tz=timezone.utc))

    # Now for each of those systems
    for s in systems:
      # How many ticks since this system was update ?
      oldest_updated = s.last_updated.astimezone(tz=timezone.utc)
      ticks_since = self.ticks_since(ticks, oldest_updated)

      # We need the inf% of all the factions in that system
      factions = self.db.system_factions_data(s.systemaddress)
      f_faction = next(filter(lambda f: f.faction_id == faction_id, factions))
      if f_faction.influence < 7.0:
        # If interest-faction is below 7% ? it can't get into conflicts.
        break

      # Now to check if the faction of interest could now be in a conflict.
      prev = None
      # XXX: Actually *worst* case is if *any* of the other factions could
      #      have been brought up to match the faction of interest.
      for f in factions:
        if f.faction_id == faction_id:
          f_faction = f

          if prev is not None:
            # Are we too close to this faction, given the ticks that have passed ?
            # This is a *very* rough guesstimate of how much the other faction's
            # influence could have increased.  It could be more than 5% if
            # they started very low, or much less if they started higher.
            # Ref: <https://forums.frontier.co.uk/threads/influence-caps-gains-and-the-wine-analogy.423837/>
            # Ref: <https://forums.frontier.co.uk/threads/influence-caps-gains-and-the-wine-analogy.423837/page-6#post-8319830>
            possible_prev_inf = prev.influence + ticks_since * 5.0
            if abs(f_faction.influence - possible_prev_inf) < 5.0:
              self.logger.debug(f"""System '{s.name}' ({s.systemaddress})
Previous Faction: {prev.faction_id} - {prev.influence}
Interest Faction: {f_faction.faction_id} - {f_faction.influence}
""")
              to_update.append(s)
              break

        else:
          if prev is not None:
            if f_faction is not None and prev == f_faction:
              # Are we too close to this faction, given the ticks that have passed ?
              possible_prev_inf = prev.influence + len(ticks) * 5.0
              if abs(f.influence - possible_prev_inf) < 5.0:
                to_update.append(s)
                break

        prev = f

    return [s.name for s in to_update]

  def ticks_since(self, ticks: list, since: datetime) -> int:
    """
    Determine how many ticks there have been since the given timestamp.

    :param ticks: The list of ticks from elitebgs.app API.
    :param since: `datetime.datetime` of start point.
    """
    t = 0
    while t < len(ticks) and ticks[t] > since:
      t += 1

    return t

  def influence_could_be(self, influence: float, ticks: int) -> float:
    """
    Estimate the highest influence that could result from `ticks` ticks.

    :param influence: The starting influence.
    :param ticks: How many ticks to progress.
    :returns float: The projected max influence.
    """
    for t in range(ticks):
      influence += 5.0

    return influence
