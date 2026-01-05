from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.date import DateTrigger
from loguru import logger
from datetime import datetime, timedelta
from sqlalchemy import select
from server.core.database import SessionLocal
from server.models.automation import AutomationTask, AutomationLog
from server.kernel.registry import registry
import asyncio
import json

# Global scheduler instance
scheduler = AsyncIOScheduler()

async def execute_task(task_id: int):
    """
    The actual execution logic for a task.
    """
    logger.info(f"Starting execution of automation task {task_id}")
    async with SessionLocal() as session:
        # 1. Get Task
        result = await session.execute(select(AutomationTask).where(AutomationTask.id == task_id))
        task = result.scalars().first()
        
        if not task:
            logger.error(f"Task {task_id} not found during execution")
            return
            
        if not task.is_active:
             logger.info(f"Task {task_id} is inactive, skipping")
             return

        # 2. Create Log
        log_entry = AutomationLog(
            task_id=task_id,
            status="RUNNING",
            start_time=datetime.utcnow()
        )
        session.add(log_entry)
        await session.commit()
        await session.refresh(log_entry)
        
        try:
            # 3. Execute Agent
            logger.info(f"Executing agent {task.agent_id} for task {task_id}")
            
            # Construct input
            # Default to placing prompt in messages
            input_data = {"messages": [{"type": "user", "content": task.input_prompt}]}
            
            # Get Plugin
            plugin = registry.get_plugin(task.agent_id)
            if not plugin:
                raise ValueError(f"Plugin {task.agent_id} not found")
                
            app = plugin.get_graph()
            
            # Config
            config = {
                "configurable": {
                    "thread_id": f"automation_{task_id}_{log_entry.id}",
                    "task_id": str(task_id),
                    "user_id": task.user_id or "system",
                }
            }
            
            # Execute
            # Use ainvoke for async execution
            result_output = await app.ainvoke(input_data, config=config)
            
            # Process Output
            output_text = ""
            if isinstance(result_output, dict):
                # Try to find the AI message
                if "messages" in result_output and isinstance(result_output["messages"], list):
                    messages = result_output["messages"]
                    if messages:
                        last_msg = messages[-1]
                        if hasattr(last_msg, "content"):
                            output_text = last_msg.content
                        elif isinstance(last_msg, dict):
                            output_text = last_msg.get("content", str(last_msg))
                        else:
                            output_text = str(last_msg)
                else:
                    # Fallback to dumping the whole dict if structure is unknown
                    # But try to be cleaner
                    # Some agents return 'output' key directly
                    if "output" in result_output:
                        output_text = str(result_output["output"])
                    else:
                        output_text = json.dumps(result_output, default=str, ensure_ascii=False)
            else:
                output_text = str(result_output)

            log_entry.status = "SUCCESS"
            log_entry.output = output_text
            logger.info(f"Task {task_id} completed successfully")
            
        except Exception as e:
            logger.error(f"Task {task_id} failed: {e}")
            log_entry.status = "FAILURE"
            log_entry.error_message = str(e)
            
        finally:
            log_entry.end_time = datetime.utcnow()
            task.last_run_time = datetime.utcnow()
            
            if task.is_one_time:
                task.is_active = False
                # Remove from scheduler
                try:
                    scheduler.remove_job(str(task_id))
                except Exception:
                    pass # Job might be already gone or self-terminating
                
            session.add(log_entry)
            session.add(task)
            await session.commit()

async def load_jobs_from_db():
    """
    Load all active tasks from DB and add them to scheduler.
    """
    logger.info("Loading automation tasks from database...")
    async with SessionLocal() as session:
        result = await session.execute(select(AutomationTask).where(AutomationTask.is_active == True))
        tasks = result.scalars().all()
        
        for task in tasks:
            add_job_to_scheduler(task)
            
    logger.info(f"Loaded {len(tasks)} tasks.")

def add_job_to_scheduler(task: AutomationTask):
    """
    Helper to add a task to the scheduler based on its config.
    """
    job_id = str(task.id)
    
    # Remove existing if any (update case)
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)
        
    if not task.is_active:
        return

    trigger = None
    if task.is_one_time:
        # If it's one time and in the past, maybe run immediately? 
        # For now, assume one-time tasks are immediate or scheduled for future.
        # If no time specified, run now.
        # But we don't have a 'scheduled_time' field for one-time, 
        # let's assume one-time means "run once after creation" or we need a run_at field.
        # The user requirement says "time configuration".
        # Let's assume if cron/interval is missing, it's run now?
        # Or better, if is_one_time is True, we might use DateTrigger if we had a date.
        # For MVP, if is_one_time is True and no cron/interval, run in 5 seconds.
        run_date = datetime.now() + timedelta(seconds=5)
        trigger = DateTrigger(run_date=run_date)
    elif task.cron_expression:
        try:
            # "0 12 * * *" -> split to kwargs? 
            # APScheduler from_crontab is useful
            trigger = CronTrigger.from_crontab(task.cron_expression)
        except Exception as e:
            logger.error(f"Invalid cron expression for task {task.id}: {e}")
            return
    elif task.interval_seconds:
        trigger = IntervalTrigger(seconds=task.interval_seconds)
    else:
        logger.warning(f"Task {task.id} has no valid timing configuration")
        return
        
    scheduler.add_job(
        execute_task,
        trigger=trigger,
        id=job_id,
        args=[task.id],
        replace_existing=True
    )
    logger.info(f"Scheduled task {task.id} with trigger {trigger}")

def remove_job_from_scheduler(task_id: int):
    try:
        scheduler.remove_job(str(task_id))
    except Exception:
        pass
