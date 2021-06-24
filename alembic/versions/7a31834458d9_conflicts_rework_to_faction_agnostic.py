"""conflicts rework to faction agnostic

Revision ID: 7a31834458d9
Revises: 49b5787bd701
Create Date: 2021-06-24 15:21:14.331183+00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7a31834458d9'
down_revision = '49b5787bd701'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint('conflicts_faction_id_fkey', 'conflicts', type_='foreignkey')
    op.drop_constraint('conflicts_constraint', 'conflicts', type_='unique')
    op.drop_constraint('conflicts_opponent_faction_id_fkey', 'conflicts', type_='foreignkey')

    op.alter_column('conflicts', 'faction_id', new_column_name='faction1_id')
    op.alter_column('conflicts', 'opponent_faction_id', new_column_name='faction2_id')
    op.alter_column('conflicts', 'days_won', new_column_name='faction1_days_won')
    op.alter_column('conflicts', 'days_lost', new_column_name='faction2_days_won')

    op.create_foreign_key(None, 'conflicts', 'factions', ['faction1_id'], ['id'])
    op.create_foreign_key(None, 'conflicts', 'factions', ['faction2_id'], ['id'])
    op.create_unique_constraint('conflicts_constraint', 'conflicts', ['systemaddress', 'faction1_id', 'faction2_id'])


def downgrade():
    op.drop_constraint('conflicts_constraint', 'conflicts', type_='unique')
    op.drop_constraint(None, 'conflicts', type_='foreignkey')
    op.drop_constraint(None, 'conflicts', type_='foreignkey')

    op.alter_column('conflicts', 'faction1_id', new_column_name='faction_id')
    op.alter_column('conflicts', 'faction2_id', new_column_name='opponent_faction_id')
    op.alter_column('conflicts', 'faction1_days_won', new_column_name='days_won')
    op.alter_column('conflicts', 'faction2_days_won', new_column_name='days_lost')

    op.create_foreign_key('conflicts_faction_id_fkey', 'conflicts', 'factions', ['faction_id'], ['id'])
    op.create_foreign_key('conflicts_opponent_faction_id_fkey', 'conflicts', 'factions', ['opponent_faction_id'], ['id'])
    op.create_unique_constraint('conflicts_constraint', 'conflicts', ['systemaddress', 'faction_id', 'opponent_faction_id'])
