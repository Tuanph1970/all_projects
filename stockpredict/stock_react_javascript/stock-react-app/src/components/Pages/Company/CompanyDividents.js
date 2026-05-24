import React, { useEffect, useState } from "react";
import DataTable from "react-data-table-component";
import { useTranslation } from 'react-i18next';
import httpClient from "../../../services/httpClient";
import { API_ENDPOINTS } from "../../../constants/api";
import { Coins, Calendar, Percent, CreditCard, Banknote } from "lucide-react";
import {
  customTableStyles,
  formatNumber,
  LoadingComponent,
  NoDataComponent,
} from "./Reports/tableStyles";

export default function CompanyDividents({ symbol }) {
  const { t } = useTranslation();
  const [tableRowsData, setTableRowsData] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

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

  // Extract year from date string
  const getYear = (dateStr) => {
    if (!dateStr) return "-";
    try {
      return new Date(dateStr).getFullYear();
    } catch {
      return dateStr.slice(0, 4);
    }
  };

  const columns = [
    {
      name: t('company_page.div_col_title'),
      selector: (row) => row.title,
      sortable: true,
      grow: 2,
      cell: (row) => (
        <div className="py-2">
          <p className="font-medium text-gray-900 line-clamp-2">{row.title}</p>
        </div>
      ),
    },
    {
      name: t('company_page.div_col_exright_date'),
      selector: (row) => row.exrightDate,
      sortable: true,
      width: "130px",
      cell: (row) => (
        <div className="flex items-center gap-2">
          <Calendar className="w-4 h-4 text-blue-500" />
          <span className="font-medium text-gray-900">{formatDate(row.exrightDate)}</span>
        </div>
      ),
    },
    {
      name: t('company_page.div_col_year'),
      selector: (row) => row.issueDate,
      sortable: true,
      width: "100px",
      cell: (row) => (
        <span className="px-3 py-1 bg-blue-100 text-blue-700 rounded-full text-sm font-medium">
          {getYear(row.issueDate)}
        </span>
      ),
    },
    {
      name: t('company_page.div_col_ratio'),
      selector: (row) => row.ratio,
      sortable: true,
      width: "140px",
      cell: (row) => (
        <div className="flex items-center gap-2">
          <Percent className="w-4 h-4 text-green-500" />
          <span className="text-green-600 font-bold text-lg">
            {row.ratio != null ? (row.ratio * 100).toFixed(1) + "%" : "-"}
          </span>
        </div>
      ),
    },
    {
      name: t('company_page.div_col_value'),
      selector: (row) => row.value,
      sortable: true,
      width: "130px",
      cell: (row) => (
        <div className="flex items-center gap-2">
          <Banknote className="w-4 h-4 text-emerald-500" />
          <span className="text-emerald-600 font-bold">
            {row.value ? formatNumber(row.value) : "-"}
          </span>
        </div>
      ),
    },
    {
      name: t('company_page.div_col_type'),
      selector: (row) => row.eventType,
      sortable: true,
      width: "150px",
      cell: (row) => (
        <div className="flex items-center gap-2">
          <CreditCard className="w-4 h-4 text-purple-500" />
          <span className="px-2 py-1 bg-purple-100 text-purple-700 rounded-lg text-xs">
            {row.eventTypeEn || row.eventType || "Cash"}
          </span>
        </div>
      ),
    },
  ];

  useEffect(() => {
    (async () => {
      try {
        setIsLoading(true);
        const result = await httpClient.get(API_ENDPOINTS.COMPANY_DIVIDENDS(symbol));
        if (result.success && result.data) {
          setTableRowsData(Array.isArray(result.data) ? result.data : []);
        }
      } catch (error) {
        console.error("Error loading dividends data:", error);
      } finally {
        setIsLoading(false);
      }
    })();
  }, [symbol]);

  // Calculate total dividends summary
  const totalDividends = tableRowsData.reduce(
    (sum, item) => sum + (Number(item.ratio) * 100 || 0),
    0
  );
  const avgDividend =
    tableRowsData.length > 0 ? totalDividends / tableRowsData.length : 0;

  return (
    <div className="p-4 space-y-4">
      {/* Summary Cards */}
      {tableRowsData.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-gradient-to-br from-green-50 to-emerald-100 rounded-xl p-4 border border-green-200">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-green-500 rounded-lg">
                <Coins className="w-5 h-5 text-white" />
              </div>
              <div>
                <p className="text-sm text-green-600 font-medium">
                  {t('company_page.div_card_total')}
                </p>
                <p className="text-2xl font-bold text-green-700">
                  {tableRowsData.length}
                </p>
              </div>
            </div>
          </div>

          <div className="bg-gradient-to-br from-blue-50 to-indigo-100 rounded-xl p-4 border border-blue-200">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-blue-500 rounded-lg">
                <Percent className="w-5 h-5 text-white" />
              </div>
              <div>
                <p className="text-sm text-blue-600 font-medium">
                  {t('company_page.div_card_avg')}
                </p>
                <p className="text-2xl font-bold text-blue-700">
                  {avgDividend.toFixed(2)}%
                </p>
              </div>
            </div>
          </div>

          <div className="bg-gradient-to-br from-purple-50 to-violet-100 rounded-xl p-4 border border-purple-200">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-purple-500 rounded-lg">
                <Calendar className="w-5 h-5 text-white" />
              </div>
              <div>
                <p className="text-sm text-purple-600 font-medium">
                  {t('company_page.div_card_latest_year')}
                </p>
                <p className="text-2xl font-bold text-purple-700">
                  {tableRowsData[0]?.issueDate ? new Date(tableRowsData[0].issueDate).getFullYear() : "-"}
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Data Table */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
        <div className="bg-gradient-to-r from-green-600 to-emerald-600 px-6 py-4">
          <div className="flex items-center gap-3">
            <Coins className="w-6 h-6 text-white" />
            <div>
              <h3 className="text-lg font-semibold text-white">
                {t('company_page.div_title')}
              </h3>
              <p className="text-green-100 text-sm">
                {t('company_page.div_subtitle')}
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
