import logging

import numpy as np
from neo4j import AsyncGraphDatabase
from sentence_transformers import SentenceTransformer

from api.config import settings
from api.schemas.kg import ExtractedEntity, ExtractedRelation

logger = logging.getLogger(__name__)

SIMILARITY_THRESHOLD = 0.92


def cosine_similarity(a: list[float], b: list[float]) -> float:
    a_arr = np.array(a)
    b_arr = np.array(b)
    return float(np.dot(a_arr, b_arr) / (np.linalg.norm(a_arr) * np.linalg.norm(b_arr)))


class Neo4jClient:
    def __init__(self, uri: str, user: str, password: str, database: str):
        self._driver = AsyncGraphDatabase.driver(uri, auth=(user, password))
        self._database = database
        self._embedding_model: SentenceTransformer | None = None

    def _get_embedding_model(self) -> SentenceTransformer:
        if self._embedding_model is None:
            self._embedding_model = SentenceTransformer(settings.EMBEDDING_MODEL, device="cpu")
        return self._embedding_model

    async def close(self) -> None:
        await self._driver.close()

    def _generate_embedding(self, text: str) -> list[float]:
        model = self._get_embedding_model()
        embedding = model.encode(text, show_progress_bar=False)
        return embedding.tolist()

    def _entity_text(self, entity: ExtractedEntity) -> str:
        return f"{entity.name}: {entity.description}"

    async def create_entities(self, entities: list[ExtractedEntity]) -> int:
        if not entities:
            return 0

        async with self._driver.session(database=self._database) as session:
            for entity in entities:
                entity_text = self._entity_text(entity)
                new_embedding = self._generate_embedding(entity_text)

                result = await session.run(
                    """
                    MATCH (e:Entity {type: $entity_type})
                    WHERE e.embedding IS NOT NULL
                    RETURN e.name AS name, e.embedding AS embedding
                    """,
                    entity_type=entity.type.value,
                )
                existing_entities = await result.data()

                matched_name = None
                if existing_entities:
                    for existing in existing_entities:
                        sim = cosine_similarity(new_embedding, existing["embedding"])
                        if sim > SIMILARITY_THRESHOLD:
                            matched_name = existing["name"]
                            logger.info(
                                f"Matched '{entity.name}' with existing '{matched_name}' (sim: {sim:.2f})"
                            )
                            break

                if matched_name:
                    await session.run(
                        """
                        MATCH (existing:Entity {name: $matched_name, type: $entity_type})
                        SET existing.description = $description,
                            existing.embedding = $embedding,
                            existing.updated_at = timestamp()
                        """,
                        matched_name=matched_name,
                        entity_type=entity.type.value,
                        description=entity.description,
                        embedding=new_embedding,
                    )
                else:
                    await session.run(
                        """
                        MERGE (e:Entity {name: $name, type: $entity_type})
                        ON CREATE SET e.description = $description,
                                      e.embedding = $embedding,
                                      e.created_at = timestamp()
                        ON MATCH SET e.description = $description,
                                    e.embedding = $embedding,
                                    e.updated_at = timestamp()
                        """,
                        name=entity.name,
                        entity_type=entity.type.value,
                        description=entity.description,
                        embedding=new_embedding,
                    )
                    logger.info(f"Created new entity: {entity.name}")

        return len(entities)

    async def create_relations(self, relations: list[ExtractedRelation]) -> int:
        if not relations:
            return 0

        created_count = 0
        async with self._driver.session(database=self._database) as session:
            for rel in relations:
                result = await session.run(
                    """
                    MATCH (a:Entity {name: $source})
                    MATCH (b:Entity {name: $target})
                    RETURN a, b
                    """,
                    source=rel.source,
                    target=rel.target,
                )
                match = await result.single()
                if not match:
                    logger.warning(
                        f"Cannot create relation '{rel.source}'->'{rel.target}': "
                        f"source or target entity not found"
                    )
                    continue

                await session.run(
                    """
                    MATCH (a:Entity {name: $source})
                    MATCH (b:Entity {name: $target})
                    MERGE (a)-[r:RELATION {type: $rel_type}]->(b)
                    ON CREATE SET r.created_at = timestamp()
                    """,
                    source=rel.source,
                    target=rel.target,
                    rel_type=rel.relation.value,
                )
                created_count += 1

        return created_count

    async def clear_graph(self) -> None:
        async with self._driver.session(database=self._database) as session:
            await session.run("MATCH (n) DETACH DELETE n")


_client: Neo4jClient | None = None


def get_neo4j_client() -> Neo4jClient:
    global _client
    if _client is None:
        _client = Neo4jClient(
            uri=settings.NEO4J_URI,
            user=settings.NEO4J_USER,
            password=settings.NEO4J_PASSWORD,
            database=settings.NEO4J_DATABASE,
        )
    return _client


async def close_neo4j() -> None:
    global _client
    if _client is not None:
        await _client.close()
        _client = None
