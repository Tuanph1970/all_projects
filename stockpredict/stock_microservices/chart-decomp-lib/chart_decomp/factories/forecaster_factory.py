"""Factory for forecaster objects.

Design patterns:
    Factory Method — same extensibility contract as DecomposerFactory.
"""
from __future__ import annotations

from chart_decomp.infrastructure.forecasting.har_forecaster import HARForecaster
from chart_decomp.infrastructure.forecasting.vmd_har_forecaster import VMDHARForecaster


class ForecasterFactory:
    """Creates forecaster instances on demand."""

    def create_har(self) -> HARForecaster:
        return HARForecaster()

    def create_vmd_har(self) -> VMDHARForecaster:
        return VMDHARForecaster()

    def create(self, model: str):
        """Generic factory method.

        Parameters
        ----------
        model : "har" | "vmd-har"
        """
        registry = {
            "har":     self.create_har,
            "vmd-har": self.create_vmd_har,
            "vmd_har": self.create_vmd_har,
        }
        if model not in registry:
            raise ValueError(
                f"Unknown forecaster model '{model}'; "
                f"registered models: {list(registry)}"
            )
        return registry[model]()
