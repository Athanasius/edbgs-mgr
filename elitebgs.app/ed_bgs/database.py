from sqlalchemy import create_engine, desc, exc, event, select
from sqlalchemy import MetaData, Table
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Column, BigInteger, Boolean, Float, Integer, Text, text
from sqlalchemy.sql.sqltypes import TIMESTAMP

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
    factions = Table('factions', self.metadata,
      Column('id', Integer, primary_key=True),
      Column('name', Text, index=True),
    )
    systems = Table('systems', self.metadata,
      Column('id', Integer, primary_key=True),
      Column('name', Text, index=True),
      Column('systemaddress', BigInteger, index=True),
      Column('starpos_x', Float, default=None),
      Column('starpos_y', Float, default=None),
      Column('starpos_z', Float, default=None),
      Column('system_allegiance', Text, default=None),
      Column('system_economy', Text, default=None),
      Column('system_second_economy', Text, default=None),
      Column('system_faction', Text, default=None),
      Column('system_government', Text, default=None),
      Column('system_security', Text, default=None),
    )
    ######################################################################

    self.metadata.create_all(self.engine)

