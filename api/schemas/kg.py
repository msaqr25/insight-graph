from enum import StrEnum

from pydantic import BaseModel


class EntityType(StrEnum):
    CONCEPT = "Concept"
    METHOD = "Method"
    MODEL = "Model"
    DATASET = "Dataset"
    AUTHOR = "Author"
    PAPER = "Paper"
    FINDING = "Finding"


class RelationType(StrEnum):
    PROPOSES = "PROPOSES"
    USES = "USES"
    CITES = "CITES"
    CONTRASTS_WITH = "CONTRASTS_WITH"
    SUPPORTS = "SUPPORTS"
    CONTRADICTS = "CONTRADICTS"
    BUILDS_ON = "BUILDS_ON"
    PART_OF = "PART_OF"
    INTRODUCED_BY = "INTRODUCED_BY"


class ExtractedEntity(BaseModel):
    name: str
    type: EntityType
    description: str


class ExtractedRelation(BaseModel):
    source: str
    relation: RelationType
    target: str


class ExtractionResult(BaseModel):
    entities: list[ExtractedEntity]
    relations: list[ExtractedRelation]
