import React from "react";
import { useTranslation } from 'react-i18next';
import ModelList from "./models/ModelList";
import SolutionList from "./Solutions/SolutionList";
export const Predict = () => {
  const { t } = useTranslation();
  return (
      <div className="content-container">
          <h1>{t('solutions.tab_predict')}</h1>
      </div>
  );
};
export const Models = () => {
  return (
      <div className="content-container">
          <ModelList></ModelList>
      </div>
  );
};
export const Solutions = () => {
  return (
      <div className="content-container">
         <SolutionList/>
      </div>
  );
};
const SolutionWrapper = () => {
  return (
    <div className="content-container">
       <SolutionList/>
    </div>
  );
}
export default SolutionWrapper


