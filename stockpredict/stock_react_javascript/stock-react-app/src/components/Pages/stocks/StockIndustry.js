import React from "react";
import { useTranslation } from 'react-i18next';
export const StockIndustry = () => {
    const { t } = useTranslation();
    return (
        <div className="services">
            <h1>{t('stocks.table.industry_title')}</h1>
        </div>
    );
};
