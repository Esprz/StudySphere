import logging
from typing import List, Dict, Any, Optional
import time

from app.services.recall.base import RecallBase
from app.services.filters.base import FilterBase
from app.services.diversity.base import DiversityBase

logger = logging.getLogger(__name__)

class RecommendationPipeline:
    """
    推荐流水线，负责协调各个推荐组件
    """
    
    def __init__(
        self,
        recall_services: List[RecallBase],
        filter_services: List[FilterBase],
        diversity_service: DiversityBase,
    ):
        """
        初始化推荐流水线
        
        Args:
            recall_services: 召回服务列表
            filter_services: 过滤服务列表
            diversity_service: 多样化服务
        """
        self.recall_services = recall_services
        self.filter_services = filter_services
        self.diversity_service = diversity_service
    
    def recommend(
        self,
        user_id: str,
        context: Dict[str, Any],
        limit: int = 20,
        detailed: bool = False
    ) -> Dict[str, Any]:
        """
        为用户生成推荐
        
        Args:
            user_id: 用户ID
            context: 上下文信息，如设备、时间等
            limit: 最终返回的推荐数量
            detailed: 是否返回详细的中间结果和调试信息
            
        Returns:
            包含推荐结果的字典
        """
        start_time = time.time()
        metrics = {}
        
        # 1. 召回阶段 - 从各个召回源获取候选项
        recall_start_time = time.time()
        candidates = self._get_candidates_from_all_sources(user_id, context)
        metrics["recall_time"] = time.time() - recall_start_time
        metrics["total_candidates"] = len(candidates)
        
        # 2. 过滤阶段 - 过滤掉不合适的项目
        filter_start_time = time.time()
        filtered_candidates = self._apply_filters(user_id, candidates, context)
        metrics["filter_time"] = time.time() - filter_start_time
        metrics["filtered_candidates"] = len(filtered_candidates)
        
        # 3. 多样化阶段 - 确保结果的多样性
        diversity_start_time = time.time()
        diversified_results = self._apply_diversity(user_id, filtered_candidates, context, limit)
        metrics["diversity_time"] = time.time() - diversity_start_time
        
        # 计算总时间
        metrics["total_time"] = time.time() - start_time
        
        # 构建响应
        response = {
            "recommendations": diversified_results,
            "user_id": user_id
        }
        
        # 如果需要，添加详细的中间结果和指标
        if detailed:
            response["metrics"] = metrics
        
        return response
    
    def _get_candidates_from_all_sources(
        self,
        user_id: str,
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        从所有召回源获取候选项并合并
        
        Args:
            user_id: 用户ID
            context: 上下文信息
            
        Returns:
            合并后的候选项列表
        """
        all_candidates = []
        source_metrics = {}
        
        # 从每个召回源获取候选项
        for recall_service in self.recall_services:
            source_name = recall_service.name
            logger.info(f"从 {source_name} 获取候选项")
            
            try:
                start_time = time.time()
                candidates = recall_service.get_candidates(user_id, context)
                elapsed_time = time.time() - start_time
                
                # 记录每个来源的指标
                source_metrics[source_name] = {
                    "count": len(candidates),
                    "time": elapsed_time
                }
                
                # 添加来源标记，如果没有的话
                for candidate in candidates:
                    if "source" not in candidate:
                        candidate["source"] = source_name
                
                all_candidates.extend(candidates)
                logger.info(f"从 {source_name} 获取了 {len(candidates)} 个候选项")
                
            except Exception as e:
                logger.error(f"从 {source_name} 获取候选项失败: {e}", exc_info=True)
        
        # 去重 - 按照物品ID去重
        unique_candidates = self._deduplicate_candidates(all_candidates)
        
        logger.info(f"总计获取了 {len(unique_candidates)} 个唯一候选项")
        return unique_candidates
    
    def _deduplicate_candidates(
        self,
        candidates: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        去除重复的候选项，保留分数最高的
        
        Args:
            candidates: 所有候选项列表
            
        Returns:
            去重后的候选项列表
        """
        # 按照物品ID分组，保留分数最高的
        item_map = {}
        
        for candidate in candidates:
            item_id = candidate.get("item_id")
            if not item_id:
                continue
                
            score = candidate.get("score", 0.0)
            
            # 如果是新物品，或者分数比已有的高，则更新
            if item_id not in item_map or score > item_map[item_id].get("score", 0.0):
                item_map[item_id] = candidate
        
        # 转换回列表
        unique_candidates = list(item_map.values())
        
        return unique_candidates
    
    def _apply_filters(
        self,
        user_id: str,
        candidates: List[Dict[str, Any]],
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        应用所有过滤器
        
        Args:
            user_id: 用户ID
            candidates: 候选项列表
            context: 上下文信息
            
        Returns:
            过滤后的候选项列表
        """
        filtered = candidates
        
        for filter_service in self.filter_services:
            try:
                filter_name = filter_service.__class__.__name__
                logger.info(f"应用过滤器: {filter_name}")
                
                before_count = len(filtered)
                filtered = filter_service.filter_candidates(user_id, filtered, context)
                after_count = len(filtered)
                
                logger.info(f"{filter_name} 过滤后剩余 {after_count} 个候选项（过滤了 {before_count - after_count} 个）")
                
            except Exception as e:
                logger.error(f"应用过滤器失败: {e}", exc_info=True)
        
        return filtered
    
    def _apply_diversity(
        self,
        user_id: str,
        candidates: List[Dict[str, Any]],
        context: Dict[str, Any],
        limit: int
    ) -> List[Dict[str, Any]]:
        """
        应用多样化处理
        
        Args:
            user_id: 用户ID
            candidates: 候选项列表
            context: 上下文信息
            limit: 结果数量限制
            
        Returns:
            多样化后的推荐结果
        """
        try:
            # 应用多样化服务
            diversified = self.diversity_service.diversify(user_id, candidates, context, limit)
            logger.info(f"多样化处理后得到 {len(diversified)} 个结果")
            return diversified
            
        except Exception as e:
            logger.error(f"应用多样化处理失败: {e}", exc_info=True)
            
            # 如果多样化失败，直接返回排序后的前N个
            sorted_candidates = sorted(candidates, key=lambda x: x.get("score", 0.0), reverse=True)
            return sorted_candidates[:limit]