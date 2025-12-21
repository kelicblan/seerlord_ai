
from typing import List, Optional
from pydantic import BaseModel

# Mock Feedback Structure
class Feedback(BaseModel):
    skill_id: str
    rating: int # 1-5
    comment: str
    user_id: str
    timestamp: float

class SkillFeedbackService:
    """
    Simulates a feedback loop service.
    In a real system, this would write to a database and trigger an 'Evolution Job'
    if the average rating for a skill drops below a threshold.
    """
    def __init__(self):
        self.feedback_log: List[Feedback] = []

    def submit_feedback(self, skill_id: str, rating: int, comment: str, user_id: str):
        import time
        feedback = Feedback(
            skill_id=skill_id,
            rating=rating,
            comment=comment,
            user_id=user_id,
            timestamp=time.time()
        )
        self.feedback_log.append(feedback)
        print(f"[FeedbackService] Received feedback for skill {skill_id}: Rating {rating}, Comment: {comment}")
        
        # Trigger Evolution Analysis (Mock)
        self._analyze_skill_performance(skill_id)

    def _analyze_skill_performance(self, skill_id: str):
        # Retrieve all feedback for this skill
        related_feedback = [f for f in self.feedback_log if f.skill_id == skill_id]
        if not related_feedback:
            return

        # Calculate average rating
        avg_rating = sum(f.rating for f in related_feedback) / len(related_feedback)
        
        print(f"[FeedbackService] Skill {skill_id} Average Rating: {avg_rating:.2f} ({len(related_feedback)} reviews)")
        
        if avg_rating < 3.0 and len(related_feedback) >= 1: # Low threshold for demo
            print(f"[FeedbackService] ⚠️ ALERT: Skill {skill_id} is underperforming. Triggering refinement...")
            # In a real system, this would call:
            # dynamic_skill_manager.refine_skill(skill_id, related_feedback)
            self._trigger_refinement_mock(skill_id, related_feedback)

    def _trigger_refinement_mock(self, skill_id: str, feedback_list: List[Feedback]):
        print(f"[FeedbackService] 🧬 Refinement Process Started for Skill {skill_id}")
        print(f"   - Aggregating {len(feedback_list)} user complaints...")
        print(f"   - Reasoning: Users reported issues like '{feedback_list[-1].comment}'")
        print(f"   - Action: Generating optimized Prompt Template...")
        print(f"   - Result: Skill {skill_id} has been updated to v{len(feedback_list)+1}.0")

# Singleton
skill_feedback_service = SkillFeedbackService()
