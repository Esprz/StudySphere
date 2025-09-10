import logging
from typing import List, Dict, Any, Optional
import time

from app.services.recall.base import RecallBase
from app.services.filters.base import FilterBase
from app.services.diversity.base import DiversityBase

logger = logging.getLogger(__name__)


class RecommendationPipeline:

    def __init__(
        self,
        recall_services: List[RecallBase],
        filter_services: List[FilterBase],
        diversity_service: DiversityBase,
    ):
        self.recall_services = recall_services
        self.filter_services = filter_services
        self.diversity_service = diversity_service

    def recommend(
        self,
        user_id: str,
        context: Dict[str, Any],
        limit: int = 20,
        detailed: bool = False,
    ) -> Dict[str, Any]:

        start_time = time.time()
        metrics = {}

        recall_start_time = time.time()
        candidates = self._get_candidates_from_all_sources(user_id, context)
        metrics["recall_time"] = time.time() - recall_start_time
        metrics["total_candidates"] = len(candidates)

        filter_start_time = time.time()
        filtered_candidates = self._apply_filters(user_id, candidates, context)
        metrics["filter_time"] = time.time() - filter_start_time
        metrics["filtered_candidates"] = len(filtered_candidates)

        diversity_start_time = time.time()
        diversified_results = self._apply_diversity(
            user_id, filtered_candidates, context, limit
        )
        metrics["diversity_time"] = time.time() - diversity_start_time

        metrics["total_time"] = time.time() - start_time

        response = {"recommendations": diversified_results, "user_id": user_id}

        if detailed:
            response["metrics"] = metrics

        return response

    def _get_candidates_from_all_sources(
        self, user_id: str, context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        all_candidates = []
        source_metrics = {}

        for recall_service in self.recall_services:
            source_name = recall_service.name
            logger.info(f"Getting candidates from {source_name}")

            try:
                start_time = time.time()
                candidates = recall_service.get_candidates(user_id, context)
                elapsed_time = time.time() - start_time

                source_metrics[source_name] = {
                    "count": len(candidates),
                    "time": elapsed_time,
                }

                for candidate in candidates:
                    if "source" not in candidate:
                        candidate["source"] = source_name

                all_candidates.extend(candidates)
                logger.info(f"Got {len(candidates)} candidates from {source_name}")

            except Exception as e:
                logger.error(
                    f"Failed to get candidates from {source_name}: {e}", exc_info=True
                )

        unique_candidates = self._deduplicate_candidates(all_candidates)

        logger.info(f"Total unique candidates: {len(unique_candidates)}")
        return unique_candidates

    def _deduplicate_candidates(
        self, candidates: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        item_map = {}

        for candidate in candidates:
            item_id = candidate.get("item_id")
            if not item_id:
                continue

            score = candidate.get("score", 0.0)

            if item_id not in item_map or score > item_map[item_id].get("score", 0.0):
                item_map[item_id] = candidate

        unique_candidates = list(item_map.values())

        return unique_candidates

    def _apply_filters(
        self, user_id: str, candidates: List[Dict[str, Any]], context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        filtered = candidates

        for filter_service in self.filter_services:
            try:
                filter_name = filter_service.__class__.__name__
                logger.info(f"Applying filter: {filter_name}")

                before_count = len(filtered)
                filtered = filter_service.filter_candidates(user_id, filtered, context)
                after_count = len(filtered)

                logger.info(
                    f"{filter_name} filtered out {before_count - after_count} candidates, {after_count} remaining"
                )

            except Exception as e:
                logger.error(f"Failed to apply filter: {e}", exc_info=True)

        return filtered

    def _apply_diversity(
        self,
        user_id: str,
        candidates: List[Dict[str, Any]],
        context: Dict[str, Any],
        limit: int,
    ) -> List[Dict[str, Any]]:
        try:
            diversified = self.diversity_service.diversify(
                user_id, candidates, context, limit
            )
            logger.info(f"Diversity applied, {len(diversified)} results")
            return diversified

        except Exception as e:
            logger.error(f"Failed to apply diversity: {e}", exc_info=True)

            sorted_candidates = sorted(
                candidates, key=lambda x: x.get("score", 0.0), reverse=True
            )
            return sorted_candidates[:limit]
