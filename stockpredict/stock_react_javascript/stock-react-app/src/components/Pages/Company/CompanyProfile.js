import React, { useEffect, useState } from "react";
import companyService from "../../../services/companyService";
import { useTranslation } from 'react-i18next';
import {
  Building2,
  FileText,
  History,
  Lightbulb,
  AlertTriangle,
  Target,
  ChevronDown,
  ChevronUp,
} from "lucide-react";

export default function CompanyProfile({ symbol }) {
  const { t } = useTranslation();
  const [profileData, setProfileData] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [expandedSections, setExpandedSections] = useState({});

  useEffect(() => {
    loadCompanyProfile();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [symbol]);

  const loadCompanyProfile = async () => {
    if (!companyService.isValidSymbol(symbol)) {
      setError(t('company_page.profile_invalid_symbol'));
      return;
    }

    try {
      setIsLoading(true);
      setError(null);

      const result = await companyService.getCompanyProfile(symbol);

      if (result.success) {
        setProfileData(result.data);
        // Initialize all sections as expanded
        const sections = {};
        profileFields.forEach((field) => {
          sections[field.key] = true;
        });
        setExpandedSections(sections);
      } else {
        setError(result.error);
      }
    } catch (err) {
      setError(t('company_page.profile_load_error'));
    } finally {
      setIsLoading(false);
    }
  };

  const toggleSection = (key) => {
    setExpandedSections((prev) => ({
      ...prev,
      [key]: !prev[key],
    }));
  };

  const profileFields = [
    {
      label: t('company_page.profile_section_profile'),
      key: "companyProfile",
      icon: FileText,
      color: "indigo",
    },
    {
      label: t('company_page.profile_section_history'),
      key: "history",
      icon: History,
      color: "purple",
    },
    {
      label: t('company_page.profile_section_industry'),
      key: "industry",
      icon: Building2,
      color: "blue",
    },
    {
      label: t('company_page.profile_section_industry_l2'),
      key: "industryL2",
      icon: Target,
      color: "cyan",
    },
    {
      label: t('company_page.profile_section_industry_l3'),
      key: "industryL3",
      icon: Lightbulb,
      color: "amber",
    },
  ];

  const getColorClasses = (color) => {
    const colors = {
      blue: {
        bg: "bg-blue-500",
        bgLight: "bg-blue-50",
        border: "border-blue-200",
        text: "text-blue-700",
        icon: "text-blue-500",
      },
      indigo: {
        bg: "bg-indigo-500",
        bgLight: "bg-indigo-50",
        border: "border-indigo-200",
        text: "text-indigo-700",
        icon: "text-indigo-500",
      },
      purple: {
        bg: "bg-purple-500",
        bgLight: "bg-purple-50",
        border: "border-purple-200",
        text: "text-purple-700",
        icon: "text-purple-500",
      },
      amber: {
        bg: "bg-amber-500",
        bgLight: "bg-amber-50",
        border: "border-amber-200",
        text: "text-amber-700",
        icon: "text-amber-500",
      },
      red: {
        bg: "bg-red-500",
        bgLight: "bg-red-50",
        border: "border-red-200",
        text: "text-red-700",
        icon: "text-red-500",
      },
      green: {
        bg: "bg-green-500",
        bgLight: "bg-green-50",
        border: "border-green-200",
        text: "text-green-700",
        icon: "text-green-500",
      },
      cyan: {
        bg: "bg-cyan-500",
        bgLight: "bg-cyan-50",
        border: "border-cyan-200",
        text: "text-cyan-700",
        icon: "text-cyan-500",
      },
    };
    return colors[color] || colors.blue;
  };

  if (isLoading) {
    return (
      <div className="p-6">
        <div className="animate-pulse space-y-4">
          {[...Array(5)].map((_, i) => (
            <div
              key={i}
              className="h-24 bg-gray-200 rounded-xl"
            ></div>
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6">
        <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-center">
          <AlertTriangle className="w-12 h-12 text-red-400 mx-auto mb-3" />
          <p className="text-red-700 font-medium">{error}</p>
        </div>
      </div>
    );
  }

  if (!profileData) {
    return (
      <div className="p-6">
        <div className="bg-gray-50 border border-gray-200 rounded-xl p-6 text-center">
          <FileText className="w-12 h-12 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500">{t('company_page.profile_no_data')}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-4 space-y-4">
      {/* Header */}
      <div className="bg-gradient-to-r from-slate-700 to-slate-900 rounded-xl p-6 text-white">
        <div className="flex items-center gap-3">
          <Building2 className="w-8 h-8" />
          <div>
            <h2 className="text-xl font-bold">
              {profileData.ticker || symbol}
            </h2>
            <p className="text-slate-300 text-sm">
              {t('company_page.profile_subtitle')}
            </p>
          </div>
        </div>
      </div>

      {/* Profile Sections */}
      <div className="space-y-3">
        {profileFields.map(({ label, key, icon: Icon, color }) => {
          const colors = getColorClasses(color);
          const content = profileData[key];
          const isExpanded = expandedSections[key];

          if (!content) return null;

          return (
            <div
              key={key}
              className={`bg-white rounded-xl border ${colors.border} shadow-sm overflow-hidden`}
            >
              {/* Section Header */}
              <button
                onClick={() => toggleSection(key)}
                className={`w-full px-5 py-4 flex items-center justify-between ${colors.bgLight} hover:opacity-90 transition-opacity`}
              >
                <div className="flex items-center gap-3">
                  <div className={`p-2 ${colors.bg} rounded-lg`}>
                    <Icon className="w-5 h-5 text-white" />
                  </div>
                  <span className={`font-semibold ${colors.text}`}>{label}</span>
                </div>
                {isExpanded ? (
                  <ChevronUp className={`w-5 h-5 ${colors.icon}`} />
                ) : (
                  <ChevronDown className={`w-5 h-5 ${colors.icon}`} />
                )}
              </button>

              {/* Section Content */}
              {isExpanded && (
                <div className="px-5 py-4 border-t border-gray-100">
                  <p className="text-gray-700 leading-relaxed whitespace-pre-line">
                    {content}
                  </p>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
