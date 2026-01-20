from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlmodel import Session, select
from app.database import get_session
from app.models import Task, Account, Log
from app.engine import actions

router = APIRouter(prefix="/tasks", tags=["tasks"])

@router.get("/")
def list_tasks(session: Session = Depends(get_session)):
    return session.exec(select(Task)).all()

@router.post("/")
def create_task(task: Task, session: Session = Depends(get_session)):
    # Verify account exists
    account = session.get(Account, task.account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    session.add(task)
    session.commit()
    session.refresh(task)
    return task

@router.delete("/{task_id}")
def delete_task(task_id: int, session: Session = Depends(get_session)):
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    # Manually delete associated logs first to avoid FK constraint/cascade issues
    logs = session.exec(select(Log).where(Log.task_id == task_id)).all()
    for log in logs:
        session.delete(log)
        
    session.delete(task)
    session.commit()
    return {"status": "success"}

@router.post("/{task_id}/run")
async def run_task(task_id: int, background_tasks: BackgroundTasks, session: Session = Depends(get_session)):
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Run in background to not block response
    background_tasks.add_task(actions.run_task, task_id)
    return {"status": "started", "message": f"Task {task.name} started"}

@router.get("/{task_id}/logs")
def get_task_logs(task_id: int, session: Session = Depends(get_session)):
    # return last 10 logs
    return session.exec(select(Log).where(Log.task_id == task_id).order_by(Log.timestamp.desc()).limit(10)).all()
