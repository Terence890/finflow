"""Alembic template for generating migration scripts.

This file provides the template for auto-generated migration scripts.
"""

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic
revision = "${rev}"
down_revision = "${down_rev}"
branch_labels = ${branch_labels}
depends_on = ${depends_on}


def upgrade():
    """Upgrade database schema."""
    pass


def downgrade():
    """Downgrade database schema."""
    pass
