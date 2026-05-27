"""Factory for decomposer objects.

Returns concrete Strategy implementations keyed by algorithm name.
Adding a new decomposition algorithm only requires:
    1. Implementing the IXxxDecomposer protocol.
    2. Adding one entry to the factory registry.
No caller code changes needed.

Design patterns:
    Factory Method — central creation logic, hides concrete types from callers.
    Registry pattern — name → class mapping for open/closed extensibility.
"""
from __future__ import annotations

from chart_decomp.infrastructure.decomposition.emd_decomposer import EMDDecomposer
from chart_decomp.infrastructure.decomposition.modwt_decomposer import MODWTDecomposer
from chart_decomp.infrastructure.decomposition.vmd_decomposer import VMDDecomposer


class DecomposerFactory:
    """Creates decomposer instances on demand (stateless; always returns new)."""

    def create_modwt(self) -> MODWTDecomposer:
        return MODWTDecomposer()

    def create_emd(self) -> EMDDecomposer:
        return EMDDecomposer()

    def create_vmd(self) -> VMDDecomposer:
        return VMDDecomposer()

    def create(self, method: str):
        """Generic factory method keyed by string name.

        Parameters
        ----------
        method : "modwt" | "emd" | "vmd"

        Raises
        ------
        ValueError if method is unrecognised.
        """
        registry = {
            "modwt": self.create_modwt,
            "emd":   self.create_emd,
            "eemd":  self.create_emd,   # EEMD uses the same EMDDecomposer
            "vmd":   self.create_vmd,
        }
        if method not in registry:
            raise ValueError(
                f"Unknown decomposition method '{method}'; "
                f"registered methods: {list(registry)}"
            )
        return registry[method]()
