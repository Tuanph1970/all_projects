import logging
from vnstock import Vnstock, Listing
from polygon import StocksClient

logger = logging.getLogger(__name__)

client = StocksClient(api_key='OMGSs9vd696RZZz2aSoWBaAIzQzw7B_2')


class Contract:
    def __init__(self):
        self._listing = None

    @property
    def listing(self):
        """Lazy initialization of Listing instance."""
        if self._listing is None:
            self._listing = Listing()
        return self._listing

    def get_contracts(self):
        """Get list of all companies/contracts using vnstock 3.x API."""
        try:
            # Use the new vnstock 3.x Listing API
            contract_list = self.listing.all_symbols()
            return contract_list
        except Exception as e:
            logger.error(f"Error getting contracts: {e}")
            # Return empty DataFrame on error
            import pandas as pd
            return pd.DataFrame()
