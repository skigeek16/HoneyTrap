from pydantic import BaseModel
from typing import List, Set

class Entity(BaseModel):
    value: str
    type: str  # UPI, PHONE, BANK_ACC, URL, ETC
    category: str # PRIMARY, SECONDARY, TACTICAL
    confidence: float
    source_turn: int
    is_validated: bool = False
    
    def __hash__(self):
        return hash((self.value, self.type))

class IntelligenceState(BaseModel):
    entities: List[Entity] = []
    completion_percentage: float = 0.0
    missing_priorities: List[str] = []
    extracted_values: Set[str] = set()

    def add_entity(self, entity: Entity):
        if entity.value not in self.extracted_values:
            self.entities.append(entity)
            self.extracted_values.add(entity.value)