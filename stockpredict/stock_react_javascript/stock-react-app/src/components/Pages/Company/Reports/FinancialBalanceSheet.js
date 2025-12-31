import React, { useState, useEffect } from "react";
import DataTable from "react-data-table-component";
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
  const [tableRowsData, setTableRowsData] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

  const columns = [
    {
      name: "Year",
      selector: (row) => row.report_year,
      sortable: true,
      width: "100px",
      cell: (row) => (
        <span className="font-semibold text-blue-700">{row.report_year}</span>
      ),
    },
    {
      name: "Current Assets",
      selector: (row) => row.current_assets,
      sortable: true,
      cell: (row) => (
        <span className="text-emerald-600 font-medium">
          {formatNumber(row.current_assets)}
        </span>
      ),
    },
    {
      name: "Cash",
      selector: (row) => row.cash,
      sortable: true,
      cell: (row) => (
        <span className="text-green-600 font-medium">
          {formatNumber(row.cash)}
        </span>
      ),
    },
    {
      name: "Short-term Investments",
      selector: (row) => row.short_term_investments,
      sortable: true,
      cell: (row) => <span>{formatNumber(row.short_term_investments)}</span>,
    },
    {
      name: "Long-term Assets",
      selector: (row) => row.long_term_assets,
      sortable: true,
      cell: (row) => (
        <span className="text-blue-600 font-medium">
          {formatNumber(row.long_term_assets)}
        </span>
      ),
    },
    {
      name: "Fixed Assets",
      selector: (row) => row.fixed_assets,
      sortable: true,
      cell: (row) => <span>{formatNumber(row.fixed_assets)}</span>,
    },
    {
      name: "Total Assets",
      selector: (row) => row.total_assets,
      sortable: true,
      cell: (row) => (
        <span className="text-indigo-700 font-bold">
          {formatNumber(row.total_assets)}
        </span>
      ),
    },
    {
      name: "Total Resources",
      selector: (row) => row.total_resources,
      sortable: true,
      cell: (row) => (
        <span className="font-medium">{formatNumber(row.total_resources)}</span>
      ),
    },
    {
      name: "Capital & Reserves",
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
        <div className="bg-gradient-to-r from-emerald-600 to-teal-600 px-6 py-4">
          <div className="flex items-center gap-3">
            <Scale className="w-6 h-6 text-white" />
            <div>
              <h3 className="text-lg font-semibold text-white">Balance Sheet</h3>
              <p className="text-emerald-100 text-sm">
                Assets, liabilities, and equity overview
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
