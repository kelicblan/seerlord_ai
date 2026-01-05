from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from server.core.database import get_db
from server.models.automation import AutomationTask, AutomationLog
from server.core.scheduler import add_job_to_scheduler, remove_job_from_scheduler, execute_task, scheduler
from server.core.llm import get_llm
from langchain_core.messages import SystemMessage, HumanMessage

router = APIRouter()

# Pydantic Models
class CronGenerateRequest(BaseModel):
    description: str

class CronGenerateResponse(BaseModel):
    cron_expression: str

class TaskCreate(BaseModel):
    name: str
    agent_id: str
    input_prompt: str
    cron_expression: Optional[str] = None
    interval_seconds: Optional[int] = None
    is_one_time: bool = False
    is_active: bool = True

class TaskUpdate(BaseModel):
    name: Optional[str] = None
    agent_id: Optional[str] = None
    input_prompt: Optional[str] = None
    cron_expression: Optional[str] = None
    interval_seconds: Optional[int] = None
    is_one_time: Optional[bool] = None
    is_active: Optional[bool] = None

class TaskResponse(BaseModel):
    id: int
    name: Optional[str]
    agent_id: str
    input_prompt: Optional[str]
    cron_expression: Optional[str]
    interval_seconds: Optional[int]
    is_one_time: bool
    is_active: bool
    last_run_time: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True

class LogResponse(BaseModel):
    id: int
    task_id: int
    status: str
    output: Optional[str]
    error_message: Optional[str]
    start_time: datetime
    end_time: Optional[datetime]
    
    class Config:
        from_attributes = True

# Endpoints

@router.post("/tasks", response_model=TaskResponse)
async def create_task(task_in: TaskCreate, db: AsyncSession = Depends(get_db)):
    task = AutomationTask(**task_in.dict())
    db.add(task)
    await db.commit()
    await db.refresh(task)
    
    # Schedule
    add_job_to_scheduler(task)
    
    return task

@router.get("/tasks", response_model=List[TaskResponse])
async def list_tasks(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AutomationTask).order_by(AutomationTask.id))
    return result.scalars().all()

@router.put("/tasks/{task_id}", response_model=TaskResponse)
async def update_task(task_id: int, task_in: TaskUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AutomationTask).where(AutomationTask.id == task_id))
    task = result.scalars().first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    update_data = task_in.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(task, field, value)
        
    await db.commit()
    await db.refresh(task)
    
    # Reschedule
    if task.is_active:
        add_job_to_scheduler(task)
    else:
        remove_job_from_scheduler(task.id)
        
    return task

@router.delete("/tasks/{task_id}")
async def delete_task(task_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AutomationTask).where(AutomationTask.id == task_id))
    task = result.scalars().first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    remove_job_from_scheduler(task.id)
    await db.delete(task)
    await db.commit()
    return {"status": "success"}

@router.post("/tasks/{task_id}/run")
async def run_task_manually(task_id: int, db: AsyncSession = Depends(get_db)):
    """Trigger the task immediately in background"""
    result = await db.execute(select(AutomationTask).where(AutomationTask.id == task_id))
    task = result.scalars().first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    # We use scheduler.add_job to run immediately once without affecting schedule
    scheduler.add_job(execute_task, args=[task.id], id=f"manual_{task.id}_{datetime.now().timestamp()}", name=f"Manual run {task.name}")
    
    return {"status": "triggered"}

@router.get("/tasks/{task_id}/logs", response_model=List[LogResponse])
async def get_task_logs(task_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(AutomationLog)
        .where(AutomationLog.task_id == task_id)
        .order_by(desc(AutomationLog.start_time))
        .limit(50)
    )
    return result.scalars().all()

@router.post("/cron/generate", response_model=CronGenerateResponse)
async def generate_cron(request: CronGenerateRequest):
    """
    Generate a Cron expression from a natural language description using LLM.
    """
    llm = get_llm(temperature=0)
    
    system_prompt = (
        "You are a helpful assistant that converts natural language time descriptions into Cron expressions.\n"
        "Output ONLY the standard Cron expression (5 fields: minute hour day month day_of_week).\n"
        "Example: 'Every day at 8 AM' -> '0 8 * * *'\n"
        "Do not add any explanation or extra text."
    )
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=request.description)
    ]
    
    response = await llm.ainvoke(messages)
    cron_expression = response.content.strip().replace("`", "")
    
    return CronGenerateResponse(cron_expression=cron_expression)
