import React from "react";
import TimeSeriesList from "./TimeSeries/TimeSeriesList";
import ModelList from "./models/ModelList";
import SolutionList from "./Solutions/SolutionList";
export const Predict = () => {
  return (
      <div className="content-container">
          <h1> Predict </h1>
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
export const TimeSeries = () => {
  return (
      <div className="content-container">
          <TimeSeriesList/>

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


