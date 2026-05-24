import React, { useState, useEffect } from "react";
import DataTable from "react-data-table-component";
import { useTranslation } from 'react-i18next';
import httpClient from "../../../services/httpClient";
import { API_ENDPOINTS } from "../../../constants/api";
import { Calendar, Activity } from "lucide-react";
import {
  customTableStyles,
  formatNumber,
  LoadingComponent,
  NoDataComponent,
} from "./Reports/tableStyles";

export default function CompanyEvents({ symbol }) {
  const { t } = useTranslation();
  const [tableRowsData, setTableRowsData] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

  // eslint-disable-next-line no-unused-vars -- helper retained for upcoming column
  const getChangeStyle = (value) => {
    if (value === null || value === undefined) return "";
    const num = Number(value);
    if (num > 0) return "text-green-600 font-medium";
    if (num < 0) return "text-red-600 font-medium";
    return "text-gray-600";
  };

  // eslint-disable-next-line no-unused-vars -- helper retained for upcoming column
  const getRSIStyle = (value) => {
    if (value === null || value === undefined) return "";
    const num = Number(value);
    if (num >= 70) return "text-red-600 font-medium"; // Overbought
    if (num <= 30) return "text-green-600 font-medium"; // Oversold
    return "text-gray-700";
  };

  // Format date from API (e.g., "2024-10-21" -> "21/10/2024")
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
      name: t('company_page.events_col_event'),
      selector: (row) => row.title,
      sortable: true,
      grow: 2,
      cell: (row) => (
        <div className="py-2">
          <p className="font-semibold text-gray-900">{row.title}</p>
          {row.eventType && (
            <span className="text-xs text-purple-600 bg-purple-50 px-2 py-0.5 rounded-full">
              {row.eventType}
            </span>
          )}
        </div>
      ),
    },
    {
      name: t('company_page.events_col_type'),
      selector: (row) => row.eventType,
      sortable: true,
      width: "150px",
      cell: (row) => (
        <p className="text-sm text-gray-600 line-clamp-2">{row.eventTypeEn || row.eventType || "-"}</p>
      ),
    },
    {
      name: t('company_page.events_col_publish_date'),
      selector: (row) => row.publishDate,
      sortable: true,
      width: "120px",
      cell: (row) => (
        <div className="flex items-center gap-2">
          <Calendar className="w-3 h-3 text-gray-400" />
          <span className="text-sm text-gray-700">{formatDate(row.publishDate)}</span>
        </div>
      ),
    },
    {
      name: t('company_page.events_col_record_date'),
      selector: (row) => row.recordDate,
      sortable: true,
      width: "120px",
      cell: (row) => (
        <span className="text-sm text-gray-600">{formatDate(row.recordDate)}</span>
      ),
    },
    {
      name: t('company_page.events_col_exright_date'),
      selector: (row) => row.exrightDate,
      sortable: true,
      width: "120px",
      cell: (row) => (
        <span className="text-sm text-gray-600">{formatDate(row.exrightDate)}</span>
      ),
    },
    {
      name: t('company_page.events_col_ratio'),
      selector: (row) => row.ratio,
      sortable: true,
      width: "100px",
      cell: (row) => (
        <span className="font-semibold text-blue-700">
          {row.ratio ? (row.ratio * 100).toFixed(1) + "%" : "-"}
        </span>
      ),
    },
    {
      name: t('company_page.events_col_value'),
      selector: (row) => row.value,
      sortable: true,
      width: "110px",
      cell: (row) => (
        <span className="font-medium text-green-600">
          {row.value ? formatNumber(row.value) : "-"}
        </span>
      ),
    },
    {
      name: t('company_page.events_col_source'),
      selector: (row) => row.source,
      sortable: false,
      width: "80px",
      cell: (row) => (
        row.source ? (
          <a
            href={row.source}
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-500 hover:text-blue-700"
          >
            <Activity className="w-4 h-4" />
          </a>
        ) : "-"
      ),
    },
  ];

  useEffect(() => {
    (async () => {
      try {
        setIsLoading(true);
        const result = await httpClient.get(API_ENDPOINTS.COMPANY_EVENTS(symbol));
        if (result.success && result.data) {
          setTableRowsData(Array.isArray(result.data) ? result.data : []);
        }
      } catch (error) {
        console.error("Error loading events data:", error);
      } finally {
        setIsLoading(false);
      }
    })();
  }, [symbol]);

  return (
    <div className="p-4">
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
        <div className="bg-gradient-to-r from-violet-600 to-purple-600 px-6 py-4">
          <div className="flex items-center gap-3">
            <Calendar className="w-6 h-6 text-white" />
            <div>
              <h3 className="text-lg font-semibold text-white">
                {t('company_page.events_title')}
              </h3>
              <p className="text-violet-100 text-sm">
                {t('company_page.events_subtitle')}
              </p>
            </div>
          </div>
        </div>
        <DataTable
          columns={columns}
          data={tableRowsData}
          defaultSortFieldId={3}
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
