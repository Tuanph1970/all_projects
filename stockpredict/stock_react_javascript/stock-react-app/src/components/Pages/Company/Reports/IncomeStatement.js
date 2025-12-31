import React, { useState, useEffect } from "react";
import DataTable from "react-data-table-component";
import httpClient from "../../../../services/httpClient";
import { API_ENDPOINTS } from "../../../../constants/api";
import { Receipt } from "lucide-react";
import {
  customTableStyles,
  formatNumber,
  LoadingComponent,
  NoDataComponent,
} from "./tableStyles";

export default function IncomeStatement({ symbol }) {
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
      name: "Year",
      selector: (row) => row.report_year,
      sortable: true,
      width: "100px",
      cell: (row) => (
        <span className="font-semibold text-blue-700">{row.report_year}</span>
      ),
    },
    {
      name: "Revenue",
      selector: (row) => row.revenue,
      sortable: true,
      cell: (row) => (
        <span className="text-blue-600 font-bold">
          {formatNumber(row.revenue)}
        </span>
      ),
    },
    {
      name: "Sales",
      selector: (row) => row.sales,
      sortable: true,
      cell: (row) => (
        <span className="font-medium">{formatNumber(row.sales)}</span>
      ),
    },
    {
      name: "Net Profit",
      selector: (row) => row.net_profit,
      sortable: true,
      cell: (row) => (
        <span className={getValueStyle(row.net_profit)}>
          {formatNumber(row.net_profit)}
        </span>
      ),
    },
    {
      name: "Profit Before Tax",
      selector: (row) => row.profit_before_tax,
      sortable: true,
      cell: (row) => (
        <span className={getValueStyle(row.profit_before_tax)}>
          {formatNumber(row.profit_before_tax)}
        </span>
      ),
    },
    {
      name: "Net Profit (Year)",
      selector: (row) => row.net_profit_for_the_year,
      sortable: true,
      cell: (row) => (
        <span className={getValueStyle(row.net_profit_for_the_year)}>
          {formatNumber(row.net_profit_for_the_year)}
        </span>
      ),
    },
    {
      name: "Dividend Received",
      selector: (row) => row.dividend_receive,
      sortable: true,
      cell: (row) => (
        <span className="text-purple-600">
          {formatNumber(row.dividend_receive)}
        </span>
      ),
    },
    {
      name: "EPS (Basic)",
      selector: (row) => row.eps_basis,
      sortable: true,
      cell: (row) => (
        <span
          className={
            row.eps_basis > 0
              ? "text-green-600 font-bold"
              : row.eps_basis < 0
              ? "text-red-600 font-bold"
              : ""
          }
        >
          {formatNumber(row.eps_basis)}
        </span>
      ),
    },
  ];

  useEffect(() => {
    (async () => {
      try {
        setIsLoading(true);
        const result = await httpClient.get(API_ENDPOINTS.FINANCIAL_INCOME_STATEMENT(symbol));
        if (result.success && result.data) {
          setTableRowsData(Array.isArray(result.data) ? result.data : []);
        }
      } catch (error) {
        console.error("Error loading income statement data:", error);
      } finally {
        setIsLoading(false);
      }
    })();
  }, [symbol]);

  return (
    <div className="p-4">
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
        <div className="bg-gradient-to-r from-orange-500 to-amber-500 px-6 py-4">
          <div className="flex items-center gap-3">
            <Receipt className="w-6 h-6 text-white" />
            <div>
              <h3 className="text-lg font-semibold text-white">
                Income Statement
              </h3>
              <p className="text-orange-100 text-sm">
                Revenue, profit, and earnings analysis
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
