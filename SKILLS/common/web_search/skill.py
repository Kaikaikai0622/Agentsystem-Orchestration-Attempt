"""
Web Search Skill - 网页搜索技能
支持搜索和查找相关信息
"""
import re
from typing import List
from agent import register_skill, SkillInput, SkillOutput, BaseSkill
from agent import ValidationError, ProviderError


@register_skill(name="web_search", keywords=["搜索", "查找", "网页", "google", "bing", "search", "find", "查询"])
class WebSearch(BaseSkill):
    """网页搜索技能 - 模拟网络搜索功能"""

    def __init__(self):
        super().__init__("web_search")

    def validate_input(self, input_data: SkillInput) -> bool:
        """验证输入参数"""
        return True

    def execute(self, input_data: SkillInput) -> SkillOutput:
        """执行搜索操作"""
        query = input_data.content or input_data.params.get("query", "")
        max_results = input_data.params.get("max_results", 5)

        if not str(query).strip():
            raise ValidationError("query is required")

        if not isinstance(max_results, int):
            raise ValidationError("max_results must be an integer")

        if max_results <= 0 or max_results > 50:
            raise ValidationError("max_results must be between 1 and 50")

        try:
            # 模拟搜索结果（实际项目中可接入真实搜索引擎 API）
            results = self._mock_search(query, max_results)
        except Exception as exc:
            raise ProviderError(f"search provider error: {exc}") from exc

        return SkillOutput(
            success=True,
            data={
                "query": query,
                "results": results,
                "total": len(results)
            },
            next_context={"last_query": query, "results_count": len(results)}
        )

    def _mock_search(self, query: str, max_results: int) -> List[dict]:
        """模拟搜索结果"""
        # 模拟一些搜索结果
        mock_db = [
            {
                "title": f"关于 '{query}' 的官方文档",
                "url": f"https://example.com/docs/{query.lower().replace(' ', '-')}",
                "snippet": f"这是关于 {query} 的详细文档，包含了完整的使用说明和示例代码。",
                "source": "official"
            },
            {
                "title": f"{query} - 维基百科",
                "url": f"https://zh.wikipedia.org/wiki/{query}",
                "snippet": f"{query} 是一个重要概念，广泛应用于各个领域...",
                "source": "wikipedia"
            },
            {
                "title": f"{query} 教程 - 从入门到精通",
                "url": f"https://tutorial.example.com/{query}",
                "snippet": f"本教程将带你全面了解 {query} 的各个方面，包含大量实战案例。",
                "source": "tutorial"
            },
            {
                "title": f"如何在项目中使用 {query}",
                "url": f"https://blog.example.com/{query}",
                "snippet": f"分享在真实项目中使用 {query} 的最佳实践和常见问题解决方案。",
                "source": "blog"
            },
            {
                "title": f"{query} 最新动态和趋势",
                "url": f"https://news.example.com/{query}",
                "snippet": f"2024年 {query} 领域的最新发展动态和未来趋势分析。",
                "source": "news"
            }
        ]

        # 根据查询内容过滤和排序
        filtered = [r for r in mock_db if query.lower() in r["title"].lower() or query.lower() in r["snippet"].lower()]

        # 如果没有匹配，返回全部
        if not filtered:
            filtered = mock_db

        return filtered[:max_results]
