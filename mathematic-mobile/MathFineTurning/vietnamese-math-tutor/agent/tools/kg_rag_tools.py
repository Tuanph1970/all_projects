"""
KG-RAG Tools for the Vietnamese Grade 12 Math Tutor Agent.

Provides tool interfaces for:
- Semantic formula search
- Hybrid retrieval
- Learning path generation
- Prerequisite discovery
"""

import logging
from typing import Any, Dict, List, Optional

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from utils.logger import get_logger

logger = get_logger("kg_rag_tools")

# Singleton instances for efficiency
_kg_rag_system = None


def _get_kg_rag_system():
    """Get or create the KG-RAG system singleton."""
    global _kg_rag_system

    if _kg_rag_system is None:
        try:
            from agent.tools.formula_kg import FormulaKnowledgeGraph
            from agent.retrieval import (
                HybridRetriever,
                HybridRetrieverConfig,
                ConversationContextManager,
            )

            # Initialize components
            kg = FormulaKnowledgeGraph()

            config = HybridRetrieverConfig(
                semantic_weight=0.6,
                graph_weight=0.4,
                include_prerequisites=True,
                max_graph_hops=2,
            )

            retriever = HybridRetriever(
                knowledge_graph=kg,
                config=config,
            )

            # Index formulas if needed
            retriever.index_formulas()

            context_manager = ConversationContextManager()

            _kg_rag_system = {
                "kg": kg,
                "retriever": retriever,
                "context": context_manager,
            }

            logger.info("KG-RAG system initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize KG-RAG system: {e}")
            _kg_rag_system = None

    return _kg_rag_system


def semantic_search_tool(
    query: str,
    top_k: int = 5,
    category: Optional[str] = None,
    language: str = "vi",
) -> Dict[str, Any]:
    """
    Tìm kiếm công thức bằng ngôn ngữ tự nhiên.

    Semantic search tool - tìm công thức phù hợp với câu hỏi của học sinh
    bằng cách so sánh nghĩa (không chỉ từ khóa).

    Args:
        query: Câu hỏi hoặc mô tả công thức cần tìm
               (ví dụ: "công thức tính đạo hàm của hàm hợp")
        top_k: Số lượng kết quả trả về (mặc định: 5)
        category: Lọc theo danh mục (calculus, trigonometry, geometry, probability)
        language: Ngôn ngữ trả về (vi hoặc en)

    Returns:
        Dictionary chứa:
        - success: True/False
        - query: Câu truy vấn
        - results: Danh sách công thức tìm được với điểm phù hợp
        - explanation: Giải thích kết quả bằng tiếng Việt

    Examples:
        >>> semantic_search_tool("đạo hàm hàm hợp", top_k=3)
        >>> semantic_search_tool("tích phân của sin x", category="calculus")
        >>> semantic_search_tool("xác suất biến cố", top_k=5, category="probability")
    """
    system = _get_kg_rag_system()

    if system is None:
        return {
            "success": False,
            "error": "KG-RAG system not initialized. Using fallback search.",
            "query": query,
        }

    try:
        retriever = system["retriever"]
        context = system["context"]

        # Record query
        context.add_query(query)

        # Get context formulas
        context_formulas = context.get_context_formulas(3)

        # Perform hybrid retrieval
        results, explanation = retriever.retrieve_with_explanation(
            query=query,
            k=top_k,
            language=language,
        )

        # Record interactions
        for result in results[:3]:  # Top 3
            context.add_formula_interaction(
                result.formula_id,
                interaction_type="viewed",
                context=query,
            )

        # Format results
        formatted_results = []
        for r in results:
            result_dict = {
                "formula_id": r.formula_id,
                "score": round(r.score, 3),
                "source": r.source,
            }

            if r.formula_data:
                result_dict["name"] = r.formula_data.get(
                    "name_vi" if language == "vi" else "name", r.formula_id
                )
                result_dict["latex"] = r.formula_data.get("latex", "")
                result_dict["category"] = r.formula_data.get("category", "")

            if r.graph_context:
                result_dict["related"] = r.graph_context

            formatted_results.append(result_dict)

        return {
            "success": True,
            "query": query,
            "results": formatted_results,
            "count": len(formatted_results),
            "explanation": explanation,
        }

    except Exception as e:
        logger.error(f"Semantic search error: {e}")
        return {
            "success": False,
            "error": str(e),
            "query": query,
        }


