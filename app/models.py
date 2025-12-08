from typing import Optional, List
from sqlmodel import Field, SQLModel, Relationship
from datetime import datetime
import json

class Account(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    naver_id: str = Field(unique=True, index=True)
    nickname: Optional[str] = None
    cookies_json: str = Field(default="[]") # Store cookies as JSON string
    created_at: datetime = Field(default_factory=datetime.now)
    
    tasks: List["Task"] = Relationship(back_populates="account")

class Task(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str 
    account_id: int = Field(foreign_key="account.id")
    cafe_url: str
    board_name: str # Name of the board to search/post to
    content_html: str
    
    account: Account = Relationship(back_populates="tasks")
    logs: List["Log"] = Relationship(back_populates="task")

class Log(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    task_id: int = Field(foreign_key="task.id")
    status: str # "SUCCESS", "FAILED"
    message: str
    timestamp: datetime = Field(default_factory=datetime.now)
    
    task: Task = Relationship(back_populates="logs")
