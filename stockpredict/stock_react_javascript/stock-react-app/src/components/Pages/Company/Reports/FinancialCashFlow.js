import React, { useState, useEffect } from "react";
import DataTable from "react-data-table-component";
import { useTranslation } from 'react-i18next';
import httpClient from "../../../../services/httpClient";
import { API_ENDPOINTS } from "../../../../constants/api";
import { Banknote } from "lucide-react";
import {
  customTableStyles,
  formatNumber,
  LoadingComponent,
  NoDataComponent,
} from "./tableStyles";

export default function FinancialCashFlow({ symbol }) {
  const { t } = useTranslation();
  const [tableRowsData, setTableRowsData] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

  const getValueStyle = (value) => {
    if (value === null || value === undefined) return "";
    const num = Number(value);
    if (num > 0) return "text-green-600 font-medium";
    if (num < 0) return "text-red-600 font-medium";
    return "";
  };

  const columns = [
    {
      name: t('company_page.cashflow_col_year'),
      selector: (row) => row.report_year,
      sortable: true,
      width: "100px",
      cell: (row) => (
        <span className="font-semibold text-blue-700">{row.report_year}</span>
      ),
    },
    {
      name: t('company_page.cashflow_col_cash'),
      selector: (row) => row.cash,
      sortable: true,
      cell: (row) => (
        <span className="text-blue-600 font-medium">
          {formatNumber(row.cash)}
        </span>
      ),
    },
    {
      name: t('company_page.cashflow_col_operating'),
      selector: (row) => row.cash_from_operating_activities,
      sortable: true,
      cell: (row) => (
        <span className={getValueStyle(row.cash_from_operating_activities)}>
          {formatNumber(row.cash_from_operating_activities)}
        </span>
      ),
    },
    {
      name: t('company_page.cashflow_col_div_paid'),
      selector: (row) => row.dividends_paid,
      sortable: true,
      cell: (row) => (
        <span className={getValueStyle(row.dividends_paid)}>
          {formatNumber(row.dividends_paid)}
        </span>
      ),
    },
    {
      name: t('company_page.cashflow_col_net_change'),
      selector: (row) => row.net_change_in_cash,
      sortable: true,
      cell: (row) => (
        <span className={getValueStyle(row.net_change_in_cash)}>
          {formatNumber(row.net_change_in_cash)}
        </span>
      ),
    },
    {
      name: t('company_page.cashflow_col_div_gain'),
      selector: (row) => row.gain_on_dividend,
      sortable: true,
      cell: (row) => (
        <span className={getValueStyle(row.gain_on_dividend)}>
          {formatNumber(row.gain_on_dividend)}
        </span>
      ),
    },
    {
      name: t('company_page.cashflow_col_charter_increase'),
      selector: (row) => row.increase_in_charter_captial,
      sortable: true,
      cell: (row) => (
        <span className={getValueStyle(row.increase_in_charter_captial)}>
          {formatNumber(row.increase_in_charter_captial)}
        </span>
      ),
    },
  ];

  useEffect(() => {
    (async () => {
      try {
        setIsLoading(true);
        const result = await httpClient.get(API_ENDPOINTS.FINANCIAL_CASH_FLOW(symbol));
        if (result.success && result.data) {
          setTableRowsData(Array.isArray(result.data) ? result.data : []);
        }
      } catch (error) {
        console.error("Error loading cash flow data:", error);
      } finally {
        setIsLoading(false);
      }
    })();
  }, [symbol]);

  return (
    <div className="p-4">
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
        <div className="bg-gradient-to-r from-cyan-600 to-blue-600 px-6 py-4">
          <div className="flex items-center gap-3">
            <Banknote className="w-6 h-6 text-white" />
            <div>
              <h3 className="text-lg font-semibold text-white">
                {t('company_page.cashflow_title')}
              </h3>
              <p className="text-cyan-100 text-sm">
                {t('company_page.cashflow_subtitle')}
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
