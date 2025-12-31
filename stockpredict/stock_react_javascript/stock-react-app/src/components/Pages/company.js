import React from "react";
import { Tab, Tabs, TabList, TabPanel } from 'react-tabs';
import 'react-tabs/style/react-tabs.css';
import '../../styles/company-profile.css';
import CompanyOverView from "./Company/CompanyOverView";
import CompanyNew from "./Company/CompanyNew";
import CompanyEvents from "./Company/CompanyEvents";
import CompanyDividents from "./Company/CompanyDividents";
import CompanyProfile from "./Company/CompanyProfile";
import CompanyReport from "./Company/CompanyReport";
import CompanyCharts from "./Company/CompanyCharts";
export const Company = ({ symbol }) => {

    return (
      <div className="company-container">
          <Tabs>
            <TabList>
              <Tab>OverView</Tab>
              <Tab>News</Tab>
              <Tab>Events</Tab>
              <Tab>Dividents</Tab>
              <Tab>Profiles</Tab>
              <Tab>Reports</Tab>
              
              <Tab>Charts</Tab>


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
                <CompanyDividents symbol={symbol}/>
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



