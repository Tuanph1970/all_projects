import React,{useEffect,useState,useRef} from "react";
import { useTranslation } from 'react-i18next';
import DatePicker from "react-datepicker";

import "bootstrap/dist/css/bootstrap.min.css";
import { useForm } from "react-hook-form"
import ModelDetail from "../../models/ModelDetail";
import httpClient from "../../../../services/httpClient";
import { API_ENDPOINTS } from "../../../../constants/api";

// A solution can be saved without training dates (NULL in the DB). `new Date(null)`
// silently collapses to the 1970 epoch, so the tab would POST a 1970-01-01 range
// that has no price data and training fails with a 404. Parse defensively and fall
// back to a sane default window (last 2 years) when the stored value is missing or
// unparseable.
const parseTrainingDate = (value, fallback) => {
    if (value === null || value === undefined || value === '') return fallback;
    const parsed = new Date(value);
    return Number.isNaN(parsed.getTime()) ? fallback : parsed;
};

// Backlog #106. Calendar-day half-life for the news decay, mirroring
// prediction-service's NEWS_HALFLIFE_DEFAULT. The backend clamps this into
// [0.5, 90] and falls back to the default on anything unusable, so the UI does
// not have to be the last line of defence — but it should not send nonsense.
const NEWS_HALFLIFE_DEFAULT = 5;

const defaultEndDate = () => new Date();
const defaultStartDate = () => {
    const d = new Date();
    d.setFullYear(d.getFullYear() - 2);
    return d;
};

const TrainingSolution = (props)=>{
    const { t } = useTranslation();
    const [startDate,setStartDate] = useState(() => parseTrainingDate(props.solution['start_training_date'], defaultStartDate()));
    const [endDate,setEndDate] = useState(() => parseTrainingDate(props.solution['end_training_date'], defaultEndDate()))
    const [validation,setValidation] = useState(true)
    const [validateionNumber,setValidationNumber] = useState(0.2)
    // Backlog #106 — news as PAST covariates. Off by default, matching the
    // backend's NEWS_FEATURES_DEFAULT: on today's corpus the two columns are
    // zero for almost every bar, so switching it on for every solution would
    // add two near-constant features and move the numbers for no gain.
    const [includeNews,setIncludeNews] = useState(false)
    const [newsHalflife,setNewsHalflife] = useState(NEWS_HALFLIFE_DEFAULT)
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
            setTrainingStatus(t('solutions.training_timeout'));
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
                setTrainingStatus(t('solutions.training_complete'));

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
                setTrainingStatus(t('solutions.training_not_found'));
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
        // Guard against missing/invalid dates (e.g. the field was cleared) so we
        // never POST a bogus range that the backend rejects with a 404.
        if (!startDate || !endDate || Number.isNaN(startDate.getTime()) || Number.isNaN(endDate.getTime())) {
            setTrainingStatus(t('solutions.training_invalid_dates'));
            return;
        }
        if (startDate >= endDate) {
            setTrainingStatus(t('solutions.training_invalid_range'));
            return;
        }

        let data = {
            id: props.solution['id'],
            validation:validation,
            train_ratio:validateionNumber,
            start_date:startDate.toISOString().split('T')[0],
            end_date:endDate.toISOString().split('T')[0],
            // Backlog #106. Sent only as the operator set them; the backend
            // decides the default and clamps the half-life.
            include_news: includeNews,
            news_halflife_days: Number(newsHalflife) || NEWS_HALFLIFE_DEFAULT
        }

        setTrainingStatus(t('solutions.training_in_progress'))
        setTrainingProgress(0)
        setRmseValue(null)
        setIsPolling(true)
        pollAttemptsRef.current = 0;

        try {
            const response = await httpClient.post(API_ENDPOINTS.SOLUTION_TRAIN, data);

            if (response.success && response.data?.rmse !== undefined) {
                // Legacy synchronous training — done in one shot.
                setRmseValue(response.data.rmse);
                setTrainingStatus(t('solutions.training_complete'));
                setTrainingProgress(100);
                stopPolling();

                if (props.onTrainingComplete) {
                    props.onTrainingComplete(response.data);
                }
            } else if (response.success && response.data?.RMSE !== undefined) {
                setRmseValue(response.data.RMSE);
                setTrainingStatus(t('solutions.training_complete'));
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
                            <h6 className="text-muted mb-3">{t('solutions.training_config')}</h6>
                        </div>
                    </div>

                    {/* Form Controls - Compact 2-Column Layout */}
                    <div className="row g-2 mb-3">
                        {/* Date Range Section */}
                        <div className="col-md-3">
                            <label className="form-label form-label-sm mb-1"><small>{t('solutions.date_start')}</small></label>
                            <DatePicker
                                id="start_date"
                                selected={startDate}
                                dateFormat={"yyyy-MM-dd"}
                                onChange={(date)=>setStartDate(date)}
                                className="form-control form-control-sm"
                            />
                        </div>
                        <div className="col-md-3">
                            <label className="form-label form-label-sm mb-1"><small>{t('solutions.date_end')}</small></label>
                            <DatePicker
                                id="end_date"
                                selected={endDate}
                                dateFormat={"yyyy-MM-dd"}
                                onChange={(date)=>setEndDate(date)}
                                className="form-control form-control-sm"
                            />
                        </div>

                        {/* Validation Controls */}
                        <div className="col-md-2">
                            <label className="form-label form-label-sm mb-1"><small>{t('solutions.validation_ratio')}</small></label>
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
                                    <small>{t('solutions.enable_validation')}</small>
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
                                {isPolling ? t('solutions.training_btn') : t('solutions.train_btn')}
                            </button>
                        </div>
                    </div>

                    {/* Backlog #106 — news as PAST covariates. Never future: tomorrow's
                        coverage is not knowable today, which is the same rule
                        #104/#105 enforce for indicators. */}
                    <div className="row g-2 mb-3 align-items-end">
                        <div className="col-md-4">
                            <div className="form-check">
                                <input
                                    type="checkbox"
                                    checked={includeNews}
                                    onChange={(e)=>setIncludeNews(e.target.checked)}
                                    className="form-check-input"
                                    id="includeNewsCheck"
                                />
                                <label className="form-check-label" htmlFor="includeNewsCheck">
                                    <small>{t('solutions.include_news')}</small>
                                </label>
                            </div>
                        </div>
                        {includeNews && (
                            <div className="col-md-3">
                                <label className="form-label form-label-sm mb-1" htmlFor="newsHalflife">
                                    <small>{t('solutions.news_halflife')}</small>
                                </label>
                                <input
                                    id="newsHalflife"
                                    type="number"
                                    step="0.5"
                                    min="0.5"
                                    max="90"
                                    value={newsHalflife}
                                    onChange={(e)=>setNewsHalflife(e.target.value)}
                                    className="form-control form-control-sm"
                                />
                            </div>
                        )}
                        {includeNews && (
                            <div className="col-md-5">
                                <small className="text-muted d-block">
                                    &#128240; {t('solutions.news_covariate_note')}
                                </small>
                            </div>
                        )}
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
                                    <h6 className="mb-0"><small>{t('solutions.training_results_title')}</small></h6>
                                </div>
                                <div className="card-body p-3" style={{minHeight: '400px', backgroundColor: '#f8f9fa'}}>
                                    {/* Chart will be rendered here */}
                                    <div id="training-chart-container" style={{width: '100%', height: '380px'}}>
                                        <div className="d-flex align-items-center justify-content-center h-100 text-muted">
                                            <small>{t('solutions.chart_pending')}</small>
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
