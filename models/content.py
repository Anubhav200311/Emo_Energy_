from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from database import Base



class Content(Base):
    __tablename__ = "contents"

    content_id = Column(String, primary_key=True, index = True)
    content_item = Column(String, primary_key=False, nullable=False)
    user_id = Column(String, ForeignKey("users.user_id"), nullable=False)