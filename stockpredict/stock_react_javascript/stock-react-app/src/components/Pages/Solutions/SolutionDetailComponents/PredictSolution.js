import React,{useEffect,useState} from "react";
import DatePicker from "react-datepicker";
import "bootstrap/dist/css/bootstrap.min.css";
import { useForm } from "react-hook-form"
import httpClient from "../../../../services/httpClient";
import { API_ENDPOINTS } from "../../../../constants/api";

const PredictSolution = (props)=>{
    const [startDate, setStartDate] = useState(new Date());
    const [endDate, setEndDate] = useState(new Date());
    const [predictions, setPredictions] = useState(null);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState(null);
    const [modelInfo, setModelInfo] = useState(null);
    const { register, handleSubmit, reset, formState: { errors }, watch } = useForm();

    // Helper function to add business days (skip weekends)
    const addBusinessDays = (date, days) => {
        const result = new Date(date);
        let daysToAdd = days;
        while (daysToAdd > 0) {
            result.setDate(result.getDate() + 1);
            if (result.getDay() !== 0 && result.getDay() !== 6) {
                daysToAdd--;
            }
        }
        return result;
    };

    // Function to set end date to max prediction length from start date
    const setMaxPrediction = () => {
        if (modelInfo && modelInfo.output_chunk_length && startDate) {
            const maxEndDate = addBusinessDays(startDate, modelInfo.output_chunk_length - 1);
            setEndDate(maxEndDate);
        }
    };

    // Load prediction dates from solution when component mounts (for returning to page)
    useEffect(() => {
        console.log('[PredictSolution] props.solution changed:', props.solution);
        console.log('[PredictSolution] props.solution.prediction_dates:', props.solution?.prediction_dates);

        // Check if solution has prediction_dates from backend (loaded from database)
        if (props.solution && props.solution.prediction_dates) {
            const { prediction_start_date, prediction_end_date, output_chunk_length, training_end_date } = props.solution.prediction_dates;

            console.log('[PredictSolution] Setting dates from solution.prediction_dates:', {
                prediction_start_date,
                prediction_end_date,
                output_chunk_length,
                training_end_date
            });

            if (prediction_start_date) {
                setStartDate(new Date(prediction_start_date));
            }
            if (prediction_end_date) {
                setEndDate(new Date(prediction_end_date));
            }

            setModelInfo({
                output_chunk_length,
                training_end_date
            });

            console.log('Prediction dates loaded from solution:', props.solution.prediction_dates);
        } else {
            console.log('[PredictSolution] No prediction_dates found in solution');
        }
    }, [props.solution]);

    // Update dates when predictionDates prop changes (from training completion during same session)
    useEffect(() => {
        if (props.predictionDates) {
            const { prediction_start_date, prediction_end_date, output_chunk_length, training_end_date } = props.predictionDates;

            if (prediction_start_date) {
                setStartDate(new Date(prediction_start_date));
            }
            if (prediction_end_date) {
                setEndDate(new Date(prediction_end_date));
            }

            // Store model info for display
            setModelInfo({
                output_chunk_length,
                training_end_date
            });

            console.log('Prediction dates auto-filled from training:', props.predictionDates);
        }
    }, [props.predictionDates]);

    // Also update if trainedModelInfo changes
    useEffect(() => {
        if (props.trainedModelInfo) {
            setModelInfo(prev => ({
                ...prev,
                ...props.trainedModelInfo
            }));
        }
    }, [props.trainedModelInfo]);

    const formSubmit = async () => {
        let data = {
            id: props.solution['id'],
            start_date: startDate.toISOString().split('T')[0],
            end_date: endDate.toISOString().split('T')[0]
        }

        setIsLoading(true);
        setError(null);
        setPredictions(null);

        try {
            const result = await httpClient.post(API_ENDPOINTS.SOLUTION_PREDICT, data, { timeout: 120000 });
            if (result.success && result.data) {
                setPredictions(result.data);
                console.log('Prediction results:', result.data);
            } else {
                setError(result.error?.message || 'Prediction failed');
            }
        } catch (err) {
            setError(err.message || 'Prediction failed');
            console.error('Prediction error:', err);
        } finally {
            setIsLoading(false);
        }
    }

    return (
        <div className="container-fluid">
            <div className="card border-0 shadow p-3">
                <form onSubmit={handleSubmit(formSubmit)}>
                    {/* Header */}
                    <div className="row mb-3">
                        <div className="col-md-12">
                            <h6 className="text-muted mb-3">Prediction Configuration</h6>
                        </div>
                    </div>

                    {/* Model Info Banner (shows after training) */}
                    {modelInfo && modelInfo.training_end_date && (
                        <div className="row mb-3">
                            <div className="col-md-12">
                                <div className="alert alert-info py-2">
                                    <small>
                                        <strong>Model Ready:</strong> Trained until {modelInfo.training_end_date}
                                        {modelInfo.output_chunk_length && (
                                            <span> | <strong>Max prediction: {modelInfo.output_chunk_length} days</strong> (auto-adjusted if exceeded)</span>
                                        )}
                                        {modelInfo.rmse && (
                                            <span> | RMSE: {typeof modelInfo.rmse === 'number' ? modelInfo.rmse.toFixed(6) : modelInfo.rmse}</span>
                                        )}
                                    </small>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Date Range Controls */}
                    <div className="row g-2 mb-3">
                        <div className="col-md-3">
                            <label className="form-label form-label-sm mb-1"><small>Start Date</small></label>
                            <DatePicker
                                id="start_date"
                                selected={startDate}
                                dateFormat={"yyyy-MM-dd"}
                                onChange={(date) => setStartDate(new Date(date))}
                                className="form-control form-control-sm"
                            />
                        </div>
                        <div className="col-md-3">
                            <label className="form-label form-label-sm mb-1"><small>End Date</small></label>
                            <div className="input-group input-group-sm">
                                <DatePicker
                                    id="end_date"
                                    selected={endDate}
                                    dateFormat={"yyyy-MM-dd"}
                                    onChange={(date) => setEndDate(new Date(date))}
                                    className="form-control form-control-sm"
                                />
                                {modelInfo && modelInfo.output_chunk_length && (
                                    <button
                                        type="button"
                                        className="btn btn-outline-secondary btn-sm"
                                        onClick={setMaxPrediction}
                                        title={`Set to max ${modelInfo.output_chunk_length} days`}
                                    >
                                        Max
                                    </button>
                                )}
                            </div>
                        </div>
                        <div className="col-md-2 d-flex align-items-end">
                            <button
                                type="submit"
                                className="btn btn-success btn-sm w-100"
                                disabled={isLoading}
                            >
                                {isLoading ? 'Predicting...' : 'Predict'}
                            </button>
                        </div>
                    </div>

                    {/* Error Message */}
                    {error && (
                        <div className="row mb-3">
                            <div className="col-md-12">
                                <div className="alert alert-danger py-2">
                                    <small>{error}</small>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Predictions Summary */}
                    {predictions && (
                        <div className="row mb-3">
                            <div className="col-md-12">
                                <div className="alert alert-success py-2">
                                    <small>
                                        <strong>Prediction Complete:</strong>
                                        {predictions.predict && predictions.predict.length > 0 && (
                                            <span> {predictions.predict.length} prediction points generated</span>
                                        )}
                                    </small>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Chart Container */}
                    <div className="row">
                        <div className="col-md-12">
                            <div className="card border shadow-sm">
                                <div className="card-header bg-light py-2">
                                    <h6 className="mb-0"><small>Prediction Results</small></h6>
                                </div>
                                <div className="card-body p-3" style={{minHeight: '400px', backgroundColor: '#f8f9fa'}}>
                                    <div id="prediction-chart-container" style={{width: '100%', height: '380px'}}>
                                        {isLoading ? (
                                            <div className="d-flex align-items-center justify-content-center h-100">
                                                <div className="spinner-border text-primary" role="status">
                                                    <span className="visually-hidden">Loading...</span>
                                                </div>
                                            </div>
                                        ) : predictions ? (
                                            <div className="p-3">
                                                {/* Simple table display of predictions */}
                                                {predictions.predict && predictions.predict.length > 0 && (
                                                    <div className="table-responsive" style={{maxHeight: '350px', overflowY: 'auto'}}>
                                                        <table className="table table-sm table-striped">
                                                            <thead className="sticky-top bg-white">
                                                                <tr>
                                                                    <th>Date</th>
                                                                    <th>Predicted Price</th>
                                                                </tr>
                                                            </thead>
                                                            <tbody>
                                                                {predictions.predict.map((item, index) => (
                                                                    <tr key={index}>
                                                                        <td>{item.tradingdate ? new Date(item.tradingdate).toLocaleDateString() : '-'}</td>
                                                                        <td>{item.close ? item.close.toFixed(2) : '-'}</td>
                                                                    </tr>
                                                                ))}
                                                            </tbody>
                                                        </table>
                                                    </div>
                                                )}
                                            </div>
                                        ) : (
                                            <div className="d-flex align-items-center justify-content-center h-100 text-muted">
                                                <small>
                                                    {props.predictionDates
                                                        ? 'Dates auto-filled from training. Click "Predict" to generate predictions.'
                                                        : 'Complete training first, then prediction dates will be auto-filled.'}
                                                </small>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </form>
            </div>
        </div>
    )
}
export default PredictSolution;
