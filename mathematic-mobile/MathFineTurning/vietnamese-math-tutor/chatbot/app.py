#!/usr/bin/env python3
"""
Gradio Web Application for Vietnamese Grade 12 Math Tutor.

Provides a user-friendly interface for:
- Asking math questions
- Getting step-by-step solutions
- Switching between simple and agent modes
- Viewing generated graphs
- Calculator quick access
- Formula lookup
"""

import argparse
import os
from pathlib import Path
from typing import Optional, List, Tuple, Generator
import time

import gradio as gr

import sys
sys.path.append(str(Path(__file__).parent.parent))
from config import get_config
from utils.logger import setup_logger, get_logger

# Lazy imports for faster startup
engine = None
agent_engine = None

logger = None


def get_engine(model_path: Optional[str] = None):
    """Lazy load the inference engine."""
    global engine
    if engine is None:
        from chatbot.inference import create_inference_engine
        engine = create_inference_engine(model_path=model_path)
    return engine


def get_agent_engine(model_path: Optional[str] = None):
    """Lazy load the agent inference engine."""
    global agent_engine
    if agent_engine is None:
        from chatbot.agent_inference import create_agent_inference_engine
        agent_engine = create_agent_inference_engine(model_path=model_path)
    return agent_engine


# =============================================================================
# Chat Functions
# =============================================================================

def chat_simple(
    message: str,
    history: List[Tuple[str, str]],
    model_path: Optional[str] = None,
) -> Generator[str, None, None]:
    """
    Handle chat in simple mode (no agent).

    Args:
        message: User message
        history: Chat history
        model_path: Path to model

    Yields:
        Response tokens
    """
    if not message.strip():
        yield "Vui lòng nhập câu hỏi."
        return

    try:
        eng = get_engine(model_path)

        # Convert history to proper format
        chat_history = []
        for user_msg, bot_msg in history:
            chat_history.append({"role": "user", "content": user_msg})
            chat_history.append({"role": "assistant", "content": bot_msg})

        # Stream response
        response = ""
        for token in eng.generate_stream(message, history=chat_history):
            response += token
            yield response

    except Exception as e:
        logger.error(f"Chat error: {e}")
        yield f"Lỗi: {str(e)}\n\nVui lòng thử lại hoặc kiểm tra model."


def chat_agent(
    message: str,
    history: List[Tuple[str, str]],
    model_path: Optional[str] = None,
) -> Tuple[str, Optional[str]]:
    """
    Handle chat in agent mode (with tools).

    Args:
        message: User message
        history: Chat history
        model_path: Path to model

    Returns:
        Tuple of (response, image_path or None)
    """
    if not message.strip():
        return "Vui lòng nhập câu hỏi.", None

    try:
        eng = get_agent_engine(model_path)

        # Solve with agent
        result = eng.solve(message, use_agent=True)

        # Build response
        response = result.answer

        # Add thinking process if available
        if result.thinking_process:
            response += "\n\n---\n**Quá trình suy luận:**\n"
            response += result.thinking_process[:500]  # Limit length
            if len(result.thinking_process) > 500:
                response += "..."

        # Return image if generated
        image_path = result.graphs[0] if result.graphs else None

        return response, image_path

    except Exception as e:
        logger.error(f"Agent chat error: {e}")
        return f"Lỗi: {str(e)}\n\nVui lòng thử lại.", None


# =============================================================================
# Tool Functions
# =============================================================================

def quick_calculate(expression: str) -> str:
    """Quick calculator."""
    if not expression.strip():
        return "Nhập biểu thức cần tính."

    try:
        from agent.tools import calculator_tool
        result = calculator_tool("eval", expression=expression)

        if result["success"]:
            output = f"**Kết quả:** {result['result']}\n\n"
            if result.get("latex"):
                output += f"**LaTeX:** ${result['latex']}$\n\n"
            if result.get("numeric_value"):
                output += f"**Giá trị số:** {result['numeric_value']:.6g}"
            return output
        else:
            return f"Lỗi: {result.get('error', 'Unknown')}"

    except Exception as e:
        return f"Lỗi: {str(e)}"


