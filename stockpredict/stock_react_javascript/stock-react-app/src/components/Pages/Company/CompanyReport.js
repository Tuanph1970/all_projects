import React from "react";
import { Tab, Tabs, TabList, TabPanel } from 'react-tabs';
import 'react-tabs/style/react-tabs.css';
import { useTranslation } from 'react-i18next';
import IncomeStatement from "./Reports/IncomeStatement";
import FinancialBalanceSheet from "./Reports/FinancialBalanceSheet";
import FinancialCashFlow from "./Reports/FinancialCashFlow";
import FinancialRatio from "./Reports/FinancialRatio";
export default function CompanyReport({symbol}) {
    const { t } = useTranslation();
    return (
        <div>
            <Tabs>
              <TabList>
                <Tab>{t('company_page.report_tab_income')}</Tab>
                <Tab>{t('company_page.report_tab_cashflow')}</Tab>
                <Tab>{t('company_page.report_tab_balance')}</Tab>
                <Tab>{t('company_page.report_tab_ratio')}</Tab>
              </TabList>

              <TabPanel>
                  <IncomeStatement symbol={symbol}/>
              </TabPanel>
              <TabPanel>
                  <FinancialCashFlow symbol={symbol}/>
              </TabPanel>
              <TabPanel>
                    <FinancialBalanceSheet symbol={symbol}/>
              </TabPanel>
              <TabPanel>
                <FinancialRatio symbol={symbol}/>
              </TabPanel>

          </Tabs>
        </div>
    );
}