def find_prerequisites_tool(
    formula_id: str,
    max_depth: int = 3,
    language: str = "vi",
) -> Dict[str, Any]:
    """
    Tìm các công thức tiên quyết cần học trước.

    Prerequisites tool - giúp học sinh biết cần học những gì trước
    khi học một công thức mới.

    Args:
        formula_id: ID của công thức đích (ví dụ: "calc_010", "trig_003")
        max_depth: Độ sâu tìm kiếm (mặc định: 3)
        language: Ngôn ngữ trả về

    Returns:
        Dictionary chứa:
        - success: True/False
        - formula_id: ID công thức đích
        - prerequisites: Danh sách công thức tiên quyết theo thứ tự
        - learning_path: Lộ trình học đề xuất

    Examples:
        >>> find_prerequisites_tool("calc_012")  # Tích phân từng phần
        >>> find_prerequisites_tool("calc_010", max_depth=2)  # Tích phân cơ bản
    """
    system = _get_kg_rag_system()

    if system is None:
        return {
            "success": False,
            "error": "KG-RAG system not initialized",
            "formula_id": formula_id,
        }

    try:
        kg = system["kg"]
        context = system["context"]

        # Get prerequisite paths
        prereq_paths = kg.find_prerequisites(formula_id, max_depth=max_depth)

        # Get learning path
        known_formulas = context.knowledge_state.known_formulas
        learning_path = kg.get_learning_path(formula_id, known_formulas)

        # Format prerequisites
        prerequisites = []
        seen_ids = set()

        for path in prereq_paths:
            for node_id in path.nodes:
                if node_id != formula_id and node_id not in seen_ids:
                    if not node_id.startswith("concept_"):
                        seen_ids.add(node_id)
                        if node_id in kg.formula_db.formulas:
                            f = kg.formula_db.formulas[node_id]
                            prerequisites.append({
                                "id": node_id,
                                "name": f.name_vi if language == "vi" else f.name,
                                "latex": f.formula,
                                "category": f.category,
                                "already_known": node_id in known_formulas,
                            })

        # Format learning path
        learning_path_info = []
        for i, f_id in enumerate(learning_path):
            if f_id in kg.formula_db.formulas:
                f = kg.formula_db.formulas[f_id]
                learning_path_info.append({
                    "step": i + 1,
                    "id": f_id,
                    "name": f.name_vi if language == "vi" else f.name,
                    "is_target": f_id == formula_id,
                })

        # Generate explanation
        if language == "vi":
            if prerequisites:
                explanation = f"Để học công thức này, bạn cần biết trước {len(prerequisites)} công thức:\n"
                for p in prerequisites[:5]:
                    status = "✓ đã biết" if p["already_known"] else "○ cần học"
                    explanation += f"  • {p['name']} ({status})\n"
            else:
                explanation = "Đây là công thức cơ bản, không yêu cầu kiến thức tiên quyết."
        else:
            explanation = f"Found {len(prerequisites)} prerequisite formulas."

        return {
            "success": True,
            "formula_id": formula_id,
            "prerequisites": prerequisites,
            "learning_path": learning_path_info,
            "explanation": explanation,
        }

    except Exception as e:
        logger.error(f"Prerequisites tool error: {e}")
        return {
            "success": False,
            "error": str(e),
            "formula_id": formula_id,
        }