def calculate_derivative(expression: str, variable: str = "x", order: int = 1) -> str:
    """Calculate derivative."""
    if not expression.strip():
        return "Nhập hàm số cần tính đạo hàm."

    try:
        from agent.tools import calculator_tool
        result = calculator_tool(
            "derivative",
            expression=expression,
            variable=variable,
            order=int(order),
        )

        if result["success"]:
            order_str = f"^{order}" if order > 1 else "'"
            return f"**y{order_str} = {result['result']}**\n\nLaTeX: ${result.get('latex', '')}$"
        else:
            return f"Lỗi: {result.get('error', 'Unknown')}"

    except Exception as e:
        return f"Lỗi: {str(e)}"


def calculate_integral(
    expression: str,
    variable: str = "x",
    lower: str = "",
    upper: str = "",
) -> str:
    """Calculate integral."""
    if not expression.strip():
        return "Nhập hàm số cần tính tích phân."

    try:
        from agent.tools import calculator_tool

        kwargs = {
            "operation": "integral",
            "expression": expression,
            "variable": variable,
        }

        if lower.strip() and upper.strip():
            kwargs["lower"] = lower
            kwargs["upper"] = upper

        result = calculator_tool(**kwargs)

        if result["success"]:
            if lower.strip() and upper.strip():
                return f"**∫[{lower},{upper}] {expression} d{variable} = {result['result']}**"
            else:
                return f"**∫{expression} d{variable} = {result['result']} + C**"
        else:
            return f"Lỗi: {result.get('error', 'Unknown')}"

    except Exception as e:
        return f"Lỗi: {str(e)}"


def solve_equation(equation: str, variable: str = "x") -> str:
    """Solve equation."""
    if not equation.strip():
        return "Nhập phương trình cần giải."

    try:
        from agent.tools import calculator_tool
        result = calculator_tool(
            "solve",
            expression=equation,
            variable=variable,
        )

        if result["success"]:
            return f"**Nghiệm: {variable} = {result['result']}**"
        else:
            return f"Lỗi: {result.get('error', 'Unknown')}"

    except Exception as e:
        return f"Lỗi: {str(e)}"


def search_formula(query: str) -> str:
    """Search formulas."""
    if not query.strip():
        return "Nhập từ khóa tìm kiếm công thức."

    try:
        from agent.tools import formula_db_tool
        result = formula_db_tool(
            action="search",
            query=query,
            max_results=5,
            language="vi",
        )

        if result["success"] and result.get("results"):
            output = f"**Tìm thấy {result['count']} công thức:**\n\n"
            for i, r in enumerate(result["results"], 1):
                output += f"{i}. **{r['name']}**\n"
                output += f"   - Công thức: `{r['formula']}`\n"
                output += f"   - {r['description']}\n\n"
            return output
        else:
            return f"Không tìm thấy công thức cho: {query}"

    except Exception as e:
        return f"Lỗi: {str(e)}"


def plot_function(
    expression: str,
    x_min: float = -10,
    x_max: float = 10,
) -> Tuple[Optional[str], str]:
    """Plot a function."""
    if not expression.strip():
        return None, "Nhập hàm số cần vẽ."

    try:
        from agent.tools import plotter_tool
        result = plotter_tool(
            action="plot_function",
            expression=expression,
            x_range=(float(x_min), float(x_max)),
            language="vi",
        )

        if result["success"]:
            metadata = result.get("metadata", {})
            critical = metadata.get("critical_points", {})

            info = f"**Đồ thị: y = {expression}**\n\n"

            if critical.get("maxima"):
                info += f"Cực đại: {critical['maxima']}\n"
            if critical.get("minima"):
                info += f"Cực tiểu: {critical['minima']}\n"
            if critical.get("roots"):
                info += f"Nghiệm: {critical['roots']}\n"

            return result.get("image_path"), info
        else:
            return None, f"Lỗi: {result.get('error', 'Unknown')}"

    except Exception as e:
        return None, f"Lỗi: {str(e)}"


