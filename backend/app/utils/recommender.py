"""
backend/app/utils/recommender.py
───────────────────────────────────
Simple mock recommendation logic.
"""

MOCK_COURSES = [
    {"id": "c1", "title": "Algorithmique Avancée", "category": "CS", "level": "L3"},
    {"id": "c2", "title": "Intelligence Artificielle", "category": "CS", "level": "M1"},
    {"id": "c3", "title": "Réseaux & Protocoles", "category": "Telecom", "level": "L3"},
    {"id": "c4", "title": "Analyse de Données", "category": "Math", "level": "M1"},
    {"id": "c5", "title": "Cybersécurité", "category": "Telecom", "level": "M2"},
]

def get_recommendations(user_id: str):
    """
    Returns a list of recommended courses based on user profile.
    For now, it returns 3 random courses from the mock list.
    """
    # Simple logic: return top 3 for now
    return MOCK_COURSES[:3]
