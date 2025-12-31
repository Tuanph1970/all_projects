"""
Graph Plotter tool for Vietnamese Grade 12 Math Tutor.

Provides mathematical graph plotting functionality:
- 2D function plotting
- Multiple functions comparison
- Critical points visualization
- Coordinate geometry plotting
- Statistical plots
"""

import io
import base64
import math
from typing import Dict, Any, Optional, List, Tuple, Union
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Rectangle, Polygon
from matplotlib.lines import Line2D

import sympy as sp
from sympy import (
    symbols, Symbol, lambdify,
    sin, cos, tan, exp, log, sqrt, Abs,
    diff, solve,
)
from sympy.parsing.sympy_parser import (
    parse_expr,
    standard_transformations,
    implicit_multiplication_application,
    convert_xor,
)

import sys
sys.path.append(str(Path(__file__).parent.parent.parent))
from utils.logger import get_logger

logger = get_logger("plotter")


class PlotType(Enum):
    """Types of plots."""
    FUNCTION_2D = "function_2d"
    MULTIPLE_FUNCTIONS = "multiple_functions"
    DERIVATIVE = "derivative"
    INTEGRAL_AREA = "integral_area"
    PARAMETRIC = "parametric"
    POLAR = "polar"
    SCATTER = "scatter"
    HISTOGRAM = "histogram"
    GEOMETRY = "geometry"


@dataclass
class PlotResult:
    """Result of a plot operation."""
    success: bool
    plot_type: PlotType
    image_base64: Optional[str] = None
    image_path: Optional[str] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = None


