"""
Functionality related to operating on BGS data.

Includes heuristics and the like.
"""
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

# isort off
if TYPE_CHECKING:
  import logging

  import ed_bgs.database as database
  import ed_bgs.elitebgs_app.elitebgs as elitebgs
# isort on


class BGS:
  """Container class for BGS related functions."""

  def __init__(self, logger: 'logging.Logger', db: 'database.Database', ebgs: 'elitebgs.EliteBGS'):
    """Initilised the BGS class instance."""
    self.logger = logger
    self.db = db
    self.ebgs = ebgs

  def systems_outdated(self, faction_id: int, since: datetime) -> list:
    """
    Determine all systems the given faction is known in, in need of update.

    :param faction_id: Our DB id of the faction of interest.
    :param since: `datetime.datetime` of newest data that's OK.
    :returns: list of system names.
    """
    systems = self.db.systems_older_than(since, faction_id=faction_id)
    return [s.name for s in systems]

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

  def possible_losing_conflicts(self, since: datetime, tick_plus: float = 2.1, faction_id: int = None) -> list:
    """
    Determine systems that might now be in 0:3 losing state in need of new data.

    :param since: `datetime.datetime` time to compare against.
    :param tick_plus: How many hours to add to tick times to 'ensure' new data.
    :param faction_id: Optional faction to filter on.
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
    since = self.tick_time_x_ago(6)
    systems = self.db.systems_older_than(since + timedelta(hours=tick_plus), faction_id=faction_id)
    to_update = []
    for s in systems:
      self.logger.debug(f'Adding system because faction could now be losing 0:3 in unknown conflict: {s.name}')
      to_update.append(s.name)

    return to_update

  def stale_danger_of_conflicts(self, since: datetime, faction_id: int) -> list:  # noqa: CCR001
    """
    Determine systems with data stale enough to be in danger of a conflict.

    Assumptions:

      1. The target faction itself won't have changed in influence.

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
      self.logger.debug(f'Considering system:\n{s.name}')

      # How many ticks since this system was updated ?
      ticks_since = self.ticks_since(ticks, s.last_updated.astimezone(tz=timezone.utc))

      # We need the inf% of all the factions in that system
      factions = self.db.system_factions_data(s.systemaddress)

      # Find the data for the target faction
      f_faction = next(filter(lambda f: f.faction_id == faction_id, factions))

      if f_faction.influence < 0.07:
        # If interest-faction is below 7% ? it can't get into conflicts.
        break

      # Now to check if the faction of interest could now be in a conflict.
      for f in factions:
        danger = False

        if f.faction_id == faction_id:
          continue

        self.logger.debug(f'Considering faction:\n{f.faction_id}')

        if f.influence < f_faction.influence:
          # It's below 'us', so what *could* it be now ?
          # Need to step day by day in case of an overshoot.
          for t in range(1, ticks_since):
            possible_inf = self.influence_could_be(f.influence, t)
            if abs(f_faction.influence - possible_inf) < 0.05:
              danger = True
              break

        else:
          # It's above us, and we assume we don't grow.
          if abs(f_faction.influence - f.influence) < 0.05:
            danger = True

        if danger:
          self.logger.debug(f"""
System '{s.name}' ({s.systemaddress})
Interest Faction: {f_faction.faction_id} - {f_faction.influence}
This     Faction: {f.faction_id} - {f.influence}
""")
          to_update.append(s)
          break

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
    # This is a *very* rough guesstimate of how much the other faction's
    # influence could have increased.  It could be more than 5% if
    # they started very low, or much less if they started higher.
    # Ref: <https://forums.frontier.co.uk/threads/influence-caps-gains-and-the-wine-analogy.423837/>
    # Ref: <https://forums.frontier.co.uk/threads/influence-caps-gains-and-the-wine-analogy.423837/page-6#post-8319830>
    for t in range(ticks):
      influence += 0.05

    return influence

  def tick_time_x_ago(self, ticks_ago: int) -> datetime:
    """
    Determine the time of the tick X ticks ago.

    :param ticks_ago: How many ticks to look back.
    """
    # We want to go back to the tick *before*, so ticks_ago + 1
    ticks = self.ebgs.ticks_since(
      datetime.now(tz=timezone.utc)
      - timedelta(days=ticks_ago + 1)
    )

    days_ago = datetime.now(tz=timezone.utc) - timedelta(days=ticks_ago)
    tick_time = next(filter(lambda t: t < days_ago, ticks))

    return tick_time