def find_applications_tool(
    formula_id: str,
    max_depth: int = 2,
    language: str = "vi",
) -> Dict[str, Any]:
    """
    Tìm các ứng dụng và công thức phát triển từ một công thức.

    Applications tool - giúp học sinh biết công thức này được dùng ở đâu
    và dẫn đến những khái niệm gì.

    Args:
        formula_id: ID của công thức nguồn
        max_depth: Độ sâu tìm kiếm
        language: Ngôn ngữ trả về

    Returns:
        Dictionary chứa:
        - success: True/False
        - formula_id: ID công thức nguồn
        - applications: Danh sách ứng dụng
        - leads_to: Công thức/khái niệm phát triển tiếp

    Examples:
        >>> find_applications_tool("calc_001")  # Đạo hàm → tối ưu, tích phân...
    """
    system = _get_kg_rag_system()

    if system is None:
        return {
            "success": False,
            "error": "KG-RAG system not initialized",
            "formula_id": formula_id,
        }

    try:
        kg = system["kg"]

        # Get application paths
        app_paths = kg.find_applications(formula_id, max_depth=max_depth)

        # Format applications
        applications = []
        seen_ids = set()

        for path in app_paths:
            for node_id in path.nodes:
                if node_id != formula_id and node_id not in seen_ids:
                    if not node_id.startswith("concept_"):
                        seen_ids.add(node_id)
                        if node_id in kg.formula_db.formulas:
                            f = kg.formula_db.formulas[node_id]
                            applications.append({
                                "id": node_id,
                                "name": f.name_vi if language == "vi" else f.name,
                                "category": f.category,
                            })

        # Generate explanation
        if language == "vi":
            if applications:
                explanation = f"Công thức này được ứng dụng trong {len(applications)} lĩnh vực:\n"
                for app in applications[:5]:
                    explanation += f"  • {app['name']}\n"
            else:
                explanation = "Chưa có thông tin về ứng dụng của công thức này."
        else:
            explanation = f"Found {len(applications)} applications."

        return {
            "success": True,
            "formula_id": formula_id,
            "applications": applications,
            "explanation": explanation,
        }

    except Exception as e:
        logger.error(f"Applications tool error: {e}")
        return {
            "success": False,
            "error": str(e),
            "formula_id": formula_id,
        }


def learning_path_tool(
    target_formula: str,
    known_formulas: Optional[List[str]] = None,
    language: str = "vi",
) -> Dict[str, Any]:
    """
    Tạo lộ trình học tập tối ưu để hiểu một công thức.

    Learning path tool - tạo trình tự học từ cơ bản đến nâng cao,
    bỏ qua những gì học sinh đã biết.

    Args:
        target_formula: ID công thức đích muốn học
        known_formulas: Danh sách ID các công thức đã biết (tùy chọn)
        language: Ngôn ngữ trả về

    Returns:
        Dictionary chứa:
        - success: True/False
        - target: Công thức đích
        - path: Lộ trình học theo thứ tự
        - total_steps: Tổng số bước
        - estimated_time: Thời gian ước tính (phút)

    Examples:
        >>> learning_path_tool("calc_012")  # Học tích phân từng phần
        >>> learning_path_tool("calc_012", known_formulas=["calc_001", "calc_004"])
    """
    system = _get_kg_rag_system()

    if system is None:
        return {
            "success": False,
            "error": "KG-RAG system not initialized",
            "target": target_formula,
        }

    try:
        kg = system["kg"]
        context = system["context"]

        # Use context known formulas if not provided
        if known_formulas is None:
            known_set = context.knowledge_state.known_formulas
        else:
            known_set = set(known_formulas)

        # Get learning path
        path = kg.get_learning_path(target_formula, known_set)

        # Format path
        path_info = []
        for i, f_id in enumerate(path):
            if f_id in kg.formula_db.formulas:
                f = kg.formula_db.formulas[f_id]
                path_info.append({
                    "step": i + 1,
                    "id": f_id,
                    "name": f.name_vi if language == "vi" else f.name,
                    "latex": f.formula,
                    "category": f.category,
                    "is_target": f_id == target_formula,
                    "difficulty": f.difficulty,
                })

        # Estimate time (rough: 10-20 min per formula based on difficulty)
        total_time = sum(
            10 + (p.get("difficulty", 2) * 5) for p in path_info
        )

        # Generate explanation
        if language == "vi":
            explanation = f"Lộ trình học {len(path)} công thức:\n\n"
            for p in path_info:
                marker = "🎯" if p["is_target"] else f"{p['step']}."
                explanation += f"{marker} {p['name']}\n"
                explanation += f"   {p['latex']}\n\n"
            explanation += f"\n⏱️ Thời gian ước tính: {total_time} phút"
        else:
            explanation = f"Learning path with {len(path)} formulas."

        return {
            "success": True,
            "target": target_formula,
            "path": path_info,
            "total_steps": len(path_info),
            "estimated_time_minutes": total_time,
            "explanation": explanation,
        }

    except Exception as e:
        logger.error(f"Learning path tool error: {e}")
        return {
            "success": False,
            "error": str(e),
            "target": target_formula,
        }


