"""Server-issued recording challenges and video assessment summaries."""

import sqlalchemy as sa
from alembic import op

revision = "0003_recording_assessment"
down_revision = "768dceeb04b2"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("video_submissions", sa.Column("assessment", sa.JSON(), nullable=True))
    op.create_table(
        "recording_challenges",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "client_process_id",
            sa.Uuid(),
            sa.ForeignKey("client_processes.id"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "registration_link_id",
            sa.Uuid(),
            sa.ForeignKey("registration_links.id"),
            nullable=False,
        ),
        sa.Column("actions", sa.JSON(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade():
    op.drop_table("recording_challenges")
    op.drop_column("video_submissions", "assessment")
