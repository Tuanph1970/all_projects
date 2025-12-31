import React,{useEffect,useState} from "react";
import { Tab, Tabs, TabList, TabPanel } from 'react-tabs';
import 'react-tabs/style/react-tabs.css';
import IncomeStatement from "./Reports/IncomeStatement";
import FinancialBalanceSheet from "./Reports/FinancialBalanceSheet";
import FinancialCashFlow from "./Reports/FinancialCashFlow";
import FinancialRatio from "./Reports/FinancialRatio";
export default function CompanyReport({symbol}) {
    return (
        <div>
            <Tabs>
              <TabList>
                <Tab>Income Statements</Tab>
                <Tab>Cash Flows</Tab>
                <Tab>Balance Sheet</Tab>
                <Tab>Ratio</Tab>
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