def find_similar_tool(
    formula_id: str,
    top_k: int = 5,
    language: str = "vi",
) -> Dict[str, Any]:
    """
    Tìm các công thức tương tự.

    Similar formulas tool - tìm công thức có cấu trúc hoặc ý nghĩa tương tự
    để giúp học sinh so sánh và ghi nhớ.

    Args:
        formula_id: ID công thức cần tìm tương tự
        top_k: Số lượng kết quả
        language: Ngôn ngữ trả về

    Returns:
        Dictionary chứa:
        - success: True/False
        - formula_id: ID công thức gốc
        - similar: Danh sách công thức tương tự với điểm tương đồng

    Examples:
        >>> find_similar_tool("calc_004")  # Tìm công thức tương tự đạo hàm tích
    """
    system = _get_kg_rag_system()

    if system is None:
        return {
            "success": False,
            "error": "KG-RAG system not initialized",
            "formula_id": formula_id,
        }

    try:
        kg = system["kg"]

        # Get similar formulas
        similar = kg.find_similar(formula_id, top_k=top_k)

        # Format results
        similar_formulas = []
        for sim_id, score in similar:
            if sim_id in kg.formula_db.formulas:
                f = kg.formula_db.formulas[sim_id]
                similar_formulas.append({
                    "id": sim_id,
                    "name": f.name_vi if language == "vi" else f.name,
                    "latex": f.formula,
                    "similarity": round(score, 2),
                    "category": f.category,
                })

        # Generate explanation
        if language == "vi":
            if similar_formulas:
                original = kg.formula_db.formulas.get(formula_id)
                orig_name = original.name_vi if original else formula_id
                explanation = f"Các công thức tương tự '{orig_name}':\n"
                for s in similar_formulas:
                    explanation += f"  • {s['name']} (độ tương đồng: {s['similarity']:.0%})\n"
            else:
                explanation = "Không tìm thấy công thức tương tự."
        else:
            explanation = f"Found {len(similar_formulas)} similar formulas."

        return {
            "success": True,
            "formula_id": formula_id,
            "similar": similar_formulas,
            "explanation": explanation,
        }

    except Exception as e:
        logger.error(f"Similar tool error: {e}")
        return {
            "success": False,
            "error": str(e),
            "formula_id": formula_id,
        }


def get_weak_areas_tool(language: str = "vi") -> Dict[str, Any]:
    """
    Phân tích điểm yếu và đề xuất ôn tập.

    Weak areas tool - phân tích lịch sử học tập để tìm những phần
    học sinh cần cải thiện.

    Args:
        language: Ngôn ngữ trả về

    Returns:
        Dictionary chứa:
        - success: True/False
        - weak_formulas: Công thức cần ôn tập
        - weak_topics: Chủ đề cần cải thiện
        - recommendations: Đề xuất học tập

    Examples:
        >>> get_weak_areas_tool()
    """
    system = _get_kg_rag_system()

    if system is None:
        return {
            "success": False,
            "error": "KG-RAG system not initialized",
        }

    try:
        kg = system["kg"]
        context = system["context"]

        # Get weak areas
        weak_areas = context.get_weak_areas()

        # Get recommendations
        recommendations = context.get_recommended_review(kg)

        # Format weak formulas with details
        weak_formulas = []
        for f_id in weak_areas["formulas"]:
            if f_id in kg.formula_db.formulas:
                f = kg.formula_db.formulas[f_id]
                weak_formulas.append({
                    "id": f_id,
                    "name": f.name_vi if language == "vi" else f.name,
                    "category": f.category,
                })

        # Format recommendations
        recommendation_info = []
        for f_id in recommendations:
            if f_id in kg.formula_db.formulas:
                f = kg.formula_db.formulas[f_id]
                recommendation_info.append({
                    "id": f_id,
                    "name": f.name_vi if language == "vi" else f.name,
                })

        # Generate explanation
        if language == "vi":
            explanation = "📊 Phân tích kết quả học tập:\n\n"

            if weak_formulas:
                explanation += "⚠️ Công thức cần ôn tập:\n"
                for wf in weak_formulas[:5]:
                    explanation += f"  • {wf['name']}\n"
            else:
                explanation += "✅ Bạn đang làm tốt! Không có công thức yếu.\n"

            if weak_areas["topics"]:
                explanation += "\n📚 Chủ đề cần cải thiện:\n"
                for t in weak_areas["topics"][:3]:
                    explanation += f"  • {t['topic']}: {t['proficiency']:.0%}\n"

            if recommendation_info:
                explanation += "\n💡 Đề xuất ôn tập:\n"
                for r in recommendation_info[:5]:
                    explanation += f"  • {r['name']}\n"
        else:
            explanation = f"Found {len(weak_formulas)} weak formulas."

        return {
            "success": True,
            "weak_formulas": weak_formulas,
            "weak_topics": weak_areas["topics"],
            "recommendations": recommendation_info,
            "explanation": explanation,
        }

    except Exception as e:
        logger.error(f"Weak areas tool error: {e}")
        return {
            "success": False,
            "error": str(e),
        }


