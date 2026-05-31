from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class EngineeringDesignDoc(TimestampMixin, Base):
    __tablename__ = "engineering_design_doc"
    __table_args__ = (
        UniqueConstraint("well_no", "version", name="uq_engineering_design_doc_well_version"),
        {"comment": "工程设计文档表"},
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="文档ID")
    project_id: Mapped[int | None] = mapped_column(
        ForeignKey("workover_project_pool.id", ondelete="SET NULL"),
        comment="关联项目池ID",
    )
    well_no: Mapped[str] = mapped_column(String(64), nullable=False, comment="井号")
    version: Mapped[str] = mapped_column(String(32), nullable=False, comment="文档版本号")
    minio_bucket: Mapped[str] = mapped_column(String(128), nullable=False, comment="MinIO桶")
    minio_object_key: Mapped[str] = mapped_column(String(512), nullable=False, comment="MinIO对象路径")
    checksum: Mapped[str | None] = mapped_column(String(128), comment="文件校验值")
    remark: Mapped[str | None] = mapped_column(Text, comment="备注")
