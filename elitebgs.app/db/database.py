from sqlalchemy import create_engine, desc, exc, event, select
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
  	factions = Table(
      Column('id', Integer, autoincrement=True, primary_key=True),
	    Column('name', Text, index=True),
		)
    systems = Table(
      Column('id', self.metadata, Integer, autoincrement=True, primary_key=True),
	    Column('name', self.metadata, Text, index=True),
	    Column('systemaddress', self.metadata, BigInteger, index=True),
	    Column('starpos_x', self.metadata, Float, default=None),
	    Column('starpos_y', self.metadata, Float, default=None),
	    Column('starpos_z', self.metadata, Float, default=None),
      Column('system_allegiance', self.metadata, Text, default=None),
      Column('system_economy', self.metadata, Text, default=None),
      Column('system_second_economy', self.metadata, Text, default=None),
      Column('system_faction', self.metadata, Text, default=None),
      Column('system_government', self.metadata, Text, default=None),
      Column('system_security', self.metadata, Text, default=None),
    )
    ######################################################################

    self.metadata.create_all(self.engine)

