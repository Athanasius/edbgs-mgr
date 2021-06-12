import sqlalchemy
from sqlalchemy import create_engine, func
from sqlalchemy import MetaData, Table
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import insert
# from sqlalchemy.orm import Session
# SQLAlchemy Column types
from sqlalchemy import (
  Column, BigInteger, Boolean, DateTime, FetchedValue, Float, ForeignKey, Integer, Sequence, Text, Sequence, Text,
)
#  from sqlalchemy.sql.sqltypes import TIMESTAMP
from typing import Optional

#########################################################################
# Our base class for database operations
###########################################################################
class database(object):
  """Class for all database access."""

  def __init__(self, url: str, logger):
    self.logger = logger

    self.engine = create_engine(url)

    self.metadata = MetaData()
    ######################################################################
    # Table definitions
    self.factions_id_seq = Sequence('factions_id_seq', metadata=self.metadata)
    self.factions = Table('factions', self.metadata,
      Column('name', Text, primary_key=True),
      Column('id', Integer, self.factions_id_seq,
        server_default=self.factions_id_seq.next_value(), index=True,
        unique=True
      ),
      Column(
        'created', DateTime,
        server_default=func.now()
      ),
    )

    self.systems = Table('systems', self.metadata,
      Column('systemaddress', BigInteger, primary_key=True),
      Column('name', Text, index=True),
      Column('starpos_x', Float, default=None),
      Column('starpos_y', Float, default=None),
      Column('starpos_z', Float, default=None),
      Column('system_allegiance', Text, default=None),
      Column('system_economy', Text, default=None),
      Column('system_secondary_economy', Text, default=None),
      Column('system_controlling_faction', Integer,
        ForeignKey('factions.id'), nullable=False, index=True,
      ),
      Column('system_government', Text, default=None),
      Column('system_security', Text, default=None),
    )

    self.faction_presence = Table('faction_presences', self.metadata,
      Column('faction_id', Integer,
        ForeignKey('factions.id'), nullable=False, index=True,
      ),
      Column('systemaddress', BigInteger,
        ForeignKey('systems.systemaddress'), nullable=False, index=True,
      ),
      Column('state', Text, index=True),
      Column('influence', Float, index=True),
      Column('happiness', Text),
    )

    # active states
    self.faction_active_states = Table('faction_active_states', self.metadata,
      Column('faction_id', Integer,
        ForeignKey('factions.id'), nullable=False, index=True,
      ),
      Column('systemaddress', BigInteger,
        ForeignKey('systems.systemaddress'), nullable=False, index=True,
      ),
      Column('state', Text, nullable=False),
    )
    # pending states
    self.faction_pending_states = Table('faction_pending_states', self.metadata,
      Column('faction_id', Integer,
        ForeignKey('factions.id'), nullable=False, index=True,
      ),
      Column('systemaddress', BigInteger,
        ForeignKey('systems.systemaddress'), nullable=False, index=True,
      ),
      Column('state', Text, nullable=False),
      Column('trend', Integer),
    )
    # recovering states
    self.faction_recovering_states = Table('faction_recovering_states', self.metadata,
      Column('faction_id', Integer,
        ForeignKey('factions.id'), nullable=False, index=True,
      ),
      Column('systemaddress', BigInteger,
        ForeignKey('systems.systemaddress'), nullable=False, index=True,
      ),
      Column('state', Text, nullable=False),
      Column('trend', Integer),
    )

    self.conflicts_id_seq = Sequence('conflicts_id_seq', metadata=self.metadata)
    self.conflicts = Table('conflicts', self.metadata,
      Column(
        'id', Integer, self.conflicts_id_seq,
        server_default=self.conflicts_id_seq.next_value(), primary_key=True,
      ),
      Column(
        'systemaddress', BigInteger,
         ForeignKey('systems.systemaddress'), nullable=False
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
        'faction_id', Integer,
         ForeignKey('factions.id'), nullable=False
      ),
      Column(
        'opponent_faction_id', Integer,
         ForeignKey('factions.id'), nullable=False
      ),
      Column(
        'won_days', Integer,
        server_default='0'
      ),
      Column(
        'lost_days', Integer,
        server_default='0'
      ),
      Column(
        'status', Text,
      ),
      Column(
        'type', Text,
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
