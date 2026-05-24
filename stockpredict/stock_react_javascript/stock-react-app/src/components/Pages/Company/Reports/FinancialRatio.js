import React, { useState, useEffect } from "react";
import DataTable from "react-data-table-component";
import { useTranslation } from 'react-i18next';
import httpClient from "../../../../services/httpClient";
import { API_ENDPOINTS } from "../../../../constants/api";
import { TrendingUp } from "lucide-react";
import {
  customTableStyles,
  formatNumber,
  formatPercent,
  LoadingComponent,
  NoDataComponent,
} from "./tableStyles";

export default function FinancialRatio({ symbol }) {
  const { t } = useTranslation();
  const [tableRowsData, setTableRowsData] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

  const columns = [
    {
      name: t('company_page.ratio_col_year'),
      selector: (row) => row.metayearreport,
      sortable: true,
      width: "100px",
      cell: (row) => (
        <span className="font-semibold text-blue-700">
          {row.metayearreport}
        </span>
      ),
    },
    {
      name: t('company_page.ratio_col_pb'),
      selector: (row) => row.p_b,
      sortable: true,
      cell: (row) => <span>{formatNumber(row.p_b)}</span>,
    },
    {
      name: t('company_page.ratio_col_market_cap'),
      selector: (row) => row.market_capital,
      sortable: true,
      cell: (row) => (
        <span className="font-medium">{formatNumber(row.market_capital)}</span>
      ),
    },
    {
      name: t('company_page.ratio_col_pe'),
      selector: (row) => row.p_e,
      sortable: true,
      cell: (row) => (
        <span
          className={
            row.p_e && row.p_e < 15
              ? "text-green-600 font-medium"
              : row.p_e && row.p_e > 25
              ? "text-red-600 font-medium"
              : ""
          }
        >
          {formatNumber(row.p_e)}
        </span>
      ),
    },
    {
      name: t('company_page.ratio_col_ps'),
      selector: (row) => row.p_s,
      sortable: true,
      cell: (row) => <span>{formatNumber(row.p_s)}</span>,
    },
    {
      name: t('company_page.ratio_col_pcashflow'),
      selector: (row) => row.p_cash_flow,
      sortable: true,
      cell: (row) => <span>{formatNumber(row.p_cash_flow)}</span>,
    },
    {
      name: t('company_page.ratio_col_eps'),
      selector: (row) => row.eps,
      sortable: true,
      cell: (row) => (
        <span
          className={
            row.eps > 0
              ? "text-green-600 font-medium"
              : row.eps < 0
              ? "text-red-600 font-medium"
              : ""
          }
        >
          {formatNumber(row.eps)}
        </span>
      ),
    },
    {
      name: t('company_page.ratio_col_roe'),
      selector: (row) => row.roe,
      sortable: true,
      cell: (row) => (
        <span
          className={
            row.roe && row.roe > 15
              ? "text-green-600 font-medium"
              : row.roe && row.roe < 10
              ? "text-orange-600 font-medium"
              : ""
          }
        >
          {formatPercent(row.roe)}
        </span>
      ),
    },
    {
      name: t('company_page.ratio_col_roic'),
      selector: (row) => row.roic,
      sortable: true,
      cell: (row) => (
        <span
          className={
            row.roic && row.roic > 12
              ? "text-green-600 font-medium"
              : row.roic && row.roic < 8
              ? "text-orange-600 font-medium"
              : ""
          }
        >
          {formatPercent(row.roic)}
        </span>
      ),
    },
  ];

  useEffect(() => {
    (async () => {
      try {
        setIsLoading(true);
        const result = await httpClient.get(API_ENDPOINTS.FINANCIAL_RATIO(symbol));
        if (result.success && result.data) {
          setTableRowsData(Array.isArray(result.data) ? result.data : []);
        }
      } catch (error) {
        console.error("Error loading financial ratio data:", error);
      } finally {
        setIsLoading(false);
      }
    })();
  }, [symbol]);

  return (
    <div className="p-4">
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
        <div className="bg-gradient-to-r from-indigo-600 to-purple-600 px-6 py-4">
          <div className="flex items-center gap-3">
            <TrendingUp className="w-6 h-6 text-white" />
            <div>
              <h3 className="text-lg font-semibold text-white">
                {t('company_page.ratio_title')}
              </h3>
              <p className="text-indigo-100 text-sm">
                {t('company_page.ratio_subtitle')}
              </p>
            </div>
          </div>
        </div>
        <DataTable
          columns={columns}
          data={tableRowsData}
          defaultSortFieldId={1}
          defaultSortAsc={false}
          pagination
          highlightOnHover
          responsive
          paginationPerPage={10}
          paginationRowsPerPageOptions={[10, 20, 30, 50]}
          customStyles={customTableStyles}
          progressPending={isLoading}
          progressComponent={<LoadingComponent />}
          noDataComponent={<NoDataComponent />}
        />
      </div>
    </div>
  );
}
