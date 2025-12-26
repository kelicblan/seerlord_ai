from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from server.db.session import get_db
from server.db.models import LLMModel, SystemSetting
from server.schemas.settings import (
    LLMModelCreate, 
    LLMModelUpdate,
    LLMModelResponse, 
    SystemSettingCreate, 
    SystemSettingResponse
)

router = APIRouter()

# --- Models Management ---

@router.get("/models", response_model=List[LLMModelResponse])
def get_models(db: Session = Depends(get_db)):
    return db.query(LLMModel).all()

@router.post("/models", response_model=LLMModelResponse)
def create_model(model: LLMModelCreate, db: Session = Depends(get_db)):
    db_model = LLMModel(
        name=model.name,
        provider=model.provider,
        base_url=model.base_url,
        model_name=model.model_name,
        api_key=model.api_key,
        model_type=model.model_type,
        price_per_1k_tokens=model.price_per_1k_tokens
    )
    db.add(db_model)
    db.commit()
    db.refresh(db_model)
    return db_model

@router.put("/models/{model_id}", response_model=LLMModelResponse)
def update_model(model_id: int, model: LLMModelUpdate, db: Session = Depends(get_db)):
    db_model = db.query(LLMModel).filter(LLMModel.id == model_id).first()
    if not db_model:
        raise HTTPException(status_code=404, detail="Model not found")
    
    db_model.name = model.name
    db_model.provider = model.provider
    db_model.base_url = model.base_url
    db_model.model_name = model.model_name
    db_model.api_key = model.api_key
    db_model.model_type = model.model_type
    db_model.price_per_1k_tokens = model.price_per_1k_tokens
    
    db.commit()
    db.refresh(db_model)
    return db_model

@router.delete("/models/{model_id}")
def delete_model(model_id: int, db: Session = Depends(get_db)):
    db_model = db.query(LLMModel).filter(LLMModel.id == model_id).first()
    if not db_model:
        raise HTTPException(status_code=404, detail="Model not found")
    db.delete(db_model)
    db.commit()
    return {"message": "Model deleted"}

# --- System Settings Management ---

@router.get("/system", response_model=List[SystemSettingResponse])
def get_system_settings(db: Session = Depends(get_db)):
    return db.query(SystemSetting).all()

@router.post("/system")
def update_system_settings(settings: List[SystemSettingCreate], db: Session = Depends(get_db)):
    for setting in settings:
        db_setting = db.query(SystemSetting).filter(SystemSetting.key == setting.key).first()
        if db_setting:
            db_setting.value = setting.value
            if setting.description:
                db_setting.description = setting.description
        else:
            db_setting = SystemSetting(
                key=setting.key,
                value=setting.value,
                description=setting.description
            )
            db.add(db_setting)
    db.commit()
    return {"message": "Settings updated"}

@router.get("/system/{key}", response_model=SystemSettingResponse)
def get_system_setting(key: str, db: Session = Depends(get_db)):
    setting = db.query(SystemSetting).filter(SystemSetting.key == key).first()
    if not setting:
        raise HTTPException(status_code=404, detail="Setting not found")
    return setting
