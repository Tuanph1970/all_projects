import React from "react";
import { Tab, Tabs, TabList, TabPanel } from 'react-tabs';
import 'react-tabs/style/react-tabs.css';
import '../../styles/company-profile.css';
import { useTranslation } from 'react-i18next';
import CompanyOverView from "./Company/CompanyOverView";
import CompanyNew from "./Company/CompanyNew";
import CompanyEvents from "./Company/CompanyEvents";
import CompanyProfile from "./Company/CompanyProfile";
import CompanyReport from "./Company/CompanyReport";
import CompanyCharts from "./Company/CompanyCharts";
export const Company = ({ symbol }) => {
  const { t } = useTranslation();
  return (
    <div className="company-container">
        <Tabs>
          <TabList>
            <Tab>{t('company_page.tab_overview')}</Tab>
            <Tab>{t('company_page.tab_news')}</Tab>
            <Tab>{t('company_page.tab_events')}</Tab>
            <Tab>{t('company_page.tab_profiles')}</Tab>
            <Tab>{t('company_page.tab_reports')}</Tab>
            <Tab>{t('company_page.tab_charts')}</Tab>
          </TabList>

          <TabPanel>
              <CompanyOverView symbol = {symbol}/>
          </TabPanel>
          <TabPanel>
             <CompanyNew symbol = {symbol}/>
          </TabPanel>
          <TabPanel>
              <CompanyEvents symbol = {symbol}/>
          </TabPanel>
          <TabPanel>
             <CompanyProfile symbol={symbol}/>
          </TabPanel>
          <TabPanel>
            <CompanyReport symbol={symbol}/>
          </TabPanel>
          <TabPanel>
            <CompanyCharts symbol={symbol}/>
          </TabPanel>
      </Tabs>
    </div>
  );
};
