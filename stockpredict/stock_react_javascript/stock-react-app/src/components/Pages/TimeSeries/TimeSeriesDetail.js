import React,{useEffect,useState} from "react";
import httpClient from "../../../services/httpClient";
import { API_ENDPOINTS } from "../../../constants/api";
import {Form, FormGroup} from 'react-bootstrap';
import DatePicker from "react-datepicker";
import "react-datepicker/dist/react-datepicker.css";
import '../../../node_modules/bootstrap/dist/css/bootstrap.min.css';

const TimeSeriesDetail = (props) => {
    const onSeriesNameChange = (name) =>{        
        let series = props.dataParentToChild;
        series.series_name = name;
        console.log(series);
        props.saveTimeSeries(series);
        
    }

    const [seriesTypeDropDowns,setSeriesTypeDropDown] = useState([]);
    const [isLoading, setIsLoading] = useState([]);    
    const [startDate,setStartDate] = useState([new Date()]);
    const [endDate,setEndDate] = useState([new Date()])  
    const startDateOnChange = (date) =>{
        
        setStartDate(date)
    }
    const endDateOnChange = (date) =>{
        setEndDate(date)
    }  
    const getSeriesType = async () => {
      try {
        const result = await httpClient.get(API_ENDPOINTS.TIME_SERIES_CATEGORIES);
        if (result.success && result.data) {
          setSeriesTypeDropDown(result.data);
        }
        setIsLoading(true);
      }
      catch (error) {
        console.error('Error fetching series types:', error);
      }
      finally {
        setIsLoading(false);
      }
  };
  
  useEffect(() => {
      getSeriesType();
  }, []);

    
    if (isLoading) {
      return <p>Loading data...</p>;
    } else {
    return (
      <div width='400px'>
          <Form.Group className="mb-3" controlId="SeriesName">
             <Form.Label>Time Series Name</Form.Label>
             <Form.Control type="text" placeholder="Enter Time Series Name" value={props.displayTimeSeries.series_name} onChange={onSeriesNameChange('bbb')} />
          </Form.Group>

          <FormGroup className="mb-3">          
               <Form.Label>Start Date</Form.Label>
               <DatePicker selected={new Date(startDate)} onChange={(date) => startDateOnChange(date)} />
               
          </FormGroup>
          <FormGroup className="mb-3"> 
                <Form.Label>End  Date</Form.Label>
                <DatePicker selected={new Date(endDate)} onChange={(date) => endDateOnChange(date)} />
                
          </FormGroup>
          <Form.Group controlId="formGridPassword">
          <Form.Select aria-label="Default select example">
             {seriesTypeDropDowns.map((data) => (
              <option value={data.id}>
                {data.series_type_name}
              </option>
             ))}               
          </Form.Select>
           </Form.Group>
      </div>
    )}     
      
};
export default TimeSeriesDetail;
