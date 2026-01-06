from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, delete
from server.models.chat import ChatSession, ChatMessage
from typing import List, Optional
import uuid

async def create_session(db: AsyncSession, user_id: int, agent_id: str = None, title: str = None) -> ChatSession:
    # Use UUID for session ID, but prefixed with something better than web-test-
    # Actually, UUID is standard. The user complained about web-test- prefix.
    # If we use UUID, it's just a string.
    # Let's generate a clean UUID.
    session_id = str(uuid.uuid4())
    
    if not title:
        title = "New Chat"
    
    db_session = ChatSession(
        id=session_id,
        user_id=user_id,
        agent_id=agent_id,
        title=title
    )
    db.add(db_session)
    await db.commit()
    await db.refresh(db_session)
    return db_session

async def get_sessions_by_user(db: AsyncSession, user_id: int, skip: int = 0, limit: int = 20) -> List[ChatSession]:
    result = await db.execute(
        select(ChatSession)
        .where(ChatSession.user_id == user_id)
        .order_by(desc(ChatSession.updated_at))
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()

async def get_session(db: AsyncSession, session_id: str) -> Optional[ChatSession]:
    result = await db.execute(select(ChatSession).where(ChatSession.id == session_id))
    return result.scalars().first()

async def create_message(db: AsyncSession, session_id: str, role: str, content: str, thoughts: list = None) -> ChatMessage:
    db_message = ChatMessage(
        session_id=session_id,
        role=role,
        content=content,
        thoughts=thoughts
    )
    db.add(db_message)
    await db.commit()
    await db.refresh(db_message)
    
    # Update session updated_at
    # We can do this explicitly to ensure the session moves to top of history
    # Or rely on 'onupdate' if the DB supports it, but SQLAlchemy object update is better
    session = await get_session(db, session_id)
    if session:
        # Just accessing it might not be enough if we don't change anything
        # But we added a message which is related.
        # Let's explicitly touch it if needed, or maybe just let it be.
        # Actually, adding a child doesn't necessarily update parent's updated_at unless configured.
        # Let's explicitly update it.
        from datetime import datetime
        session.updated_at = datetime.utcnow()
        db.add(session)
        await db.commit()
        
    return db_message

async def get_messages_by_session(db: AsyncSession, session_id: str) -> List[ChatMessage]:
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at) # Ascending order
    )
    return result.scalars().all()

async def delete_session(db: AsyncSession, session_id: str, user_id: int) -> bool:
    result = await db.execute(
        select(ChatSession).where(ChatSession.id == session_id, ChatSession.user_id == user_id)
    )
    session = result.scalars().first()
    if session:
        await db.delete(session)
        await db.commit()
        return True
    return False

async def get_or_create_session(db: AsyncSession, session_id: str, user_id: int, agent_id: str = None) -> ChatSession:
    session = await get_session(db, session_id)
    if not session:
        # Create new one
        # Use the provided session_id if valid, or generate new one?
        # The frontend might generate a temporary ID.
        # If the frontend ID is not a UUID or we want to enforce our ID generation, we might have issues.
        # But `stream_events` usually takes a `thread_id`.
        # If `thread_id` is passed, we should respect it if possible, or mapping it.
        # For simplicity, if the ID doesn't exist, we create it.
        
        db_session = ChatSession(
            id=session_id,
            user_id=user_id,
            agent_id=agent_id,
            title="New Chat"
        )
        db.add(db_session)
        await db.commit()
        await db.refresh(db_session)
        return db_session
    
    # Verify user ownership?
    if session.user_id != user_id:
        # This is tricky. If a user tries to access another user's session ID.
        # We should probably throw error or create a new one with different ID.
        # For now, let's assume session IDs are unique enough (UUIDs).
        # If collision (unlikely) or malicious access, we should block.
        raise ValueError("Session exists but belongs to another user")
        
    return session
