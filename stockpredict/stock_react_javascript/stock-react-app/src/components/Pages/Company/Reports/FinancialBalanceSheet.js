import React, { useState, useEffect } from "react";
import DataTable from "react-data-table-component";
import { useTranslation } from 'react-i18next';
import httpClient from "../../../../services/httpClient";
import { API_ENDPOINTS } from "../../../../constants/api";
import { Scale } from "lucide-react";
import {
  customTableStyles,
  formatNumber,
  LoadingComponent,
  NoDataComponent,
} from "./tableStyles";

export default function FinancialBalanceSheet({ symbol }) {
  const { t } = useTranslation();
  const [tableRowsData, setTableRowsData] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

  const columns = [
    {
      name: t('company_page.balance_col_year'),
      selector: (row) => row.report_year,
      sortable: true,
      width: "100px",
      cell: (row) => (
        <span className="font-semibold text-blue-700">{row.report_year}</span>
      ),
    },
    {
      name: t('company_page.balance_col_current_assets'),
      selector: (row) => row.current_assets,
      sortable: true,
      cell: (row) => (
        <span className="text-emerald-600 font-medium">
          {formatNumber(row.current_assets)}
        </span>
      ),
    },
    {
      name: t('company_page.balance_col_cash'),
      selector: (row) => row.cash,
      sortable: true,
      cell: (row) => (
        <span className="text-green-600 font-medium">
          {formatNumber(row.cash)}
        </span>
      ),
    },
    {
      name: t('company_page.balance_col_st_investments'),
      selector: (row) => row.short_term_investments,
      sortable: true,
      cell: (row) => <span>{formatNumber(row.short_term_investments)}</span>,
    },
    {
      name: t('company_page.balance_col_lt_assets'),
      selector: (row) => row.long_term_assets,
      sortable: true,
      cell: (row) => (
        <span className="text-blue-600 font-medium">
          {formatNumber(row.long_term_assets)}
        </span>
      ),
    },
    {
      name: t('company_page.balance_col_fixed_assets'),
      selector: (row) => row.fixed_assets,
      sortable: true,
      cell: (row) => <span>{formatNumber(row.fixed_assets)}</span>,
    },
    {
      name: t('company_page.balance_col_total_assets'),
      selector: (row) => row.total_assets,
      sortable: true,
      cell: (row) => (
        <span className="text-indigo-700 font-bold">
          {formatNumber(row.total_assets)}
        </span>
      ),
    },
    {
      name: t('company_page.balance_col_total_resources'),
      selector: (row) => row.total_resources,
      sortable: true,
      cell: (row) => (
        <span className="font-medium">{formatNumber(row.total_resources)}</span>
      ),
    },
    {
      name: t('company_page.balance_col_capital_reserves'),
      selector: (row) => row.capital_and_reserves,
      sortable: true,
      cell: (row) => (
        <span className="text-purple-600 font-medium">
          {formatNumber(row.capital_and_reserves)}
        </span>
      ),
    },
  ];

  useEffect(() => {
    (async () => {
      try {
        setIsLoading(true);
        const result = await httpClient.get(API_ENDPOINTS.FINANCIAL_BALANCE_SHEET(symbol));
        if (result.success && result.data) {
          setTableRowsData(Array.isArray(result.data) ? result.data : []);
        }
      } catch (error) {
        console.error("Error loading balance sheet data:", error);
      } finally {
        setIsLoading(false);
      }
    })();
  }, [symbol]);

  return (
    <div className="p-4">
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
        <div className="bg-white border-b border-gray-200 px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="p-1.5 bg-blue-500 rounded-lg">
              <Scale className="w-5 h-5 text-white" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-gray-900">{t('company_page.balance_title')}</h3>
              <p className="text-gray-500 text-sm">
                {t('company_page.balance_subtitle')}
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