def calculate_probability(n: int, k: int, calc_type: str) -> str:
    """Calculate combination or permutation."""
    try:
        from agent.tools import calculator_tool

        if calc_type == "combination":
            result = calculator_tool("combination", n=int(n), k=int(k))
            if result["success"]:
                return f"**C({n},{k}) = {result['result']}**"
        else:
            result = calculator_tool("permutation", n=int(n), k=int(k))
            if result["success"]:
                return f"**P({n},{k}) = {result['result']}**"

        return f"Lỗi: {result.get('error', 'Unknown')}"

    except Exception as e:
        return f"Lỗi: {str(e)}"


# =============================================================================
# UI Construction
# =============================================================================

def create_ui(model_path: Optional[str] = None) -> gr.Blocks:
    """Create the Gradio UI."""

    # Custom CSS
    css = """
    .chatbot {font-size: 14px;}
    .math-display {font-family: 'Computer Modern', serif;}
    .tool-box {background: #f7f7f7; padding: 10px; border-radius: 8px;}
    """

    with gr.Blocks(
        title="Gia Sư Toán Lớp 12",
        theme=gr.themes.Soft(),
        css=css,
    ) as app:

        gr.Markdown("""
        # 📐 Gia Sư Toán Học Lớp 12
        **Vietnamese Grade 12 Math Tutor**

        Hỏi bất kỳ câu hỏi toán học nào về chương trình lớp 12!
        - Giải tích (đạo hàm, tích phân, giới hạn)
        - Hình học không gian
        - Hình học tọa độ trong không gian
        - Xác suất và thống kê
        """)

        with gr.Tabs() as tabs:

            # =========== Chat Tab ===========
            with gr.TabItem("💬 Chat", id="chat"):
                with gr.Row():
                    with gr.Column(scale=2):
                        mode_selector = gr.Radio(
                            choices=["Đơn giản (Simple)", "Agent (Có công cụ)"],
                            value="Agent (Có công cụ)",
                            label="Chế độ / Mode",
                        )

                        chatbot = gr.Chatbot(
                            label="Cuộc trò chuyện",
                            height=500,
                            elem_classes=["chatbot"],
                        )

                        with gr.Row():
                            msg_input = gr.Textbox(
                                placeholder="Nhập câu hỏi toán học...",
                                label="Câu hỏi",
                                scale=4,
                            )
                            submit_btn = gr.Button("Gửi", variant="primary", scale=1)

                        with gr.Row():
                            clear_btn = gr.Button("Xóa lịch sử")
                            example_btn = gr.Button("Ví dụ")

                    with gr.Column(scale=1):
                        gr.Markdown("### 📊 Đồ thị")
                        plot_output = gr.Image(
                            label="Đồ thị",
                            type="filepath",
                        )

                # Example questions
                examples = gr.Examples(
                    examples=[
                        "Tìm đạo hàm của hàm số y = x³ - 3x² + 2x",
                        "Tính tích phân ∫₀¹ x² dx",
                        "Giải phương trình: x² - 5x + 6 = 0",
                        "Tính C(10, 3)",
                        "Tìm giới hạn lim(x→0) sin(x)/x",
                        "Khảo sát sự biến thiên và vẽ đồ thị hàm số y = x³ - 3x",
                    ],
                    inputs=msg_input,
                )

                # Chat logic
                def respond(message, history, mode):
                    if "Agent" in mode:
                        response, image = chat_agent(message, history, model_path)
                        history.append((message, response))
                        return history, "", image
                    else:
                        # Simple mode with streaming
                        history.append((message, ""))
                        for response in chat_simple(message, history[:-1], model_path):
                            history[-1] = (message, response)
                            yield history, "", None
                        return history, "", None

                submit_btn.click(
                    respond,
                    [msg_input, chatbot, mode_selector],
                    [chatbot, msg_input, plot_output],
                )

                msg_input.submit(
                    respond,
                    [msg_input, chatbot, mode_selector],
                    [chatbot, msg_input, plot_output],
                )

                clear_btn.click(lambda: ([], None), None, [chatbot, plot_output])

            # =========== Calculator Tab ===========
            with gr.TabItem("🧮 Máy tính", id="calculator"):
                gr.Markdown("### Máy tính toán học")

                with gr.Row():
                    with gr.Column():
                        gr.Markdown("#### Tính biểu thức")
                        calc_input = gr.Textbox(
                            label="Biểu thức",
                            placeholder="VD: 2^3 + sqrt(16) - sin(pi/2)",
                        )
                        calc_btn = gr.Button("Tính", variant="primary")
                        calc_output = gr.Markdown()
                        calc_btn.click(quick_calculate, calc_input, calc_output)

                    with gr.Column():
                        gr.Markdown("#### Đạo hàm")
                        deriv_input = gr.Textbox(
                            label="Hàm số f(x)",
                            placeholder="VD: x^3 - 3*x^2 + 2*x",
                        )
                        deriv_var = gr.Textbox(label="Biến", value="x")
                        deriv_order = gr.Number(label="Bậc đạo hàm", value=1, minimum=1, maximum=5)
                        deriv_btn = gr.Button("Tính đạo hàm", variant="primary")
                        deriv_output = gr.Markdown()
                        deriv_btn.click(
                            calculate_derivative,
                            [deriv_input, deriv_var, deriv_order],
                            deriv_output,
                        )

                with gr.Row():
                    with gr.Column():
                        gr.Markdown("#### Tích phân")
                        integ_input = gr.Textbox(
                            label="Hàm số f(x)",
                            placeholder="VD: x^2",
                        )
                        integ_var = gr.Textbox(label="Biến", value="x")
                        with gr.Row():
                            integ_lower = gr.Textbox(label="Cận dưới (tùy chọn)")
                            integ_upper = gr.Textbox(label="Cận trên (tùy chọn)")
                        integ_btn = gr.Button("Tính tích phân", variant="primary")
                        integ_output = gr.Markdown()
                        integ_btn.click(
                            calculate_integral,
                            [integ_input, integ_var, integ_lower, integ_upper],
                            integ_output,
                        )

                    with gr.Column():
                        gr.Markdown("#### Giải phương trình")
                        eq_input = gr.Textbox(
                            label="Phương trình",
                            placeholder="VD: x^2 - 5*x + 6 = 0",
                        )
                        eq_var = gr.Textbox(label="Biến", value="x")
                        eq_btn = gr.Button("Giải", variant="primary")
                        eq_output = gr.Markdown()
                        eq_btn.click(solve_equation, [eq_input, eq_var], eq_output)

            # =========== Formula Tab ===========
            with gr.TabItem("📚 Công thức", id="formulas"):
                gr.Markdown("### Tra cứu công thức")

                formula_query = gr.Textbox(
                    label="Tìm kiếm",
                    placeholder="VD: đạo hàm, tích phân, giới hạn...",
                )
                formula_btn = gr.Button("Tìm", variant="primary")
                formula_output = gr.Markdown()
                formula_btn.click(search_formula, formula_query, formula_output)

                gr.Markdown("### Danh mục công thức")
                with gr.Row():
                    for cat in ["Giải tích", "Hình học", "Lượng giác", "Xác suất"]:
                        cat_btn = gr.Button(cat)
                        cat_btn.click(
                            lambda c=cat: search_formula(c),
                            None,
                            formula_output,
                        )

            # =========== Graph Tab ===========
            with gr.TabItem("📈 Đồ thị", id="graph"):
                gr.Markdown("### Vẽ đồ thị hàm số")

                with gr.Row():
                    with gr.Column():
                        plot_expr = gr.Textbox(
                            label="Hàm số y = f(x)",
                            placeholder="VD: x^3 - 3*x^2 + 2*x",
                        )
                        with gr.Row():
                            plot_xmin = gr.Number(label="x min", value=-10)
                            plot_xmax = gr.Number(label="x max", value=10)
                        plot_btn = gr.Button("Vẽ đồ thị", variant="primary")

                    with gr.Column():
                        graph_image = gr.Image(label="Đồ thị", type="filepath")
                        graph_info = gr.Markdown()

                plot_btn.click(
                    plot_function,
                    [plot_expr, plot_xmin, plot_xmax],
                    [graph_image, graph_info],
                )

            # =========== Probability Tab ===========
            with gr.TabItem("🎲 Xác suất", id="probability"):
                gr.Markdown("### Tính toán tổ hợp - Chỉnh hợp")

                with gr.Row():
                    prob_n = gr.Number(label="n", value=10, minimum=0)
                    prob_k = gr.Number(label="k", value=3, minimum=0)
                    prob_type = gr.Radio(
                        choices=["combination", "permutation"],
                        value="combination",
                        label="Loại",
                    )

                prob_btn = gr.Button("Tính", variant="primary")
                prob_output = gr.Markdown()
                prob_btn.click(
                    calculate_probability,
                    [prob_n, prob_k, prob_type],
                    prob_output,
                )

                gr.Markdown("""
                ### Công thức
                - **Tổ hợp C(n,k)** = n! / (k!(n-k)!) - Chọn k phần tử từ n (không quan tâm thứ tự)
                - **Chỉnh hợp P(n,k)** = n! / (n-k)! - Chọn và sắp xếp k phần tử từ n
                """)

            # =========== About Tab ===========
            with gr.TabItem("ℹ️ Giới thiệu", id="about"):
                gr.Markdown("""
                ## Vietnamese Grade 12 Math Tutor

                ### Tính năng
                - 💬 **Chat thông minh**: Hỏi đáp với AI về toán lớp 12
                - 🧮 **Máy tính**: Tính toán nhanh các biểu thức
                - 📚 **Tra cứu công thức**: Cơ sở dữ liệu công thức đầy đủ
                - 📈 **Vẽ đồ thị**: Trực quan hóa hàm số
                - 🎲 **Xác suất**: Tính toán tổ hợp, chỉnh hợp

                ### Chế độ Chat
                - **Đơn giản**: Sử dụng trực tiếp mô hình AI
                - **Agent**: Sử dụng AI kết hợp với công cụ tính toán để có kết quả chính xác

                ### Chủ đề hỗ trợ
                - Giải tích (đạo hàm, tích phân, giới hạn)
                - Hình học không gian
                - Hình học tọa độ trong không gian
                - Xác suất và thống kê

                ### Công nghệ
                - Fine-tuned Qwen2.5-Math-7B-Instruct
                - ReAct Agent với SymPy
                - 8-bit Quantization cho RTX 3060 12GB

                ---
                *Dự án được phát triển cho học sinh lớp 12 Việt Nam*
                """)

    return app


# =============================================================================
# Main
# =============================================================================

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Vietnamese Grade 12 Math Tutor")

    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Path to trained model (uses base model if not specified)",
    )
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Host to run the server on",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=7860,
        help="Port to run the server on",
    )
    parser.add_argument(
        "--share",
        action="store_true",
        help="Create a public share link",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode",
    )

    return parser.parse_args()


def main():
    """Main entry point."""
    global logger

    args = parse_args()

    # Setup logging
    setup_logger("app")
    logger = get_logger("app")

    logger.info("Starting Vietnamese Grade 12 Math Tutor...")

    # Create and launch UI
    app = create_ui(model_path=args.model)

    logger.info(f"Launching on http://{args.host}:{args.port}")

    app.launch(
        server_name=args.host,
        server_port=args.port,
        share=args.share,
        debug=args.debug,
    )


if __name__ == "__main__":
    main()
