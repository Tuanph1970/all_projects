import React, { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import StockChart from "../../ui/StockChart";
import httpClient from "../../../services/httpClient";
import { API_ENDPOINTS } from "../../../constants/api";

export default function CompanyCharts({ symbol }) {
  const { t } = useTranslation();
  const [stockData, setStockData] = useState([]);
  const [isLoading, setIsLoading] = useState([]);

  useEffect(() => {
    (async () => {
      try {
        setIsLoading(true);
        const result = await httpClient.get(API_ENDPOINTS.STOCK_HISTORY(symbol));
        if (result.success && result.data) {
          setStockData(result.data.data || result.data);
        }
      } catch (error) {
        console.error("Error loading historical data:", error);
      } finally {
        setIsLoading(false);
      }
    })();
  }, [symbol]);

  if (isLoading) {
    return <p>{t("company_page.charts_loading")}</p>;
  }
  return <StockChart initialData={stockData} symbol={symbol} />;
}
