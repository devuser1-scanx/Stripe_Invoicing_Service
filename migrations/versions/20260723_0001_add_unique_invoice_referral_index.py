"""Add one-invoice-per-referral safeguard."""
from typing import Sequence, Union

from alembic import op

revision: str = "20260723_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "uq_org_invoice_appointment_referral",
        "organization_invoices",
        ["appointment_referral_id"],
        unique=True,
        if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_index(
        "uq_org_invoice_appointment_referral",
        table_name="organization_invoices",
        if_exists=True,
    )