class MathPlotter:
    """
    Mathematical graph plotter using Matplotlib.

    Optimized for Vietnamese Grade 12 math visualization.
    """

    # Common symbols
    x, y, t = symbols('x y t')

    # Transformation rules
    TRANSFORMATIONS = (
        standard_transformations +
        (implicit_multiplication_application, convert_xor)
    )

    # Vietnamese labels
    VIETNAMESE_LABELS = {
        "x_axis": "Trục x",
        "y_axis": "Trục y",
        "function": "Hàm số",
        "derivative": "Đạo hàm",
        "integral": "Tích phân",
        "area": "Diện tích",
        "maximum": "Cực đại",
        "minimum": "Cực tiểu",
        "inflection": "Điểm uốn",
        "root": "Nghiệm",
    }

    def __init__(
        self,
        output_dir: Optional[Path] = None,
        style: str = "seaborn-v0_8-whitegrid",
        figsize: Tuple[int, int] = (10, 8),
        dpi: int = 100,
    ):
        """
        Initialize the plotter.

        Args:
            output_dir: Directory to save plots
            style: Matplotlib style
            figsize: Default figure size
            dpi: Resolution
        """
        self.output_dir = output_dir or Path("output/plots")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.figsize = figsize
        self.dpi = dpi

        # Try to set style, fallback to default if not available
        try:
            plt.style.use(style)
        except:
            pass

        self.local_dict = {
            'x': self.x, 'y': self.y, 't': self.t,
            'pi': sp.pi, 'e': sp.E,
            'sin': sp.sin, 'cos': sp.cos, 'tan': sp.tan,
            'exp': sp.exp, 'log': sp.log, 'ln': sp.ln,
            'sqrt': sp.sqrt, 'abs': sp.Abs,
        }

        logger.info("Math plotter initialized")

    def _parse_expression(self, expr_str: str) -> sp.Expr:
        """Parse a string expression into SymPy expression."""
        expr_str = expr_str.strip()
        expr_str = expr_str.replace('^', '**')

        try:
            return parse_expr(
                expr_str,
                local_dict=self.local_dict,
                transformations=self.TRANSFORMATIONS,
            )
        except Exception as e:
            logger.error(f"Failed to parse expression: {expr_str}, error: {e}")
            raise ValueError(f"Cannot parse expression: {expr_str}")

    def _to_numpy_func(self, expr: sp.Expr, var: Symbol = None) -> callable:
        """Convert SymPy expression to numpy function."""
        if var is None:
            var = self.x
        return lambdify(var, expr, modules=['numpy'])

    def _save_figure(
        self,
        fig: plt.Figure,
        filename: str,
        return_base64: bool = True,
    ) -> Tuple[Optional[str], Optional[str]]:
        """Save figure and optionally return base64."""
        # Save to file
        filepath = self.output_dir / filename
        fig.savefig(filepath, dpi=self.dpi, bbox_inches='tight')
        logger.info(f"Plot saved to: {filepath}")

        # Generate base64 if requested
        base64_str = None
        if return_base64:
            buf = io.BytesIO()
            fig.savefig(buf, format='png', dpi=self.dpi, bbox_inches='tight')
            buf.seek(0)
            base64_str = base64.b64encode(buf.read()).decode('utf-8')
            buf.close()

        plt.close(fig)
        return base64_str, str(filepath)

    def plot_function(
        self,
        expression: str,
        x_range: Tuple[float, float] = (-10, 10),
        y_range: Optional[Tuple[float, float]] = None,
        title: Optional[str] = None,
        xlabel: str = "x",
        ylabel: str = "y",
        show_grid: bool = True,
        show_axes: bool = True,
        show_critical_points: bool = True,
        color: str = "blue",
        language: str = "vi",
    ) -> PlotResult:
        """
        Plot a 2D function.

        Args:
            expression: Function expression (e.g., "x^2 - 2*x + 1")
            x_range: (x_min, x_max)
            y_range: (y_min, y_max) or None for auto
            title: Plot title
            xlabel, ylabel: Axis labels
            show_grid: Show grid lines
            show_axes: Show x and y axes
            show_critical_points: Mark critical points
            color: Line color
            language: "vi" for Vietnamese labels

        Returns:
            PlotResult with image data
        """
        try:
            # Parse expression
            expr = self._parse_expression(expression)
            func = self._to_numpy_func(expr)

            # Create figure
            fig, ax = plt.subplots(figsize=self.figsize)

            # Generate x values
            x_vals = np.linspace(x_range[0], x_range[1], 1000)

            # Calculate y values with error handling
            with np.errstate(divide='ignore', invalid='ignore'):
                y_vals = func(x_vals)
                # Replace inf/nan with nan for cleaner plotting
                y_vals = np.where(np.isfinite(y_vals), y_vals, np.nan)

            # Plot the function
            ax.plot(x_vals, y_vals, color=color, linewidth=2, label=f"f(x) = {expression}")

            # Set ranges
            if y_range:
                ax.set_ylim(y_range)
            else:
                # Auto y-range with some padding
                valid_y = y_vals[np.isfinite(y_vals)]
                if len(valid_y) > 0:
                    y_min, y_max = np.min(valid_y), np.max(valid_y)
                    padding = (y_max - y_min) * 0.1
                    ax.set_ylim(y_min - padding, y_max + padding)

            ax.set_xlim(x_range)

            # Show axes
            if show_axes:
                ax.axhline(y=0, color='k', linewidth=0.5)
                ax.axvline(x=0, color='k', linewidth=0.5)

            # Grid
            if show_grid:
                ax.grid(True, alpha=0.3)

            # Critical points
            critical_data = {}
            if show_critical_points:
                critical_data = self._mark_critical_points(ax, expr, x_range, language)

            # Labels
            if language == "vi":
                xlabel = xlabel or self.VIETNAMESE_LABELS.get("x_axis", "x")
                ylabel = ylabel or self.VIETNAMESE_LABELS.get("y_axis", "y")

            ax.set_xlabel(xlabel, fontsize=12)
            ax.set_ylabel(ylabel, fontsize=12)

            # Title
            if title:
                ax.set_title(title, fontsize=14)
            else:
                ax.set_title(f"Đồ thị hàm số y = {expression}" if language == "vi"
                            else f"Graph of y = {expression}", fontsize=14)

            ax.legend(loc='best')

            # Save
            filename = f"function_{hash(expression) % 10000}.png"
            base64_img, filepath = self._save_figure(fig, filename)

            return PlotResult(
                success=True,
                plot_type=PlotType.FUNCTION_2D,
                image_base64=base64_img,
                image_path=filepath,
                metadata={
                    "expression": expression,
                    "x_range": x_range,
                    "critical_points": critical_data,
                },
            )

        except Exception as e:
            logger.error(f"Plot function failed: {e}")
            return PlotResult(
                success=False,
                plot_type=PlotType.FUNCTION_2D,
                error_message=str(e),
            )

    def _mark_critical_points(
        self,
        ax: plt.Axes,
        expr: sp.Expr,
        x_range: Tuple[float, float],
        language: str = "vi",
    ) -> Dict[str, List]:
        """Mark critical points on the plot."""
        critical_data = {
            "maxima": [],
            "minima": [],
            "roots": [],
            "inflection": [],
        }

        try:
            func = self._to_numpy_func(expr)

            # Find roots
            try:
                roots = solve(expr, self.x)
                for root in roots:
                    try:
                        root_val = float(root.evalf())
                        if x_range[0] <= root_val <= x_range[1]:
                            ax.plot(root_val, 0, 'go', markersize=8)
                            ax.annotate(
                                f"{'Nghiệm' if language == 'vi' else 'Root'}: ({root_val:.2f}, 0)",
                                (root_val, 0), textcoords="offset points",
                                xytext=(10, 10), fontsize=9,
                            )
                            critical_data["roots"].append(root_val)
                    except:
                        pass
            except:
                pass

            # Find critical points (first derivative = 0)
            try:
                deriv1 = diff(expr, self.x)
                critical_points = solve(deriv1, self.x)
                deriv2 = diff(deriv1, self.x)

                for cp in critical_points:
                    try:
                        cp_val = float(cp.evalf())
                        if x_range[0] <= cp_val <= x_range[1]:
                            y_val = float(expr.subs(self.x, cp).evalf())
                            d2_val = float(deriv2.subs(self.x, cp).evalf())

                            if d2_val < 0:  # Maximum
                                ax.plot(cp_val, y_val, 'r^', markersize=10)
                                label = f"{'Cực đại' if language == 'vi' else 'Max'}: ({cp_val:.2f}, {y_val:.2f})"
                                ax.annotate(label, (cp_val, y_val), textcoords="offset points",
                                          xytext=(10, 10), fontsize=9, color='red')
                                critical_data["maxima"].append((cp_val, y_val))
                            elif d2_val > 0:  # Minimum
                                ax.plot(cp_val, y_val, 'bv', markersize=10)
                                label = f"{'Cực tiểu' if language == 'vi' else 'Min'}: ({cp_val:.2f}, {y_val:.2f})"
                                ax.annotate(label, (cp_val, y_val), textcoords="offset points",
                                          xytext=(10, -15), fontsize=9, color='blue')
                                critical_data["minima"].append((cp_val, y_val))
                    except:
                        pass
            except:
                pass

            # Find inflection points (second derivative = 0)
            try:
                inflection_points = solve(deriv2, self.x)
                for ip in inflection_points:
                    try:
                        ip_val = float(ip.evalf())
                        if x_range[0] <= ip_val <= x_range[1]:
                            y_val = float(expr.subs(self.x, ip).evalf())
                            ax.plot(ip_val, y_val, 'ms', markersize=8)
                            label = f"{'Điểm uốn' if language == 'vi' else 'Inflection'}: ({ip_val:.2f}, {y_val:.2f})"
                            ax.annotate(label, (ip_val, y_val), textcoords="offset points",
                                      xytext=(10, 5), fontsize=9, color='purple')
                            critical_data["inflection"].append((ip_val, y_val))
                    except:
                        pass
            except:
                pass

        except Exception as e:
            logger.warning(f"Error finding critical points: {e}")

        return critical_data

    def plot_multiple_functions(
        self,
        expressions: List[str],
        x_range: Tuple[float, float] = (-10, 10),
        y_range: Optional[Tuple[float, float]] = None,
        title: Optional[str] = None,
        labels: Optional[List[str]] = None,
        colors: Optional[List[str]] = None,
        language: str = "vi",
    ) -> PlotResult:
        """
        Plot multiple functions on the same graph.

        Args:
            expressions: List of function expressions
            x_range: (x_min, x_max)
            y_range: (y_min, y_max) or None for auto
            title: Plot title
            labels: List of labels for each function
            colors: List of colors for each function
            language: "vi" for Vietnamese labels

        Returns:
            PlotResult with image data
        """
        try:
            if not colors:
                colors = plt.cm.tab10.colors[:len(expressions)]
            if not labels:
                labels = [f"f{i+1}(x) = {expr}" for i, expr in enumerate(expressions)]

            fig, ax = plt.subplots(figsize=self.figsize)
            x_vals = np.linspace(x_range[0], x_range[1], 1000)

            for expr_str, label, color in zip(expressions, labels, colors):
                expr = self._parse_expression(expr_str)
                func = self._to_numpy_func(expr)

                with np.errstate(divide='ignore', invalid='ignore'):
                    y_vals = func(x_vals)
                    y_vals = np.where(np.isfinite(y_vals), y_vals, np.nan)

                ax.plot(x_vals, y_vals, color=color, linewidth=2, label=label)

            ax.axhline(y=0, color='k', linewidth=0.5)
            ax.axvline(x=0, color='k', linewidth=0.5)
            ax.grid(True, alpha=0.3)
            ax.set_xlim(x_range)

            if y_range:
                ax.set_ylim(y_range)

            ax.set_xlabel("x", fontsize=12)
            ax.set_ylabel("y", fontsize=12)
            ax.set_title(title or ("So sánh các hàm số" if language == "vi" else "Function Comparison"), fontsize=14)
            ax.legend(loc='best')

            filename = f"multi_functions_{hash(str(expressions)) % 10000}.png"
            base64_img, filepath = self._save_figure(fig, filename)

            return PlotResult(
                success=True,
                plot_type=PlotType.MULTIPLE_FUNCTIONS,
                image_base64=base64_img,
                image_path=filepath,
                metadata={"expressions": expressions, "x_range": x_range},
            )

        except Exception as e:
            logger.error(f"Plot multiple functions failed: {e}")
            return PlotResult(
                success=False,
                plot_type=PlotType.MULTIPLE_FUNCTIONS,
                error_message=str(e),
            )

    def plot_derivative(
        self,
        expression: str,
        x_range: Tuple[float, float] = (-10, 10),
        show_original: bool = True,
        language: str = "vi",
    ) -> PlotResult:
        """
        Plot a function and its derivative.

        Args:
            expression: Function expression
            x_range: (x_min, x_max)
            show_original: Also plot the original function
            language: "vi" for Vietnamese labels

        Returns:
            PlotResult with image data
        """
        try:
            expr = self._parse_expression(expression)
            deriv_expr = diff(expr, self.x)

            expressions = [expression, str(deriv_expr)] if show_original else [str(deriv_expr)]
            labels = [
                f"f(x) = {expression}",
                f"f'(x) = {deriv_expr}",
            ] if show_original else [f"f'(x) = {deriv_expr}"]
            colors = ['blue', 'red'] if show_original else ['red']

            fig, ax = plt.subplots(figsize=self.figsize)
            x_vals = np.linspace(x_range[0], x_range[1], 1000)

            for expr_str, label, color in zip(expressions, labels, colors):
                parsed_expr = self._parse_expression(expr_str)
                func = self._to_numpy_func(parsed_expr)

                with np.errstate(divide='ignore', invalid='ignore'):
                    y_vals = func(x_vals)
                    y_vals = np.where(np.isfinite(y_vals), y_vals, np.nan)

                ax.plot(x_vals, y_vals, color=color, linewidth=2, label=label)

            ax.axhline(y=0, color='k', linewidth=0.5)
            ax.axvline(x=0, color='k', linewidth=0.5)
            ax.grid(True, alpha=0.3)
            ax.set_xlim(x_range)

            ax.set_xlabel("x", fontsize=12)
            ax.set_ylabel("y", fontsize=12)
            title = f"Hàm số và đạo hàm của y = {expression}" if language == "vi" else f"Function and Derivative of y = {expression}"
            ax.set_title(title, fontsize=14)
            ax.legend(loc='best')

            filename = f"derivative_{hash(expression) % 10000}.png"
            base64_img, filepath = self._save_figure(fig, filename)

            return PlotResult(
                success=True,
                plot_type=PlotType.DERIVATIVE,
                image_base64=base64_img,
                image_path=filepath,
                metadata={
                    "expression": expression,
                    "derivative": str(deriv_expr),
                    "x_range": x_range,
                },
            )

        except Exception as e:
            logger.error(f"Plot derivative failed: {e}")
            return PlotResult(
                success=False,
                plot_type=PlotType.DERIVATIVE,
                error_message=str(e),
            )

    def plot_integral_area(
        self,
        expression: str,
        lower: float,
        upper: float,
        x_range: Optional[Tuple[float, float]] = None,
        language: str = "vi",
    ) -> PlotResult:
        """
        Plot a function with shaded area for definite integral.

        Args:
            expression: Function expression
            lower: Lower bound of integration
            upper: Upper bound of integration
            x_range: Full x range for the plot
            language: "vi" for Vietnamese labels

        Returns:
            PlotResult with image data
        """
        try:
            if x_range is None:
                padding = (upper - lower) * 0.5
                x_range = (lower - padding, upper + padding)

            expr = self._parse_expression(expression)
            func = self._to_numpy_func(expr)

            # Calculate integral
            from sympy import integrate
            integral_value = integrate(expr, (self.x, lower, upper))
            integral_numeric = float(integral_value.evalf())

            fig, ax = plt.subplots(figsize=self.figsize)

            # Plot full function
            x_full = np.linspace(x_range[0], x_range[1], 1000)
            with np.errstate(divide='ignore', invalid='ignore'):
                y_full = func(x_full)
                y_full = np.where(np.isfinite(y_full), y_full, np.nan)

            ax.plot(x_full, y_full, 'b-', linewidth=2, label=f"f(x) = {expression}")

            # Shade the integral area
            x_shade = np.linspace(lower, upper, 500)
            y_shade = func(x_shade)
            ax.fill_between(x_shade, y_shade, alpha=0.3, color='blue',
                          label=f"{'Diện tích' if language == 'vi' else 'Area'} = {integral_numeric:.4f}")

            # Mark bounds
            ax.axvline(x=lower, color='green', linestyle='--', linewidth=1)
            ax.axvline(x=upper, color='green', linestyle='--', linewidth=1)

            ax.axhline(y=0, color='k', linewidth=0.5)
            ax.axvline(x=0, color='k', linewidth=0.5)
            ax.grid(True, alpha=0.3)
            ax.set_xlim(x_range)

            ax.set_xlabel("x", fontsize=12)
            ax.set_ylabel("y", fontsize=12)
            title = f"Tích phân xác định ∫[{lower}, {upper}] {expression} dx" if language == "vi" else f"Definite Integral ∫[{lower}, {upper}] {expression} dx"
            ax.set_title(title, fontsize=14)
            ax.legend(loc='best')

            filename = f"integral_{hash(expression + str(lower) + str(upper)) % 10000}.png"
            base64_img, filepath = self._save_figure(fig, filename)

            return PlotResult(
                success=True,
                plot_type=PlotType.INTEGRAL_AREA,
                image_base64=base64_img,
                image_path=filepath,
                metadata={
                    "expression": expression,
                    "lower": lower,
                    "upper": upper,
                    "integral_value": integral_numeric,
                },
            )

        except Exception as e:
            logger.error(f"Plot integral area failed: {e}")
            return PlotResult(
                success=False,
                plot_type=PlotType.INTEGRAL_AREA,
                error_message=str(e),
            )

    def plot_scatter(
        self,
        x_data: List[float],
        y_data: List[float],
        title: Optional[str] = None,
        xlabel: str = "x",
        ylabel: str = "y",
        show_regression: bool = False,
        language: str = "vi",
    ) -> PlotResult:
        """
        Create a scatter plot.

        Args:
            x_data: X coordinates
            y_data: Y coordinates
            title: Plot title
            xlabel, ylabel: Axis labels
            show_regression: Show linear regression line
            language: "vi" for Vietnamese labels

        Returns:
            PlotResult with image data
        """
        try:
            fig, ax = plt.subplots(figsize=self.figsize)

            ax.scatter(x_data, y_data, alpha=0.7, s=50)

            metadata = {"x_data": x_data, "y_data": y_data}

            if show_regression and len(x_data) > 1:
                # Linear regression
                x_arr = np.array(x_data)
                y_arr = np.array(y_data)
                coeffs = np.polyfit(x_arr, y_arr, 1)
                reg_line = np.poly1d(coeffs)
                x_reg = np.linspace(min(x_data), max(x_data), 100)
                ax.plot(x_reg, reg_line(x_reg), 'r-', linewidth=2,
                       label=f"y = {coeffs[0]:.2f}x + {coeffs[1]:.2f}")
                ax.legend()
                metadata["regression"] = {"slope": coeffs[0], "intercept": coeffs[1]}

            ax.grid(True, alpha=0.3)
            ax.set_xlabel(xlabel, fontsize=12)
            ax.set_ylabel(ylabel, fontsize=12)
            ax.set_title(title or ("Biểu đồ phân tán" if language == "vi" else "Scatter Plot"), fontsize=14)

            filename = f"scatter_{hash(str(x_data) + str(y_data)) % 10000}.png"
            base64_img, filepath = self._save_figure(fig, filename)

            return PlotResult(
                success=True,
                plot_type=PlotType.SCATTER,
                image_base64=base64_img,
                image_path=filepath,
                metadata=metadata,
            )

        except Exception as e:
            logger.error(f"Plot scatter failed: {e}")
            return PlotResult(
                success=False,
                plot_type=PlotType.SCATTER,
                error_message=str(e),
            )

    def plot_histogram(
        self,
        data: List[float],
        bins: int = 10,
        title: Optional[str] = None,
        xlabel: str = "Giá trị",
        ylabel: str = "Tần số",
        show_stats: bool = True,
        language: str = "vi",
    ) -> PlotResult:
        """
        Create a histogram.

        Args:
            data: Data values
            bins: Number of bins
            title: Plot title
            xlabel, ylabel: Axis labels
            show_stats: Show mean and std on plot
            language: "vi" for Vietnamese labels

        Returns:
            PlotResult with image data
        """
        try:
            fig, ax = plt.subplots(figsize=self.figsize)

            data_arr = np.array(data)
            ax.hist(data_arr, bins=bins, edgecolor='black', alpha=0.7)

            metadata = {
                "data_count": len(data),
                "bins": bins,
                "mean": float(np.mean(data_arr)),
                "std": float(np.std(data_arr)),
                "min": float(np.min(data_arr)),
                "max": float(np.max(data_arr)),
            }

            if show_stats:
                stats_text = f"{'Trung bình' if language == 'vi' else 'Mean'}: {metadata['mean']:.2f}\n"
                stats_text += f"{'Độ lệch chuẩn' if language == 'vi' else 'Std'}: {metadata['std']:.2f}"
                ax.text(0.95, 0.95, stats_text, transform=ax.transAxes, fontsize=10,
                       verticalalignment='top', horizontalalignment='right',
                       bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

            ax.grid(True, alpha=0.3, axis='y')
            ax.set_xlabel(xlabel, fontsize=12)
            ax.set_ylabel(ylabel, fontsize=12)
            ax.set_title(title or ("Biểu đồ tần số" if language == "vi" else "Histogram"), fontsize=14)

            filename = f"histogram_{hash(str(data)) % 10000}.png"
            base64_img, filepath = self._save_figure(fig, filename)

            return PlotResult(
                success=True,
                plot_type=PlotType.HISTOGRAM,
                image_base64=base64_img,
                image_path=filepath,
                metadata=metadata,
            )

        except Exception as e:
            logger.error(f"Plot histogram failed: {e}")
            return PlotResult(
                success=False,
                plot_type=PlotType.HISTOGRAM,
                error_message=str(e),
            )


# Tool interface for agent
def plotter_tool(
    action: str,
    expression: str = "",
    x_range: Tuple[float, float] = (-10, 10),
    y_range: Optional[Tuple[float, float]] = None,
    language: str = "vi",
    **kwargs,
) -> Dict[str, Any]:
    """
    Graph plotter tool interface for the math agent.

    Args:
        action: Action to perform (plot_function, plot_multiple, plot_derivative,
                plot_integral, plot_scatter, plot_histogram)
        expression: Mathematical expression (or list for plot_multiple)
        x_range: (x_min, x_max)
        y_range: (y_min, y_max) or None for auto
        language: "vi" for Vietnamese labels
        **kwargs: Additional arguments

    Returns:
        Dictionary with plot results
    """
    plotter = MathPlotter()

    try:
        if action == "plot_function":
            result = plotter.plot_function(
                expression=expression,
                x_range=x_range,
                y_range=y_range,
                title=kwargs.get("title"),
                show_critical_points=kwargs.get("show_critical_points", True),
                language=language,
            )

        elif action == "plot_multiple":
            expressions = kwargs.get("expressions", [expression])
            result = plotter.plot_multiple_functions(
                expressions=expressions,
                x_range=x_range,
                y_range=y_range,
                title=kwargs.get("title"),
                labels=kwargs.get("labels"),
                language=language,
            )

        elif action == "plot_derivative":
            result = plotter.plot_derivative(
                expression=expression,
                x_range=x_range,
                show_original=kwargs.get("show_original", True),
                language=language,
            )

        elif action == "plot_integral":
            lower = kwargs.get("lower", 0)
            upper = kwargs.get("upper", 1)
            result = plotter.plot_integral_area(
                expression=expression,
                lower=lower,
                upper=upper,
                x_range=x_range,
                language=language,
            )

        elif action == "plot_scatter":
            result = plotter.plot_scatter(
                x_data=kwargs.get("x_data", []),
                y_data=kwargs.get("y_data", []),
                title=kwargs.get("title"),
                show_regression=kwargs.get("show_regression", False),
                language=language,
            )

        elif action == "plot_histogram":
            result = plotter.plot_histogram(
                data=kwargs.get("data", []),
                bins=kwargs.get("bins", 10),
                title=kwargs.get("title"),
                show_stats=kwargs.get("show_stats", True),
                language=language,
            )

        else:
            return {
                "success": False,
                "error": f"Unknown action: {action}. "
                        f"Available: plot_function, plot_multiple, plot_derivative, "
                        f"plot_integral, plot_scatter, plot_histogram",
            }

        return {
            "success": result.success,
            "action": action,
            "plot_type": result.plot_type.value,
            "image_path": result.image_path,
            "image_base64": result.image_base64,
            "metadata": result.metadata,
            "error": result.error_message,
        }

    except Exception as e:
        logger.error(f"Plotter tool error: {e}")
        return {
            "success": False,
            "error": str(e),
        }


if __name__ == "__main__":
    # Test the plotter
    plotter = MathPlotter()

    print("=" * 60)
    print("Graph Plotter Tool Test")
    print("=" * 60)

    # Test function plot
    print("\n1. Plot Function: x^3 - 3*x^2 + 2*x")
    result = plotter.plot_function("x^3 - 3*x^2 + 2*x", x_range=(-2, 4))
    print(f"   Success: {result.success}")
    print(f"   Saved to: {result.image_path}")
    if result.metadata:
        print(f"   Critical points: {result.metadata.get('critical_points', {})}")

    # Test derivative plot
    print("\n2. Plot Function with Derivative: sin(x)")
    result = plotter.plot_derivative("sin(x)", x_range=(-2*math.pi, 2*math.pi))
    print(f"   Success: {result.success}")
    print(f"   Derivative: {result.metadata.get('derivative', 'N/A')}")

    # Test integral area
    print("\n3. Plot Integral Area: x^2, [0, 2]")
    result = plotter.plot_integral_area("x^2", lower=0, upper=2)
    print(f"   Success: {result.success}")
    print(f"   Integral value: {result.metadata.get('integral_value', 'N/A')}")

    # Test via tool interface
    print("\n4. Tool Interface Test:")
    tool_result = plotter_tool("plot_function", expression="x^2 - 4", x_range=(-5, 5))
    print(f"   Plot x² - 4: {'Success' if tool_result['success'] else 'Failed'}")
    print(f"   Saved to: {tool_result.get('image_path', 'N/A')}")

    print("\n" + "=" * 60)
    print("All tests completed!")
    print("=" * 60)
