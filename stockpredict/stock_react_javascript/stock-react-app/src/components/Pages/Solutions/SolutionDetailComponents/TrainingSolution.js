import React,{useEffect,useState,useRef} from "react";
import DatePicker from "react-datepicker";

import "bootstrap/dist/css/bootstrap.min.css";
import { useForm } from "react-hook-form"
import ModelDetail from "../../models/ModelDetail";
import httpClient from "../../../../services/httpClient";
import { API_ENDPOINTS } from "../../../../constants/api";

const TrainingSolution = (props)=>{
    const [startDate,setStartDate] = useState(new Date(props.solution['start_training_date']));
    const [endDate,setEndDate] = useState(new Date(props.solution['end_training_date']))
    const [validation,setValidation] = useState(true)
    const [validateionNumber,setValidationNumber] = useState(0.2)
    const [rmseValue,setRmseValue] = useState(null)
    const [trainingStatus,setTrainingStatus] = useState('')
    const [trainingProgress, setTrainingProgress] = useState(0)
    const [isPolling, setIsPolling] = useState(false)
    const pollingIntervalRef = useRef(null)
    const pollAttemptsRef = useRef(0)
    // ~10 minutes at 3s interval — plenty of headroom for slow trainings
    // without polling forever if the backend silently dies.
    const MAX_POLL_ATTEMPTS = 200
    // eslint-disable-next-line no-unused-vars -- react-hook-form returns bindings not all used yet
    const { register,handleSubmit,reset,formState: { errors },watch} = useForm();

    const stopPolling = () => {
        setIsPolling(false);
        if (pollingIntervalRef.current) {
            clearInterval(pollingIntervalRef.current);
            pollingIntervalRef.current = null;
        }
        pollAttemptsRef.current = 0;
    };

    const handleValidationChange = ()=>{
        setValidation(!validation);
    }

    // Poll for training status
    const pollTrainingStatus = async (solutionId) => {
        pollAttemptsRef.current += 1;
        // Bail out if we've polled too long — assumption is the backend
        // forgot about us. Surface as a recoverable error rather than spin.
        if (pollAttemptsRef.current > MAX_POLL_ATTEMPTS) {
            stopPolling();
            setTrainingStatus('Training timed out. Please retry or contact support.');
            return;
        }

        try {
            const result = await httpClient.get(API_ENDPOINTS.SOLUTION_TRAINING_STATUS(solutionId));
            if (!result.success) {
                console.error('Error polling training status:', result.error);
                return;
            }
            const statusData = result.data;

            if (statusData.status === 'completed') {
                stopPolling();
                setTrainingProgress(100);

                const trainingResult = statusData.result;
                if (trainingResult && trainingResult.rmse !== undefined) {
                    setRmseValue(trainingResult.rmse);
                } else if (trainingResult && trainingResult.RMSE !== undefined) {
                    setRmseValue(trainingResult.RMSE);
                }
                setTrainingStatus('Training completed successfully!');

                if (props.onTrainingComplete && trainingResult) {
                    props.onTrainingComplete(trainingResult);
                }
            } else if (statusData.status === 'failed') {
                stopPolling();
                setTrainingStatus('Training failed: ' + (statusData.message || 'Unknown error'));
            } else if (statusData.status === 'not_found') {
                // Backend has no record. Most likely the in-memory training_status
                // dict was reset (service restart) or the request silently dropped.
                // Stop polling so the user can retry.
                stopPolling();
                setTrainingStatus('Training session not found on server. Please retry.');
            } else if (statusData.status === 'training') {
                const pct = typeof statusData.progress === 'number' ? statusData.progress : 0;
                setTrainingProgress(pct);
                const detail = statusData.message || 'Training in progress...';
                setTrainingStatus(pct > 0 ? `${detail} (${pct}%)` : detail);
            }
        } catch (error) {
            console.error('Error polling training status:', error);
            // Network blips are tolerated — pollAttemptsRef caps total time spent
        }
    };

    // Cleanup polling on unmount
    useEffect(() => {
        return () => {
            if (pollingIntervalRef.current) {
                clearInterval(pollingIntervalRef.current);
            }
        };
    }, []);

    const formSubmit = async () => {
        let data = {
            id: props.solution['id'],
            validation:validation,
            train_ratio:validateionNumber,
            start_date:startDate.toISOString().split('T')[0],
            end_date:endDate.toISOString().split('T')[0]
        }

        setTrainingStatus('Training in progress...')
        setTrainingProgress(0)
        setRmseValue(null)
        setIsPolling(true)
        pollAttemptsRef.current = 0;

        try {
            const response = await httpClient.post(API_ENDPOINTS.SOLUTION_TRAIN, data);

            if (response.success && response.data?.rmse !== undefined) {
                // Legacy synchronous training — done in one shot.
                setRmseValue(response.data.rmse);
                setTrainingStatus('Training completed successfully!');
                setTrainingProgress(100);
                stopPolling();

                if (props.onTrainingComplete) {
                    props.onTrainingComplete(response.data);
                }
            } else if (response.success && response.data?.RMSE !== undefined) {
                setRmseValue(response.data.RMSE);
                setTrainingStatus('Training completed successfully!');
                setTrainingProgress(100);
                stopPolling();

                if (props.onTrainingComplete) {
                    props.onTrainingComplete(response.data);
                }
            } else if (response.success) {
                // Async path — backend returns {status: "training"} and we poll.
                pollingIntervalRef.current = setInterval(() => {
                    pollTrainingStatus(props.solution['id']);
                }, 3000);
                pollTrainingStatus(props.solution['id']);
            } else {
                setTrainingStatus('Training failed: ' + (response.error?.message || 'Unknown error'));
                stopPolling();
            }
        } catch (error) {
            stopPolling();
            setTrainingStatus('Training failed: ' + (error.message || 'Unknown error'));
            console.error('Training error:', error);
        }
    }

    return (
        <div className="container-fluid">
            <div className="card border-0 shadow p-3">
                <form onSubmit={handleSubmit(formSubmit)}>
                    {/* Compact Training Configuration Section */}
                    <div className="row mb-3">
                        <div className="col-md-12">
                            <h6 className="text-muted mb-3">Training Configuration</h6>
                        </div>
                    </div>

                    {/* Form Controls - Compact 2-Column Layout */}
                    <div className="row g-2 mb-3">
                        {/* Date Range Section */}
                        <div className="col-md-3">
                            <label className="form-label form-label-sm mb-1"><small>Start Date</small></label>
                            <DatePicker
                                id="start_date"
                                selected={startDate}
                                dateFormat={"yyyy-MM-dd"}
                                onChange={(date)=>setStartDate(new Date(date))}
                                className="form-control form-control-sm"
                            />
                        </div>
                        <div className="col-md-3">
                            <label className="form-label form-label-sm mb-1"><small>End Date</small></label>
                            <DatePicker
                                id="end_date"
                                selected={endDate}
                                dateFormat={"yyyy-MM-dd"}
                                onChange={(date)=>setEndDate(new Date(date))}
                                className="form-control form-control-sm"
                            />
                        </div>

                        {/* Validation Controls */}
                        <div className="col-md-2">
                            <label className="form-label form-label-sm mb-1"><small>Validation Ratio</small></label>
                            <input
                                type="number"
                                step="0.01"
                                min="0"
                                max="1"
                                value={validateionNumber}
                                onChange={(e)=>setValidationNumber(e.target.value)}
                                className="form-control form-control-sm"
                            />
                        </div>
                        <div className="col-md-2 d-flex align-items-end">
                            <div className="form-check">
                                <input
                                    type="checkbox"
                                    checked={validation}
                                    onChange={handleValidationChange}
                                    className="form-check-input"
                                    id="validationCheck"
                                />
                                <label className="form-check-label" htmlFor="validationCheck">
                                    <small>Enable Validation</small>
                                </label>
                            </div>
                        </div>

                        {/* Train Button */}
                        <div className="col-md-2 d-flex align-items-end">
                            <button
                                type="submit"
                                className="btn btn-primary btn-sm w-100"
                                disabled={isPolling}
                            >
                                {isPolling ? 'Training...' : 'Train Model'}
                            </button>
                        </div>
                    </div>

                    {/* Model Details Section */}
                    <div className="row mb-3">
                        <div className="col-md-12">
                            <ModelDetail models={props.models} solution={props.solution}/>
                        </div>
                    </div>

                    {/* Status Messages */}
                    {trainingStatus && (
                        <div className="row mb-3">
                            <div className="col-md-12">
                                <div className={`alert alert-sm ${trainingStatus.includes('failed') || trainingStatus.includes('not found') || trainingStatus.includes('timed out') ? 'alert-danger' : trainingStatus.includes('progress') ? 'alert-info' : 'alert-success'} py-2`}>
                                    <small>{trainingStatus}</small>
                                    {isPolling && (
                                        <span className="spinner-border spinner-border-sm ms-2" role="status">
                                            <span className="visually-hidden">Loading...</span>
                                        </span>
                                    )}
                                </div>
                                {/* Live progress bar — reflects backend `progress` field */}
                                {(isPolling || (trainingProgress > 0 && trainingProgress < 100)) && (
                                    <div className="progress" style={{ height: '6px' }}>
                                        <div
                                            className="progress-bar progress-bar-striped progress-bar-animated"
                                            role="progressbar"
                                            style={{ width: `${trainingProgress}%` }}
                                            aria-valuenow={trainingProgress}
                                            aria-valuemin="0"
                                            aria-valuemax="100"
                                        />
                                    </div>
                                )}
                            </div>
                        </div>
                    )}

                    {/* RMSE Display */}
                    {rmseValue !== null && (
                        <div className="row mb-3">
                            <div className="col-md-12">
                                <div className="alert alert-success py-2">
                                    <small><strong>RMSE: </strong>{typeof rmseValue === 'number' ? rmseValue.toFixed(6) : rmseValue}</small>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Chart Container - Full Width */}
                    <div className="row">
                        <div className="col-md-12">
                            <div className="card border shadow-sm">
                                <div className="card-header bg-light py-2">
                                    <h6 className="mb-0"><small>Training Results Visualization</small></h6>
                                </div>
                                <div className="card-body p-3" style={{minHeight: '400px', backgroundColor: '#f8f9fa'}}>
                                    {/* Chart will be rendered here */}
                                    <div id="training-chart-container" style={{width: '100%', height: '380px'}}>
                                        <div className="d-flex align-items-center justify-content-center h-100 text-muted">
                                            <small>Chart will be displayed after training completion</small>
                                        </div>
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
export default TrainingSolution;
