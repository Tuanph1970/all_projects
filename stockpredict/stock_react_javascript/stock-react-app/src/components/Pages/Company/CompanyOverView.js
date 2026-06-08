import React, { useEffect, useState } from "react";
import {
  Building2,
  Users,
  BarChart3,
  Briefcase,
  PieChart,
} from "lucide-react";
import { useTranslation } from 'react-i18next';
import httpClient from "../../../services/httpClient";
import { API_ENDPOINTS } from "../../../constants/api";

export default function CompanyOverView({ symbol }) {
  const { t } = useTranslation();
  const [overViewData, setOverViewData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        setIsLoading(true);
        const result = await httpClient.get(API_ENDPOINTS.COMPANY_PROFILE(symbol));
        if (result.success && result.data) {
          const data = Array.isArray(result.data) ? result.data[0] : result.data;
          setOverViewData(data);
        }
      } catch (error) {
        console.error("Error loading overview data:", error);
      } finally {
        setIsLoading(false);
      }
    })();
  }, [symbol]);

  const formatNumber = (num) => {
    if (num === null || num === undefined) return "N/A";
    return Number(num).toLocaleString();
  };

  if (isLoading) {
    return (
      <div className="p-6">
        <div className="animate-pulse space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {[...Array(8)].map((_, i) => (
              <div key={i} className="h-24 bg-gray-200 rounded-xl"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (!overViewData) {
    return (
      <div className="p-6 text-center text-gray-500">
        {t('company_page.overview_no_data')}
      </div>
    );
  }

  return (
    <div className="p-4 space-y-4">
      {/* Row 1: Company Header + Performance Metrics */}
      <div className="flex flex-wrap gap-4">
        {/* Company Header */}
        <div className="flex-1 min-w-[300px]">
          <div className="bg-white border border-gray-200 rounded-2xl p-5 h-full shadow-sm">
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-2">
                  <div className="w-12 h-12 bg-blue-50 border border-blue-200 rounded-xl flex items-center justify-center">
                    <Building2 className="w-6 h-6 text-blue-600" />
                  </div>
                  <div>
                    <h2 className="text-2xl font-bold tracking-tight text-gray-900">{overViewData.ticker}</h2>
                    <p className="text-gray-500 text-sm">{overViewData.industry}</p>
                  </div>
                </div>
                <div className="flex flex-wrap items-center gap-2 mt-3">
                  {overViewData.industry && (
                    <span className="px-3 py-1.5 bg-blue-50 border border-blue-200 rounded-lg text-xs font-semibold uppercase tracking-wide text-blue-700">
                      {overViewData.industry}
                    </span>
                  )}
                  {overViewData.industryL2 && (
                    <span className="px-3 py-1.5 bg-gray-50 border border-gray-200 rounded-lg text-xs font-semibold uppercase tracking-wide text-gray-600">
                      {overViewData.industryL2}
                    </span>
                  )}
                </div>
              </div>
              <div className="text-right bg-blue-50 border border-blue-100 rounded-xl p-3">
                <p className="text-gray-500 text-xs font-medium">{t('company_page.overview_charter_capital')}</p>
                <p className="text-gray-900 text-lg font-bold">
                  {overViewData.charterCapital ? formatNumber(overViewData.charterCapital / 1000000000) + "B" : "N/A"}
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Info Cards */}
        <div className="flex gap-4 flex-wrap">
          {/* Issue Share */}
          <div className="min-w-[120px] flex-1 rounded-xl p-4 bg-blue-50 border border-blue-200 shadow-sm hover:shadow-lg transition-all">
            <div className="flex flex-col items-center text-center">
              <span className="text-xs text-blue-500 font-semibold uppercase tracking-wide mb-2">{t('company_page.overview_issue_share')}</span>
              <span className="text-xl font-bold text-blue-700">
                {overViewData.issueShare ? formatNumber(overViewData.issueShare / 1000000) + "M" : "N/A"}
              </span>
            </div>
          </div>

          {/* Outstanding Share */}
          <div className="min-w-[120px] flex-1 rounded-xl p-4 bg-green-50 border border-green-200 shadow-sm hover:shadow-lg transition-all">
            <div className="flex flex-col items-center text-center">
              <span className="text-xs text-green-500 font-semibold uppercase tracking-wide mb-2">{t('company_page.overview_outstanding')}</span>
              <span className="text-xl font-bold text-green-700">
                {overViewData.outstandingShare ? formatNumber(overViewData.outstandingShare / 1000000) + "M" : "N/A"}
              </span>
            </div>
          </div>

          {/* Foreign % */}
          <div className="min-w-[120px] flex-1 rounded-xl p-4 bg-purple-50 border border-purple-200 shadow-sm hover:shadow-lg transition-all">
            <div className="flex flex-col items-center text-center">
              <span className="text-xs text-purple-500 font-semibold uppercase tracking-wide mb-2">{t('company_page.overview_foreign_pct')}</span>
              <span className="text-xl font-bold text-purple-700">
                {overViewData.foreignPercent != null ? (overViewData.foreignPercent * 100).toFixed(1) + "%" : "N/A"}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Row 2: Detail Cards */}
      <div className="flex flex-wrap gap-4">
        {/* Share Info */}
        <div className="flex-1 min-w-[150px] bg-white rounded-xl p-4 border border-gray-200 shadow-sm hover:shadow-md hover:scale-[1.02] transition-all duration-200">
          <div className="flex items-center gap-2 mb-3">
            <div className="p-2 bg-blue-500 rounded-lg">
              <PieChart className="w-4 h-4 text-white" />
            </div>
            <h3 className="font-semibold text-gray-800 text-sm">{t('company_page.overview_shares_card')}</h3>
          </div>
          <div className="space-y-2">
            <div className="flex justify-between items-center">
              <span className="text-xs text-gray-500">{t('company_page.overview_outstanding')}</span>
              <span className="text-sm font-bold text-gray-800 bg-blue-50 px-2 py-0.5 rounded">
                {overViewData.outstandingShare ? formatNumber(overViewData.outstandingShare / 1000000) + "M" : "N/A"}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-xs text-gray-500">{t('company_page.overview_issued')}</span>
              <span className="text-sm font-bold text-gray-800 bg-blue-50 px-2 py-0.5 rounded">
                {overViewData.issueShare ? formatNumber(overViewData.issueShare / 1000000) + "M" : "N/A"}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-xs text-violet-600">{t('company_page.overview_free_float')}</span>
              <span className="text-sm font-bold text-violet-900 bg-violet-100 px-2 py-0.5 rounded">
                {overViewData.freeFloatRate != null ? (overViewData.freeFloatRate * 100).toFixed(1) + "%" : "N/A"}
              </span>
            </div>
          </div>
        </div>

        {/* Stakeholders */}
        <div className="flex-1 min-w-[150px] bg-white rounded-xl p-4 border border-gray-200 shadow-sm hover:shadow-md hover:scale-[1.02] transition-all duration-200">
          <div className="flex items-center gap-2 mb-3">
            <div className="p-2 bg-blue-500 rounded-lg">
              <Users className="w-4 h-4 text-white" />
            </div>
            <h3 className="font-semibold text-gray-800 text-sm">{t('company_page.overview_people_card')}</h3>
          </div>
          <div className="space-y-2">
            <div className="flex justify-between items-center">
              <span className="text-xs text-gray-500">{t('company_page.overview_shareholders')}</span>
              <span className="text-sm font-bold text-gray-800 bg-blue-50 px-2 py-0.5 rounded">
                {overViewData.noShareholders ? formatNumber(overViewData.noShareholders) : "N/A"}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-xs text-gray-500">{t('company_page.overview_employees')}</span>
              <span className="text-sm font-bold text-gray-800 bg-blue-50 px-2 py-0.5 rounded">
                {overViewData.noEmployees ? formatNumber(overViewData.noEmployees) : "N/A"}
              </span>
            </div>
          </div>
        </div>

        {/* Industry Info */}
        <div className="flex-1 min-w-[150px] bg-white rounded-xl p-4 border border-gray-200 shadow-sm hover:shadow-md hover:scale-[1.02] transition-all duration-200">
          <div className="flex items-center gap-2 mb-3">
            <div className="p-2 bg-blue-500 rounded-lg">
              <Briefcase className="w-4 h-4 text-white" />
            </div>
            <h3 className="font-semibold text-gray-800 text-sm">{t('company_page.overview_industry_card')}</h3>
          </div>
          <div className="space-y-2">
            <div className="flex justify-between items-center">
              <span className="text-xs text-gray-500">{t('company_page.overview_level_1')}</span>
              <span className="text-sm font-bold text-gray-800 bg-blue-50 px-2 py-0.5 rounded truncate max-w-[100px]" title={overViewData.industry}>
                {overViewData.industry || "N/A"}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-xs text-gray-500">{t('company_page.overview_level_2')}</span>
              <span className="text-sm font-bold text-gray-800 bg-blue-50 px-2 py-0.5 rounded truncate max-w-[100px]" title={overViewData.industryL2}>
                {overViewData.industryL2 || "N/A"}
              </span>
            </div>
          </div>
        </div>

        {/* Capital Info */}
        <div className="flex-1 min-w-[150px] bg-white rounded-xl p-4 border border-gray-200 shadow-sm hover:shadow-md hover:scale-[1.02] transition-all duration-200">
          <div className="flex items-center gap-2 mb-3">
            <div className="p-2 bg-blue-500 rounded-lg">
              <BarChart3 className="w-4 h-4 text-white" />
            </div>
            <h3 className="font-semibold text-gray-800 text-sm">{t('company_page.overview_capital_card')}</h3>
          </div>
          <div className="space-y-2">
            <div className="flex justify-between items-center">
              <span className="text-xs text-gray-500">{t('company_page.overview_charter')}</span>
              <span className="text-sm font-bold text-gray-800 bg-blue-50 px-2 py-0.5 rounded">
                {overViewData.charterCapital ? formatNumber(overViewData.charterCapital / 1000000000) + "B" : "N/A"}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-xs text-gray-500">{t('company_page.overview_foreign_pct')}</span>
              <span className="text-sm font-bold text-gray-800 bg-blue-50 px-2 py-0.5 rounded">
                {overViewData.foreignPercent != null ? (overViewData.foreignPercent * 100).toFixed(1) + "%" : "N/A"}
              </span>
            </div>
          </div>
        </div>

        {/* Industry L3 Card */}
        <div className="flex-1 min-w-[150px] bg-white rounded-xl p-4 border border-gray-200 shadow-sm hover:shadow-md hover:scale-[1.02] transition-all duration-200">
          <div className="flex items-center gap-2 mb-3">
            <div className="p-2 bg-blue-500 rounded-lg">
              <Building2 className="w-4 h-4 text-white" />
            </div>
            <h3 className="font-semibold text-gray-800 text-sm">{t('company_page.overview_sector_detail')}</h3>
          </div>
          <div className="text-center">
            <p className="text-sm font-bold text-gray-800 leading-tight" title={overViewData.industryL3}>
              {overViewData.industryL3 || overViewData.industry || "N/A"}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
