"""Optional applicant contact details; preserve existing client records."""

import sqlalchemy as sa
from alembic import op

revision = "0004_client_contact_details"
down_revision = "0003_recording_assessment"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("client_processes", sa.Column("email", sa.String(254), nullable=True))
    op.add_column(
        "client_processes", sa.Column("alternative_phone_number", sa.String(32), nullable=True)
    )
    op.add_column("client_processes", sa.Column("address", sa.String(500), nullable=True))


def downgrade():
    op.drop_column("client_processes", "address")
    op.drop_column("client_processes", "alternative_phone_number")
    op.drop_column("client_processes", "email")
