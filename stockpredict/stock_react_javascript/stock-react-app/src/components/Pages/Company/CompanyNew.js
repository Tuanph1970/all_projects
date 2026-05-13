import React, { useState, useEffect } from "react";
import DataTable from "react-data-table-component";
import httpClient from "../../../services/httpClient";
import { API_ENDPOINTS } from "../../../constants/api";
import { Newspaper, ExternalLink, TrendingUp, TrendingDown } from "lucide-react";
import {
  customTableStyles,
  formatNumber,
  LoadingComponent,
  NoDataComponent,
} from "./Reports/tableStyles";

export default function CompanyNew({ symbol }) {
  const [tableRowsData, setTableRowsData] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

  const getChangeStyle = (value) => {
    if (value === null || value === undefined) return "";
    const num = Number(value);
    if (num > 0) return "text-green-600 font-medium";
    if (num < 0) return "text-red-600 font-medium";
    return "text-gray-600";
  };

  // Format date from API (e.g., "2025-12-16 15:42:49" -> "16/12/2025")
  const formatDate = (dateStr) => {
    if (!dateStr) return "-";
    try {
      const date = new Date(dateStr);
      return date.toLocaleDateString("vi-VN", {
        day: "2-digit",
        month: "2-digit",
        year: "numeric",
      });
    } catch {
      return dateStr;
    }
  };

  const columns = [
    {
      name: "Title",
      selector: (row) => row.title,
      sortable: true,
      grow: 3,
      cell: (row) => (
        <div className="py-2">
          <p className="font-medium text-gray-900 line-clamp-2">{row.title}</p>
        </div>
      ),
    },
    {
      name: "Published",
      selector: (row) => row.publishDate,
      sortable: true,
      width: "120px",
      cell: (row) => (
        <span className="text-sm text-gray-600">
          {formatDate(row.publishDate)}
        </span>
      ),
    },
    {
      name: "Price",
      selector: (row) => row.price,
      sortable: true,
      width: "100px",
      cell: (row) => (
        <span className="font-semibold text-blue-700">
          {formatNumber(row.price)}
        </span>
      ),
    },
    {
      name: "Change",
      selector: (row) => row.change,
      sortable: true,
      width: "100px",
      cell: (row) => (
        <div className="flex items-center gap-1">
          {row.change > 0 ? (
            <TrendingUp className="w-3 h-3 text-green-500" />
          ) : row.change < 0 ? (
            <TrendingDown className="w-3 h-3 text-red-500" />
          ) : null}
          <span className={getChangeStyle(row.change)}>
            {formatNumber(row.change)}
          </span>
        </div>
      ),
    },
    {
      name: "Change %",
      selector: (row) => row.changePercent,
      sortable: true,
      width: "110px",
      cell: (row) => (
        <span className={getChangeStyle(row.changePercent)}>
          {row.changePercent != null
            ? (row.changePercent * 100).toFixed(2) + "%"
            : "-"}
        </span>
      ),
    },
    {
      name: "Source",
      selector: (row) => row.source,
      sortable: true,
      grow: 2,
      cell: (row) => (
        <a
          href={row.source}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 px-2 py-1 bg-gray-100 hover:bg-gray-200 rounded-full text-xs text-blue-600 hover:text-blue-800 transition-colors"
        >
          <ExternalLink className="w-3 h-3" />
          View Source
        </a>
      ),
    },
  ];

  useEffect(() => {
    (async () => {
      try {
        setIsLoading(true);
        const result = await httpClient.get(API_ENDPOINTS.COMPANY_NEWS(symbol));
        if (result.success && result.data) {
          setTableRowsData(Array.isArray(result.data) ? result.data : []);
        }
      } catch (error) {
        console.error("Error loading news data:", error);
      } finally {
        setIsLoading(false);
      }
    })();
  }, [symbol]);

  return (
    <div className="p-4">
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
        <div className="bg-gradient-to-r from-rose-500 to-pink-600 px-6 py-4">
          <div className="flex items-center gap-3">
            <Newspaper className="w-6 h-6 text-white" />
            <div>
              <h3 className="text-lg font-semibold text-white">Company News</h3>
              <p className="text-rose-100 text-sm">
                Latest news and price impact analysis
              </p>
            </div>
          </div>
        </div>
        <DataTable
          columns={columns}
          data={tableRowsData}
          defaultSortFieldId={2}
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
