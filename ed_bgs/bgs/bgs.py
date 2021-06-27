"""
Functions related to operating on the BGS data, including heuristics and the
like.
"""

class BGS:
  """Container class for BGS related functions."""

  def __init__(self, logger, db):
    """Initilised the BGS class instance."""
    self.logger = logger
    self.db = db

  def active_conflicts_needing_update(self, faction_id, since) -> list:
    """
    Determine systems in need of data update due to active conflict.

    :param faction_id: Our DB id of the faction of interest.
    :param since: `datetime.datetime` of newest data that's OK.
    :returns: list of faction names.
    """
    # Anywhere we know there was a conflict already and not updated since
    # the last known tick + fuzz.
    systems = self.db.systems_conflicts_older_than(since, faction_id=faction_id)
    to_update = []
    for s in systems:
      self.logger.debug(f'Adding system because of on-going conflict: {s.name}')
      to_update.append(s.name)

    return to_update

  def possible_losing_conflicts(self, faction_id=None):
    """
    """
    ...
