import json
import logging

from google.genai import Client

from api.config import settings
from api.schemas.kg import ExtractionResult

logger = logging.getLogger(__name__)
_genai_client: Client | None = None


EXTRACTION_PROMPT = """You are an academic knowledge graph extractor. Given the following text chunk from a research paper,
extract all entities and relationships.

STRICT RULES:
- Entity types must be one of: Concept, Method, Model, Dataset, Author, Paper, Finding
- Relation types must be one of: PROPOSES, USES, CITES, CONTRASTS_WITH, SUPPORTS,
  CONTRADICTS, BUILDS_ON, PART_OF, INTRODUCED_BY
- Return ONLY valid JSON. No preamble. No explanation.
- Normalize entity names: use title case, spell out abbreviations on first occurrence.
- If no entities or relations are found, return {"entities": [], "relations": []}

OUTPUT FORMAT:
{{
  "entities": [
    {{"name": "string", "type": "EntityType", "description": "one sentence"}}
  ],
  "relations": [
    {{"source": "entity_name", "relation": "RELATION_TYPE", "target": "entity_name"}}
  ]
}}

TEXT CHUNK:
{chunk_text}"""


def get_genai_client() -> Client:
    global _genai_client
    if _genai_client is None:
        _genai_client = Client(api_key=settings.GOOGLE_API_KEY)
    return _genai_client


def extract_entities_relations(chunk_text: str) -> ExtractionResult:
    client = get_genai_client()

    prompt = EXTRACTION_PROMPT.replace("{chunk_text}", chunk_text)

    try:
        response = client.models.generate_content(
            model=settings.GENAI_MODEL,
            contents=prompt,
        )
    except Exception as e:
        logger.error(f"GenAI API call failed: {e}")
        return ExtractionResult(entities=[], relations=[])

    response_text = response.text if response.text else ""

    response_text = response_text.strip()
    if response_text.startswith("```"):
        lines = response_text.split("\n")
        if len(lines) > 1 and lines[0].startswith("```"):
            response_text = "\n".join(lines[1:])
            if response_text.strip().endswith("```"):
                response_text = response_text.rstrip().rsplit("```", 1)[0]
            response_text = response_text.strip()

    try:
        parsed = json.loads(response_text)
    except json.JSONDecodeError as e:
        logger.warning(
            f"Failed to parse LLM response as JSON: {e}, response: {response_text[:500]}"
        )
        return ExtractionResult(entities=[], relations=[])

    try:
        result = ExtractionResult.model_validate(parsed)
    except Exception as e:
        logger.warning(f"Failed to validate extraction result: {e}, parsed: {parsed}")
        return ExtractionResult(entities=[], relations=[])

    return result
