"""Rename conflicts constraint

Revision ID: 2fdcd0da93d8
Revises: 4a0561422166
Create Date: 2021-06-24 12:02:14.854483+00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2fdcd0da93d8'
down_revision = '4a0561422166'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint('conflicts_unique_tuple', 'conflicts', type_='unique')
    op.create_unique_constraint('conflicts_constraint', 'conflicts', ['systemaddress', 'faction_id', 'opponent_faction_id'])
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint('conflicts_constraint', 'conflicts', type_='unique')
    op.create_unique_constraint('conflicts_unique_tuple', 'conflicts', ['systemaddress', 'faction_id', 'opponent_faction_id'])
    # ### end Alembic commands ###