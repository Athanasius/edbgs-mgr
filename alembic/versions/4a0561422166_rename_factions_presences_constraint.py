"""Rename factions_presences constraint

Revision ID: 4a0561422166
Revises: d8e2ea1df2cb
Create Date: 2021-06-24 11:58:12.796369+00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4a0561422166'
down_revision = 'd8e2ea1df2cb'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint('factions_presences_tuple', 'factions_presences', type_='unique')
    op.create_unique_constraint('factions_presences_constraint', 'factions_presences', ['faction_id', 'systemaddress'])
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint('factions_presences_constraint', 'factions_presences', type_='unique')
    op.create_unique_constraint('factions_presences_tuple', 'factions_presences', ['faction_id', 'systemaddress'])
    # ### end Alembic commands ###
