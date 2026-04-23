"""
Converts raw news dicts into typed ClassifiedNews objects.

No sentiment analysis happens here — the raw data already carries sentiment,
scope, and entity tags. This module validates structure and wraps each item
in the schema so all downstream code works with typed objects.
"""

from src.schemas import ClassifiedNews, NewsEntity


_REQUIRED_FIELDS = {
    "id", "headline", "summary", "sentiment", "sentiment_score",
    "scope", "impact_level", "entities", "published_at",
}


class NewsProcessor:
    def process(self, raw_news: list[dict]) -> list[ClassifiedNews]:
        """
        Wraps raw news dicts in ClassifiedNews, validating required fields.

        Logic:
        - Assert all required fields are present (fail fast with a clear error)
        - Build NewsEntity from the nested entities dict
        - Set relevance_score to 0.0 (populated later by RelevanceFilter)
        """
        result: list[ClassifiedNews] = []

        for item in raw_news:
            missing = _REQUIRED_FIELDS - item.keys()
            if missing:
                raise ValueError(
                    f"News item '{item.get('id', '<unknown>')}' is missing fields: {missing}"
                )

            raw_entities: dict = item["entities"]
            entities = NewsEntity(
                sectors=raw_entities.get("sectors", []),
                stocks=raw_entities.get("stocks", []),
                indices=raw_entities.get("indices", []),
                keywords=raw_entities.get("keywords", []),
            )

            result.append(
                ClassifiedNews(
                    id=item["id"],
                    headline=item["headline"],
                    summary=item["summary"],
                    sentiment=item["sentiment"],
                    sentiment_score=item["sentiment_score"],
                    scope=item["scope"],
                    impact_level=item["impact_level"],
                    entities=entities,
                    published_at=item["published_at"],
                    relevance_score=0.0,
                )
            )

        return result
