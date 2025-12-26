from sqlalchemy import Column, String, DateTime
from sqlalchemy.sql import func

from server.core.database import Base

class TutorialExport(Base):
    __tablename__ = "tutorial_exports"

    id = Column(String, primary_key=True, index=True)
    tenant_id = Column(String, index=True, nullable=True)
    user_id = Column(String, index=True, nullable=True)

    topic = Column(String, nullable=True)
    title = Column(String, nullable=True)
    file_path = Column(String, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
