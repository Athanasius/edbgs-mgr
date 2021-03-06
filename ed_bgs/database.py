"""Database handling functionality."""
import datetime
#  from sqlalchemy.sql.sqltypes import TIMESTAMP
from typing import TYPE_CHECKING, Optional

import sqlalchemy
# from sqlalchemy.orm import Session
# SQLAlchemy Column types
from sqlalchemy import (BigInteger, Column, DateTime, FetchedValue, Float, ForeignKey, Integer, MetaData, Sequence,
                        Table, Text, UniqueConstraint, create_engine, delete, func, or_)
from sqlalchemy.dialects.postgresql import insert

# isort off
if TYPE_CHECKING:
  import logging


#########################################################################
# Our base class for database operations
###########################################################################
class Database(object):
  """Class for all database access."""

  def __init__(self, url: str, logger: 'logging.Logger'):
    self.logger = logger

    self.engine = create_engine(url)

    self.metadata = MetaData()
    ######################################################################
    # Table definitions
    self.factions_id_seq = Sequence('factions_id_seq', metadata=self.metadata)
    self.factions = Table(
      'factions', self.metadata,
      Column('name', Text, primary_key=True),
      Column(
        'id', Integer, self.factions_id_seq,
        server_default=self.factions_id_seq.next_value(), index=True,
        unique=True
      ),
      Column(
        'created', DateTime,
        server_default=func.now()
      ),
    )

    self.systems = Table(
      'systems', self.metadata,
      Column('systemaddress', BigInteger, primary_key=True),
      Column('name', Text, index=True),
      Column('starpos_x', Float, default=None),
      Column('starpos_y', Float, default=None),
      Column('starpos_z', Float, default=None),
      Column('system_allegiance', Text, default=None),
      Column('system_economy', Text, default=None),
      Column('system_secondary_economy', Text, default=None),
      Column(
        'system_controlling_faction', Integer,
        ForeignKey('factions.id'), nullable=False, index=True,
      ),
      Column('system_government', Text, default=None),
      Column('system_security', Text, default=None),
      Column(
        'last_updated', DateTime,
        server_default=func.now(),
        server_onupdate=FetchedValue()
      ),
    )

    self.factions_presences = Table(
      'factions_presences', self.metadata,
      Column(
        'faction_id', Integer,
        ForeignKey('factions.id', ondelete='CASCADE'), nullable=False, index=True,
      ),
      Column(
        'systemaddress', BigInteger,
        ForeignKey('systems.systemaddress', ondelete='CASCADE'), nullable=False, index=True,
      ),
      Column('state', Text, index=True),
      Column('influence', Float, index=True),
      Column('happiness', Text),
      UniqueConstraint(
        'faction_id',
        'systemaddress',
        name='factions_presences_constraint',
      ),
    )

    # active states
    self.factions_active_states = Table(
      'factions_active_states', self.metadata,
      Column(
        'faction_id', Integer,
        ForeignKey('factions.id', ondelete='CASCADE'), nullable=False, index=True,
      ),
      Column(
        'systemaddress', BigInteger,
        ForeignKey('systems.systemaddress', ondelete='CASCADE'), nullable=False, index=True,
      ),
      Column('state', Text, nullable=False),
    )
    # pending states
    self.factions_pending_states = Table(
      'factions_pending_states', self.metadata,
      Column(
        'faction_id', Integer,
        ForeignKey('factions.id', ondelete='CASCADE'), nullable=False, index=True,
      ),
      Column(
        'systemaddress', BigInteger,
        ForeignKey('systems.systemaddress', ondelete='CASCADE'), nullable=False, index=True,
      ),
      Column('state', Text, nullable=False),
      Column('trend', Integer),
    )
    # recovering states
    self.factions_recovering_states = Table(
      'factions_recovering_states', self.metadata,
      Column(
        'faction_id', Integer,
        ForeignKey('factions.id', ondelete='CASCADE'), nullable=False, index=True,
      ),
      Column(
        'systemaddress', BigInteger,
        ForeignKey('systems.systemaddress', ondelete='CASCADE'), nullable=False, index=True,
      ),
      Column('state', Text, nullable=False),
      Column('trend', Integer),
    )

    self.conflicts_id_seq = Sequence('conflicts_id_seq', metadata=self.metadata)
    self.conflicts = Table(
      'conflicts', self.metadata,
      Column(
        'id', Integer, self.conflicts_id_seq,
        server_default=self.conflicts_id_seq.next_value(), primary_key=True,
      ),
      Column(
        'systemaddress', BigInteger,
        ForeignKey('systems.systemaddress', ondelete='CASCADE'), nullable=False
      ),
      Column(
        'created', DateTime,
        server_default=func.now()
      ),
      Column(
        'last_updated', DateTime,
        server_default=func.now(),
        server_onupdate=FetchedValue()
      ),
      Column(
        'faction1_id', Integer,
        ForeignKey('factions.id', ondelete='CASCADE'), nullable=False
      ),
      Column(
        'faction2_id', Integer,
        ForeignKey('factions.id', ondelete='CASCADE'), nullable=False
      ),
      Column(
        'faction1_days_won', Integer,
        server_default='0'
      ),
      Column(
        'faction2_days_won', Integer,
        server_default='0'
      ),
      # faction1_stake, faction2_stake
      Column(
        'status', Text,
      ),
      Column(
        'conflict_type', Text,
      ),
      UniqueConstraint(
        'systemaddress',
        'faction1_id',
        'faction2_id',
        # TODO: We might want to have history eventually, add created ?
        name='conflicts_constraint',
      ),
    )

    self.factions_conflicts = Table(
      'factions_conflicts', self.metadata,
      Column(
        'faction_id', Integer,
        ForeignKey('factions.id', ondelete='CASCADE'), nullable=False
      ),
      Column(
        'conflict_id', Integer,
        ForeignKey('conflicts.id', ondelete='CASCADE'), nullable=False
      ),
      UniqueConstraint(
        'faction_id',
        'conflict_id',
        name='factions_conflicts_constraint',
      ),
    )
    ######################################################################

    self.metadata.create_all(self.engine)

  def record_faction(self, faction_name: str) -> Optional[int]:
    """
    Record the given faction name in the database.

    :param faction_name:
    :returns: id of the faction
    """
    # Attempt to INSERT
    with self.engine.connect() as conn:
      stmt = self.factions.insert().values(
        name=faction_name
      )

      try:
        result = conn.execute(stmt)

      except sqlalchemy.exc.IntegrityError:
        # Assume already present
        pass

    # Retrieve the `id` value for this faction
    with self.engine.connect() as conn:
      stmt = self.factions.select().where(self.factions.c.name == faction_name)
      result = conn.execute(stmt)
      return result.first()._mapping['id']

    return None

  def record_factions_presences(self, system_id: int, factions: dict) -> None:
    """
    Record data for given faction in a specific system.

    :param system_id: System id.
    :param data: Array of faction data dicts.
    """
    with self.engine.begin() as conn:
      # First remove all factions from the given system so we take note of
      # retreats.
      stmt = delete(self.factions_presences).where(
        self.factions_presences.c.systemaddress == system_id
      )
      conn.execute(stmt)
      # self.logger.debug(f'{result.rowcount} factions deleted from {system_id}')

      # Now add the ones currently known to be in that system.
      for f in factions:
        stmt = insert(self.factions_presences).values(f)

        # self.logger.debug(f'Statement:\n{str(stmt)}\n')
        conn.execute(stmt)

  def record_faction_presence(self, faction_id: int, data: dict) -> None:
    """
    Record data for given faction in a specific system.

    Deprecated: Update the entire system with `record_factions_presences()`
                instead.

    :param faction_id: Our DB id for the faction.
    :param data: `dict` of the data
    """
    data['faction_id'] = faction_id
    with self.engine.connect() as conn:
      stmt = insert(self.factions_presences).values(
        data
      ).on_conflict_do_update(
        constraint='factions_presences_constraint',
        set_=data
      )

      try:
        conn.execute(stmt)

      except sqlalchemy.exc.IntegrityError:
        # Assume already present
        self.logger.error('IntegrityError inserting faction presence data')
        return None

  def record_system(self, system_data: dict) -> Optional[int]:
    """
    Record the given system data in the database.

    :param system_data: `dict` with key:value per database column.
    :returns: The database data for that system.
    """
    # Attempt to INSERT
    with self.engine.connect() as conn:
      stmt = insert(self.systems).values(
        systemaddress=system_data['systemaddress'],
        name=system_data['name'],
        starpos_x=system_data['starpos_x'],
        starpos_y=system_data['starpos_y'],
        starpos_z=system_data['starpos_z'],
        system_allegiance=system_data['system_allegiance'],
        system_economy=system_data['system_economy'],
        system_secondary_economy=system_data['system_secondary_economy'],
        system_controlling_faction=system_data['system_controlling_faction'],
        system_government=system_data['system_government'],
        system_security=system_data['system_security'],
        last_updated=system_data['last_updated'],
      ).on_conflict_do_update(
        constraint='systems_pkey',
        set_=system_data
      )

      try:
        result = conn.execute(stmt)

      except sqlalchemy.exc.IntegrityError:
        # Assume already present
        self.logger.error('IntegrityError inserting system data')
        return None

    # Retrieve the `id` value for this system
    with self.engine.connect() as conn:
      stmt = self.systems.select().where(self.systems.c.systemaddress == system_data['systemaddress'])
      result = conn.execute(stmt)
      return result.first()

    return None

  def record_faction_active_states(self, faction_id: int, system_id: int, states: list) -> None:
    """
    Update database for these to be the active states of the given faction.

    :param faction_id: Our DB id of the faction.
    :param system_id: The system if this is for.
    :param states: List of currently active states.
    """
    # We need a transaction for this
    with self.engine.begin() as conn:
      # First clear all the states for this (faction, system) tuple
      conn.execute(
        delete(self.factions_active_states).where(
          self.factions_active_states.c.faction_id == faction_id
        ).where(
          self.factions_active_states.c.systemaddress == system_id
        )
      )
      # Now add in all of the specified ones.
      for a_state in states:
        conn.execute(
          insert(self.factions_active_states).values(
            faction_id=faction_id,
            systemaddress=system_id,
            state=a_state,
          )
        )

  def record_faction_pending_states(self, faction_id: int, system_id: int, states: list) -> None:
    """
    Update database for these to be the pending states of the given faction.

    :param faction_id: Our DB id of the faction.
    :param system_id: The system if this is for.
    :param states: List of currently pending states.
    """
    # We need a transaction for this
    with self.engine.begin() as conn:
      # First clear all the states for this (faction, system) tuple
      conn.execute(
        delete(self.factions_pending_states).where(
          self.factions_pending_states.c.faction_id == faction_id
        ).where(
          self.factions_pending_states.c.systemaddress == system_id
        )
      )
      # Now add in all of the specified ones.
      for a_state in states:
        conn.execute(
          insert(self.factions_pending_states).values(
            faction_id=faction_id,
            systemaddress=system_id,
            state=a_state,
          )
        )

  def record_faction_recovering_states(self, faction_id: int, system_id: int, states: list) -> None:
    """
    Update database for these to be the recovering states of the given faction.

    :param faction_id: Our DB id of the faction.
    :param system_id: The system if this is for.
    :param states: List of currently recovering states.
    """
    # We need a transaction for this
    with self.engine.begin() as conn:
      # First clear all the states for this (faction, system) tuple
      conn.execute(
        delete(self.factions_recovering_states).where(
          self.factions_recovering_states.c.faction_id == faction_id
        ).where(
          self.factions_recovering_states.c.systemaddress == system_id
        )
      )
      # Now add in all of the specified ones.
      for a_state in states:
        conn.execute(
          insert(self.factions_recovering_states).values(
            faction_id=faction_id,
            systemaddress=system_id,
            state=a_state,
          )
        )

  def record_conflict(self, system_id: int, last_updated: str, conflict: dict) -> None:
    """
    Record current state of a conflict for the faction in a system.

    :param system_id: The system if this is for.
    :param last_updated: `str` - from elitebgs.app API systems data.
    :param conflict: `dict` of conflict data from elitebgs.app API.
    """
    with self.engine.begin() as conn:
      # We need the two factions to always be in the same order otherwise
      # the unique constraint won't always work.
      if conflict['faction1']['name'] > conflict['faction2']['name']:
        f = conflict['faction2'].copy()
        conflict['faction2'] = conflict['faction1'].copy()
        conflict['faction1'] = f

      faction1_id = self.record_faction(conflict['faction1']['name'])
      faction2_id = self.record_faction(conflict['faction2']['name'])

      # Insert or update data for this conflict
      data = {
        'systemaddress': system_id,
        'faction1_id': faction1_id,
        'faction2_id': faction2_id,
        'faction1_days_won': conflict['faction1']['days_won'],
        'faction2_days_won': conflict['faction2']['days_won'],
        'status': conflict['status'],
        'conflict_type': conflict['type'],
        'last_updated': last_updated,
      }
      stmt = insert(self.conflicts).values(
        data
      ).on_conflict_do_update(
        constraint='conflicts_constraint',
        set_=data
      )

      try:
        result = conn.execute(stmt)
        conflict_id = result.inserted_primary_key[0]

      except sqlalchemy.exc.IntegrityError:
        # Assume already present
        self.logger.error('IntegrityError inserting conflict data')
        return None

      # Update the factions_conflicts table as well.
      self.record_faction_conflict(conn, faction1_id, conflict_id)
      self.record_faction_conflict(conn, faction2_id, conflict_id)

  def record_faction_conflict(
    self,
    conn: sqlalchemy.engine.base.Connection,
    faction_id: Optional[int],
    conflict_id: Optional[int]
  ) -> None:
    """
    Record a conflict a faction is involved in.

    :param conn: DB connection - we might be called within a transaction.
    :param faction_id: Our DB id for the faction.
    :param conflict_id: Our DB id for this conflict.
    """
    stmt = insert(self.factions_conflicts).values(
      faction_id=faction_id,
      conflict_id=conflict_id,
    ).on_conflict_do_nothing()

    try:
      conn.execute(stmt)

    except sqlalchemy.exc.IntegrityError:
      # Assume it was already recorded
      pass

  def faction_id_from_name(self, faction_name: str) -> Optional[int]:
    """Fetch our faction_id for the named faction.

    :param faction_name: `str` - faction of interest.
    :returns: `int` - Our DB ID for this faction.
    """
    with self.engine.connect() as conn:
      stmt = self.factions.select(
      ).where(
        self.factions.c.name == faction_name
      )

      result = conn.execute(stmt)

      if result.rowcount != 1:
        return None

      return result.first()['id']

  def expire_conflicts(self) -> int:
    """Remove data for any conflicts that have expired."""
    # For every conflict we know
    #  Expire if in cooldown and older than a day.
    #  Anything else just needs updated data.
    one_day_ago = datetime.datetime.utcnow() - datetime.timedelta(days=1)
    with self.engine.begin() as conn:
      stmt = delete(self.conflicts).where(
        self.conflicts.c.status == ''
      ).where(
        self.conflicts.c.last_updated < one_day_ago
      )

      result = conn.execute(stmt)

      return result.rowcount

  def systems_older_than(self, since: datetime.datetime, faction_id: int = None) -> list:
    """
    Return a list of systems with latest data older than specified.

    :param since: `datetime` of oldest data to not need updating.
    :param faction_id: Optional faction to filter systems for presence.
    :returns: `list` of system rows, in ascending last_updated order.
    """
    # self.logger.debug(f'Finding systems older than {since}')
    systems = []

    with self.engine.connect() as conn:
      stmt = self.systems.select()

      if faction_id is not None:
        stmt = stmt.where(
          self.systems.c.systemaddress.in_(
            self.factions_presences.select(
            ).with_only_columns(
              self.factions_presences.c.systemaddress
            ).where(
              self.factions_presences.c.faction_id == faction_id
            )
          )
        )

      stmt = stmt.where(
        self.systems.c.last_updated < since
      ).order_by(
        self.systems.c.last_updated.asc()
      )

      # self.logger.debug(f'Statement:\n{str(stmt)}\n')
      result = conn.execute(stmt)
      for r in result.fetchall():
        systems.append(r)

    return systems

  def systems_conflicts_older_than(self, since: datetime.datetime, faction_id: int = None) -> list:
    """
    Return a list of systems with conflicts with data older than specified.

    :param since: `datetime` of oldest data to not need updating.
    :param faction_id: Faction ID to limit involved to, if specified.
    :returns: `list` of system rows
    """
    systems = []

    with self.engine.connect() as conn:
      # SELECT name FROM systems
      #  WHERE systemaddress IN
      #   (SELECT systemaddress FROM conflicts WHERE ( faction1_id = 1 OR faction2_id = 1 )
      #  AND status != '' AND last_updated < TIMESTAMP '2021-06-24 23:22:00Z');
      inner_stmt = self.conflicts.select(
      ).with_only_columns(
        self.conflicts.c.systemaddress
      ).where(
        self.conflicts.c.last_updated < since
      ).where(
        self.conflicts.c.status != ''
      )

      if faction_id is not None:
        inner_stmt = inner_stmt.where(
          or_(
            self.conflicts.c.faction1_id == faction_id,
            self.conflicts.c.faction2_id == faction_id
          )
        )

      # self.logger.debug(f'Statement:\n{str(inner_stmt)}\n')

      stmt = self.systems.select(
      ).with_only_columns(
        self.systems.c.name
      ).where(
        self.systems.c.systemaddress.in_(
          inner_stmt
        )
      )
      # self.logger.debug(f'Statement:\n{str(stmt)}\n')

      result = conn.execute(stmt)
      for r in result.fetchall():
        systems.append(r)

    return systems

  def system_factions_data(self, systemaddress: int) -> list:
    """
    Accumulate all the per-faction data for the given system.

    :param systemaddress: ID of the system.
    :returns: ???
    """
    with self.engine.connect() as conn:
      stmt = self.factions_presences.select(
      ).where(
        self.factions_presences.c.systemaddress == systemaddress
      ).order_by(
        self.factions_presences.c.influence.asc()
      )

      # self.logger.debug(f'Statement:\n{str(stmt)}\n')
      return conn.execute(stmt).all()