def record_practice_result(
    formula_id: str,
    correct: bool,
    problem_text: str = "",
    topic: str = "",
) -> Dict[str, Any]:
    """
    Ghi nhận kết quả luyện tập.

    Practice recording tool - ghi nhận khi học sinh làm đúng/sai
    để cập nhật trạng thái học tập.

    Args:
        formula_id: ID công thức đã sử dụng
        correct: Đúng hay sai
        problem_text: Đề bài (tùy chọn)
        topic: Chủ đề (tùy chọn)

    Returns:
        Dictionary xác nhận ghi nhận

    Examples:
        >>> record_practice_result("calc_001", correct=True)
    """
    system = _get_kg_rag_system()

    if system is None:
        return {
            "success": False,
            "error": "KG-RAG system not initialized",
        }

    try:
        context = system["context"]

        # Record interaction
        context.add_formula_interaction(
            formula_id=formula_id,
            interaction_type="practiced",
            context=problem_text,
            success=correct,
        )

        # Record problem attempt if we have enough info
        if problem_text or topic:
            context.add_problem_attempt(
                problem_id=f"practice_{formula_id}_{len(context.problem_attempts)}",
                problem_text=problem_text,
                topic=topic or "general",
                correct=correct,
                formulas_used=[formula_id],
            )

        stats = context.get_statistics()

        return {
            "success": True,
            "recorded": {
                "formula_id": formula_id,
                "correct": correct,
            },
            "stats": {
                "total_attempts": stats["total_problems_attempted"],
                "accuracy": f"{stats['accuracy']:.1%}",
                "formulas_mastered": stats["formulas_mastered"],
            },
        }

    except Exception as e:
        logger.error(f"Record practice error: {e}")
        return {
            "success": False,
            "error": str(e),
        }


# Export all tools
__all__ = [
    "semantic_search_tool",
    "find_prerequisites_tool",
    "find_applications_tool",
    "learning_path_tool",
    "find_similar_tool",
    "get_weak_areas_tool",
    "record_practice_result",
]


if __name__ == "__main__":
    print("=" * 60)
    print("KG-RAG Tools Test")
    print("=" * 60)

    # Test semantic search
    print("\n1. Semantic Search: 'đạo hàm hàm hợp'")
    result = semantic_search_tool("đạo hàm hàm hợp", top_k=3)
    if result["success"]:
        for r in result["results"]:
            print(f"   - {r['name']}: {r['score']:.2f}")
    else:
        print(f"   Error: {result.get('error')}")

    # Test prerequisites
    print("\n2. Find Prerequisites: calc_012")
    result = find_prerequisites_tool("calc_012")
    if result["success"]:
        print(result["explanation"])
    else:
        print(f"   Error: {result.get('error')}")

    # Test learning path
    print("\n3. Learning Path: calc_010")
    result = learning_path_tool("calc_010")
    if result["success"]:
        print(f"   Steps: {result['total_steps']}")
        print(f"   Time: {result['estimated_time_minutes']} min")
    else:
        print(f"   Error: {result.get('error')}")

    print("\n" + "=" * 60)
    print("Test complete!")
