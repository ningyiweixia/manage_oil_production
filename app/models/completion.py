from datetime import date
from typing import Any

from sqlalchemy import Date, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class WellCompletionRecord(TimestampMixin, Base):
    __tablename__ = "well_completion_record"
    __table_args__ = (
        Index("ix_well_completion_well_no", "well_no"),
        Index("ix_well_completion_measure_type", "measure_type"),
        Index("ix_well_completion_completion_date", "completion_date"),
        {"comment": "完井分类台账表"},
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="记录ID")
    well_no: Mapped[str] = mapped_column(String(64), nullable=False, comment="井号")
    operation_sheet_id: Mapped[int | None] = mapped_column(
        ForeignKey("workover_operation_sheet.id", ondelete="SET NULL"),
        comment="关联修井运行表ID",
    )
    measure_type: Mapped[str] = mapped_column(String(64), nullable=False, comment="措施类型")
    completion_date: Mapped[date | None] = mapped_column(Date, comment="完井日期")
    team_name: Mapped[str | None] = mapped_column(String(128), comment="施工队伍")
    pre_repair_data: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, comment="修前关键数据JSONB（产量、压力、泵效等）"
    )
    post_repair_data: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, comment="修后关键数据JSONB（产量、压力、泵效等）"
    )
    remark: Mapped[str | None] = mapped_column(Text, comment="备注")
