"""
Continuous improvement engine with quality metrics and refinement loop
"""
import json
import time
from typing import Dict, List, Optional
from dataclasses import dataclass
from utils.logger import get_logger
from utils.schema import CodeAnalysis
from adapters.llm_adapter import LLMAdapter
from adapters.redis_adapter import RedisAdapter
from config.prompts import PROMPTS
import hashlib

@dataclass
class ImprovementMetrics:
    code_quality: float
    test_coverage: float
    performance: float
    modularity: float
    documentation: float

class ImprovementEngine:
    def __init__(self, llm_adapter: LLMAdapter, redis_adapter: Optional[RedisAdapter] = None):
        self.llm = llm_adapter
        self.redis = redis_adapter
        self.logger = get_logger(__name__)
        self.quality_threshold = 0.85  # Default quality threshold
        
    async def analyze_code_quality(self, code: str, analysis: CodeAnalysis) -> ImprovementMetrics:
        """Analyze code quality with context from Redis"""
        # Get historical quality data from Redis if available
        historical_metrics = {}
        if self.redis and hasattr(analysis, 'file_path'):
            file_metadata = await self.redis.get_file_metadata(analysis.file_path)
            if file_metadata and 'quality_metrics' in file_metadata:
                historical_metrics = file_metadata['quality_metrics']
        
        prompt = PROMPTS.get("improvement", {}).get("analyze_quality", "").format(
            code=code,
            language=analysis.language,
            analysis=analysis.__dict__,
            historical_metrics=json.dumps(historical_metrics) if historical_metrics else "No historical metrics available"
        )
        
        metrics = await self.llm.generate(prompt, formated_output="json")
        
        # Store metrics in Redis if we have a file path
        if self.redis and hasattr(analysis, 'file_path'):
            await self.redis.track_file(analysis.file_path, {
                'quality_metrics': metrics,
                'last_analysis_time': int(time.time())
            })
        
        return ImprovementMetrics(**metrics)
        
    async def needs_improvement(self, metrics: ImprovementMetrics) -> bool:
        """Determine if code needs improvement with contextual thresholds"""
        # Get threshold from Redis if available
        threshold = self.quality_threshold
        if self.redis:
            config = await self.redis.get_context("quality_config")
            if config and 'threshold' in config:
                threshold = float(config['threshold'])
        
        overall_score = (
            metrics.code_quality * 0.3 +
            metrics.test_coverage * 0.2 +
            metrics.performance * 0.2 +
            metrics.modularity * 0.2 +
            metrics.documentation * 0.1
        )
        return overall_score < threshold
        
    async def generate_improvement_plan(self, code: str, analysis: CodeAnalysis, metrics: ImprovementMetrics) -> List[Dict]:
        """Generate improvement plan with historical context"""
        # Get previous improvement plans from Redis
        previous_plans = []
        if self.redis and hasattr(analysis, 'file_path'):
            previous_plans = await self.redis.search_context(f"improve:{analysis.file_path}:*")
        
        # Get similar files' improvement plans
        similar_improvements = []
        if self.redis and hasattr(analysis, 'file_path'):
            file_metadata = await self.redis.get_file_metadata(analysis.file_path)
            if file_metadata and 'similar_files' in file_metadata:
                for similar_file in file_metadata['similar_files']:
                    similar_plans = await self.redis.search_context(f"improve:{similar_file}:*")
                    similar_improvements.extend(similar_plans)
        
        prompt = PROMPTS.get("improvement", {}).get("improvement_plan", "").format(
            code=code,
            metrics=metrics.__dict__,
            analysis=analysis.__dict__,
            language=analysis.language,
            previous_plans=json.dumps(previous_plans) if previous_plans else "No previous improvement plans",
            similar_improvements=json.dumps(similar_improvements) if similar_improvements else "No similar improvements found"
        )
        
        return await self.llm.generate(prompt, formated_output="json")
        
    async def refine_code(self, code: str, improvement_plan: List[Dict], context: Dict = None) -> str:
        """Refine code with full context awareness"""
        if context is None:
            context = {}
        
        # Get code patterns from Redis
        patterns = {}
        if self.redis:
            patterns = await self.redis.get_context("code_patterns")
            if not patterns:
                patterns = {}
        
        # Get similar implementations
        similar_implementations = []
        if self.redis and context.get('file_path'):
            similar_implementations = await self.redis.search_context(f"similar:{context['file_path']}")
        
        prompt = PROMPTS.get("improvement", {}).get("refine_code", "").format(
            improvement_plan=json.dumps(improvement_plan),
            context=json.dumps({
                **context,
                "patterns": patterns,
                "similar_implementations": similar_implementations
            }),
            language=context.get('language', 'unknown'),
            code=code
        )
        
        refined_code = await self.llm.generate(prompt, formated_output="code")
        
        # Store the refinement in Redis if we have a file path
        if self.redis and context.get('file_path'):
            snippet_hash = hashlib.sha256(refined_code.encode()).hexdigest()
            await self.redis.track_code_snippet(snippet_hash, {
                'code': refined_code,
                'file_path': context['file_path'],
                'improvement_plan': improvement_plan,
                'type': 'refinement'
            })
        
        return refined_code

    async def track_improvement(self, file_path: str, original_metrics: ImprovementMetrics, 
                              improved_metrics: ImprovementMetrics, improvement_plan: List[Dict]):
        """Track improvement results in Redis for future reference"""
        if not self.redis:
            return
            
        improvement_data = {
            'file_path': file_path,
            'original_metrics': original_metrics.__dict__,
            'improved_metrics': improved_metrics.__dict__,
            'improvement_plan': improvement_plan,
            'timestamp': int(time.time()),
            'improvement_score': self._calculate_improvement_score(original_metrics, improved_metrics)
        }
        
        await self.redis.store_context(
            f"improvement:{file_path}:{int(time.time())}",
            improvement_data
        )
    
    def _calculate_improvement_score(self, original: ImprovementMetrics, improved: ImprovementMetrics) -> float:
        """Calculate overall improvement score"""
        return (
            (improved.code_quality - original.code_quality) * 0.3 +
            (improved.test_coverage - original.test_coverage) * 0.2 +
            (improved.performance - original.performance) * 0.2 +
            (improved.modularity - original.modularity) * 0.2 +
            (improved.documentation - original.documentation) * 0.1
        )