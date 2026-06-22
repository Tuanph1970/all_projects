import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Button, Form, Row, Col, Alert, Spinner } from 'react-bootstrap';
import DatePicker from 'react-datepicker';
import UnifiedFinancialChart from '../../ui/UnifiedFinancialChart';
import IndicatorSelector from './IndicatorSelector';
import solutionService from '../../../services/solutionService';
import indicatorService from '../../../services/indicatorService';
import httpClient from '../../../services/httpClient';
import { API_ENDPOINTS } from '../../../constants/api';
import 'react-datepicker/dist/react-datepicker.css';
import './SolutionModal.css';

// Both tabs render the same unified single-panel chart for a consistent look.
const FinancialPredictionChart = ({ data, ticker }) => <UnifiedFinancialChart data={data} ticker={ticker} />;
const FinancialTrainingChart = ({ data, ticker }) => <UnifiedFinancialChart data={data} ticker={ticker} />;

// Map a backend point (training `predictions[]` or prediction `chart[]`) to the
// canonical chart shape UnifiedFinancialChart expects. Shared by the Training and
// Prediction tabs so both charts show the same series. `close` is deliberately
// omitted — it equals `actual`, so emitting both draws duplicate overlapping lines
// (the chart falls back to `actual` for volume coloring / edge indicator).
const apiPointToChartPoint = (item) => ({
  date: item.date || item.tradingdate || item.timestamp,
  actual: item.actual_price !== undefined ? item.actual_price : (item.actual !== undefined ? item.actual : item.close),
  predicted: item.predicted_price !== undefined ? item.predicted_price : (item.predicted !== undefined ? item.predicted : item.prediction),
  validation: item.validation_price !== undefined ? item.validation_price : item.validation,
  // Trend — price/left axis (overlays)
  sma_20: item.sma_20 || item.sma,
  sma_50: item.sma_50,
  ema_12: item.ema_12 || item.ema,
  wma: item.wma,
  dema: item.dema,
  tema: item.tema,
  psar: item.psar,
  vwap: item.vwap,
  supertrend: item.supertrend,
  ichimoku_conv: item.ichimoku_conv,
  ichimoku_base: item.ichimoku_base,
  ichimoku_a: item.ichimoku_a,
  ichimoku_b: item.ichimoku_b,
  // Trend — right axis (oscillators)
  adx: item.adx,
  aroon_up: item.aroon_up,
  aroon_down: item.aroon_down,
  vortex_pos: item.vortex_pos,
  vortex_neg: item.vortex_neg,
  // Momentum — right axis
  rsi: item.rsi,
  rsi_signal: item.rsi_signal,
  macd: item.macd,
  macd_signal: item.macd_signal || item.signal,
  macd_histogram: item.macd_histogram || item.histogram,
  cci: item.cci,
  stoch_k: item.stoch_k,
  stoch_d: item.stoch_d,
  stoch_rsi_k: item.stoch_rsi_k,
  stoch_rsi_d: item.stoch_rsi_d,
  williams_r: item.williams_r,
  roc: item.roc,
  mom: item.mom,
  tsi: item.tsi,
  uo: item.uo,
  ao: item.ao,
  // Volatility — bands on price axis, scalars on right axis
  atr: item.atr,
  stddev: item.stddev,
  hv: item.hv,
  bb_upper: item.bb_upper,
  bb_middle: item.bb_middle,
  bb_lower: item.bb_lower,
  kc_upper: item.kc_upper,
  kc_middle: item.kc_middle,
  kc_lower: item.kc_lower,
  dc_upper: item.dc_upper,
  dc_middle: item.dc_middle,
  dc_lower: item.dc_lower,
  // Volume — right axis (flow/oscillators), raw volume drawn below
  volume: item.volume,
  volume_sma: item.volume_sma,
  volume_ma: item.volume_ma,
  obv: item.obv,
  mfi: item.mfi,
  cmf: item.cmf,
  cho: item.cho,
  eom: item.eom,
  fi: item.fi,
  nvi: item.nvi,
  pvi: item.pvi,
  vosc: item.vosc,
  ad: item.ad,
});

// Build the Prediction-tab chart series from a /solutions/predict response (or a
// persisted prediction_result). Prefers the rich `chart` array (real history with
// indicators + volume + a backtest line, same shape as the Training tab); falls
// back to the legacy bare `actual`/`predict` closes. The `future` forecast is
// always appended as a predicted-only extension. Returns chronologically sorted data.
const buildPredictionChartData = (predData) => {
  if (!predData) return [];
  const hasRich = Array.isArray(predData.chart) && predData.chart.length > 0;
  let chartData = [];

  if (hasRich) {
    chartData = predData.chart.map(apiPointToChartPoint);
  } else if (Array.isArray(predData.actual)) {
    predData.actual.forEach(item => {
      chartData.push({ date: item.tradingdate, actual: item.close, predicted: null });
    });
    if (Array.isArray(predData.predict)) {
      predData.predict.forEach(item => {
        const i = chartData.findIndex(d => d.date === item.tradingdate);
        if (i >= 0) chartData[i].predicted = item.close;
        else chartData.push({ date: item.tradingdate, actual: null, predicted: item.close });
      });
    }
  }

  // Future forecast — the only data present when forecasting a future date range.
  if (Array.isArray(predData.future)) {
    predData.future.forEach(item => {
      const i = chartData.findIndex(d => d.date === item.tradingdate);
      if (i >= 0) chartData[i].predicted = item.close;
      else chartData.push({ date: item.tradingdate, actual: null, predicted: item.close });
    });
  }

  chartData.sort((a, b) => new Date(a.date) - new Date(b.date));
  return chartData;
};

const SolutionModal = ({ show, onHide, solution, onSave }) => {
  const { t } = useTranslation();
  const [activeTab, setActiveTab] = useState('general');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  // Tab 1: General Information State
  const [solutionName, setSolutionName] = useState('');
  const [ticker, setTicker] = useState('');
  const [modelId, setModelId] = useState('');
  const [target, setTarget] = useState('close');
  const [indicators, setIndicators] = useState(null);

  // Available options
  const [models, setModels] = useState([]);
  const [tickers, setTickers] = useState([]);
  const [selectedModel, setSelectedModel] = useState(null);

  // Tab 2: Training State
  const [trainStartDate, setTrainStartDate] = useState(new Date());
  const [trainEndDate, setTrainEndDate] = useState(new Date());
  const [validation, setValidation] = useState(true);
  const [trainRatio, setTrainRatio] = useState(0.8);
  const [trainingStatus, setTrainingStatus] = useState(null);
  const [trainingResult, setTrainingResult] = useState(null);
  const [trainingSuggestions, setTrainingSuggestions] = useState([]);
  const [indicatorChartData, setIndicatorChartData] = useState([]);
  const [dateRangeRecommendation, setDateRangeRecommendation] = useState(null);
  const [calculatingDates, setCalculatingDates] = useState(false);

  // Tab 3: Prediction State
  const [predictStartDate, setPredictStartDate] = useState(new Date());
  const [predictEndDate, setPredictEndDate] = useState(new Date());
  // predictionResult value is set by callers but not yet consumed in the
  // render path; kept so the data is available when a future result panel
  // reads it.
  // eslint-disable-next-line no-unused-vars
  const [predictionResult, setPredictionResult] = useState(null);
  const [predictionChartData, setPredictionChartData] = useState([]);
  const [predictionModelInfo, setPredictionModelInfo] = useState(null); // Store output_chunk_length and training info

  useEffect(() => {
    if (show) {
      loadInitialData();
      if (solution) {
        populateSolutionData(solution);
      } else {
        resetForm();
      }
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [show, solution]);

  // Helper function to add business days (skip weekends)
  const addBusinessDays = (date, days) => {
    const result = new Date(date);
    let daysToAdd = days;
    while (daysToAdd > 0) {
      result.setDate(result.getDate() + 1);
      // Skip weekends (0 = Sunday, 6 = Saturday)
      if (result.getDay() !== 0 && result.getDay() !== 6) {
        daysToAdd--;
      }
    }
    return result;
  };

  // Function to set end date to max prediction length from start date
  const setMaxPrediction = () => {
    if (predictionModelInfo && predictionModelInfo.output_chunk_length && predictStartDate) {
      const maxEndDate = addBusinessDays(predictStartDate, predictionModelInfo.output_chunk_length - 1);
      setPredictEndDate(maxEndDate);
    }
  };

  const loadInitialData = async () => {
    try {
      setLoading(true);
      // Load models - using httpClient to include JWT token for user-specific models
      const modelsResponse = await httpClient.get(API_ENDPOINTS.MODELS_ALL);
      if (modelsResponse.success) {
        setModels(modelsResponse.data || []);
      } else {
        throw new Error(modelsResponse.error?.message || 'Failed to fetch models');
      }

      // Load tickers
      const tickersResponse = await httpClient.get(API_ENDPOINTS.SOLUTION_TICKERS);
      if (tickersResponse.success) {
        setTickers(tickersResponse.data || []);
      } else {
        throw new Error(tickersResponse.error?.message || 'Failed to fetch tickers');
      }

      setError(null);
    } catch (err) {
      setError('Failed to load initial data: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const populateSolutionData = (sol) => {
    setSolutionName(sol.solution_name || '');
    setTicker(sol.ticker || '');
    setModelId(sol.model_id || '');
    setTarget(sol.target || 'close');

    if (sol.start_training_date) {
      setTrainStartDate(new Date(sol.start_training_date));
    }
    if (sol.end_training_date) {
      setTrainEndDate(new Date(sol.end_training_date));
    }

    // Load model details
    if (sol.model_id) {
      const model = models.find(m => m.id === sol.model_id);
      setSelectedModel(model);
    }

    // Load prediction dates if available (from backend calculation for trained solutions)
    console.log('[SolutionModal] populateSolutionData - solution:', sol);
    console.log('[SolutionModal] populateSolutionData - prediction_dates:', sol.prediction_dates);
    if (sol.prediction_dates) {
      console.log('[SolutionModal] Setting prediction dates from solution.prediction_dates');
      if (sol.prediction_dates.prediction_start_date) {
        setPredictStartDate(new Date(sol.prediction_dates.prediction_start_date));
        console.log('[SolutionModal] Set predictStartDate:', sol.prediction_dates.prediction_start_date);
      }
      if (sol.prediction_dates.prediction_end_date) {
        setPredictEndDate(new Date(sol.prediction_dates.prediction_end_date));
        console.log('[SolutionModal] Set predictEndDate:', sol.prediction_dates.prediction_end_date);
      }
      // Store model info for prediction tab
      setPredictionModelInfo({
        output_chunk_length: sol.prediction_dates.output_chunk_length,
        training_end_date: sol.prediction_dates.training_end_date || sol.end_training_date
      });
    } else if (sol.end_training_date) {
      // Fallback: Calculate prediction start date from training end date + 1 business day
      console.log('[SolutionModal] No prediction_dates, calculating from end_training_date:', sol.end_training_date);
      const endTrainingDate = new Date(sol.end_training_date);
      const predictStart = addBusinessDays(endTrainingDate, 1);
      setPredictStartDate(predictStart);
      console.log('[SolutionModal] Calculated predictStartDate:', predictStart);

      // Default prediction end date to prediction start + 10 business days (default output_chunk_length)
      const predictEnd = addBusinessDays(predictStart, 10);
      setPredictEndDate(predictEnd);
      console.log('[SolutionModal] Calculated predictEndDate:', predictEnd);

      // Store model info with default output_chunk_length
      setPredictionModelInfo({
        output_chunk_length: 10, // default
        training_end_date: sol.end_training_date
      });
    }

    // Restore persisted training result (metrics + chart data)
    if (sol.training_result && typeof sol.training_result === 'object') {
      console.log('[SolutionModal] Restoring persisted training result');
      setTrainingResult(sol.training_result);
      processTrainingResults(sol.training_result);
    }

    // Restore persisted prediction result (same builder as the Predict button).
    if (sol.prediction_result && typeof sol.prediction_result === 'object') {
      console.log('[SolutionModal] Restoring persisted prediction result');
      setPredictionResult(sol.prediction_result);
      const chartData = buildPredictionChartData(sol.prediction_result);
      if (chartData.length > 0) {
        setPredictionChartData(chartData);
      }
    }
  };

  const resetForm = () => {
    setSolutionName('');
    setTicker('');
    setModelId('');
    setTarget('close');
    setIndicators(null);
    setTrainStartDate(new Date());
    setTrainEndDate(new Date());
    setValidation(true);
    setTrainRatio(0.8);
    setPredictStartDate(new Date());
    setPredictEndDate(new Date());
    setTrainingResult(null);
    setTrainingSuggestions([]);
    setPredictionResult(null);
    setIndicatorChartData([]);
    setPredictionChartData([]);
    setPredictionModelInfo(null);
    setError(null);
    setSuccess(null);
  };

  const handleModelChange = (e) => {
    const selectedModelId = parseInt(e.target.value);
    setModelId(selectedModelId);
    const model = models.find(m => m.id === selectedModelId);
    setSelectedModel(model);
  };

  const handleIndicatorsChange = (indicatorData) => {
    setIndicators(indicatorData);
  };

  const handleSaveGeneral = async () => {
    try {
      setLoading(true);
      setError(null);

      const data = {
        solution_name: solutionName,
        ticker: ticker,
        model_id: parseInt(modelId),
        target: target,
        status: 1,
        created_by: 0,
        created_date: new Date().toISOString().replace('T', ' ').substring(0, 19)
      };

      let result;
      if (solution && solution.id) {
        // Update existing solution
        data.id = solution.id;
        data.updated_by = 0;
        data.updated_date = new Date().toISOString().replace('T', ' ').substring(0, 19);
        result = await solutionService.updateSolution(solution.id, data);
      } else {
        // Create new solution
        result = await solutionService.createSolution(data);
      }

      if (result.success) {
        // Save indicators if provided
        if (indicators && result.data && result.data.id) {
          await indicatorService.setSolutionIndicators(result.data.id, indicators);
        }

        setSuccess(t('solutions.save_success'));
        if (onSave) {
          onSave(result.data);
        }
      } else {
        setError(result.error || 'Failed to save solution');
      }
    } catch (err) {
      setError('Failed to save solution: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  // Helper function to merge training predictions with indicator data
  const mergeChartData = (existingData, newData) => {
    if (!existingData || existingData.length === 0) return newData;
    if (!newData || newData.length === 0) return existingData;

    // Create a map of existing data by date for quick lookup
    const existingMap = new Map();
    existingData.forEach(item => {
      if (item.date) existingMap.set(item.date, item);
    });

    // Merge new data with existing, preserving predictions
    const merged = newData.map(newItem => {
      const existing = existingMap.get(newItem.date);
      if (existing) {
        // Merge, prioritizing predictions from existing (training) data
        return {
          ...newItem,
          actual: existing.actual !== undefined && existing.actual !== null ? existing.actual : newItem.actual,
          predicted: existing.predicted !== undefined && existing.predicted !== null ? existing.predicted : newItem.predicted,
          validation: existing.validation !== undefined && existing.validation !== null ? existing.validation : newItem.validation,
        };
      }
      return newItem;
    });

    console.log('✓ Merged chart data:', merged.length, 'points');
    return merged;
  };

  const processTrainingResults = (trainingData) => {
    try {
      console.log('=== PROCESSING TRAINING RESULTS ===');
      console.log('Full training data object:', trainingData);
      console.log('Has predictions field:', !!trainingData?.predictions);
      console.log('Predictions is array:', Array.isArray(trainingData?.predictions));
      console.log('Predictions length:', trainingData?.predictions?.length || 0);

      // Early return if trainingData is null, undefined, or not an object
      if (!trainingData || typeof trainingData !== 'object') {
        console.log('ℹ️ No training result data to process (will load from indicator service)');
        return false; // Return false to indicate no data processed
      }

      console.log('Type:', typeof trainingData);
      console.log('Keys:', Object.keys(trainingData));
      if (trainingData.predictions && trainingData.predictions.length > 0) {
        console.log('✓ First prediction item:', trainingData.predictions[0]);
        console.log('✓ Last prediction item:', trainingData.predictions[trainingData.predictions.length - 1]);
      }

      // Check different possible data structures from training response
      let dataPoints = [];

      // Try to find the actual data points in the response - check all possible paths
      const possiblePaths = [
        trainingData.predictions,
        trainingData.results,
        trainingData.data,
        trainingData.series,
        trainingData.history,
        trainingData.train_data,
        trainingData.training_data,
        Array.isArray(trainingData) ? trainingData : null
      ];

      for (const path of possiblePaths) {
        if (path && Array.isArray(path) && path.length > 0) {
          dataPoints = path;
          console.log('✓ Found data at path, length:', path.length);
          break;
        }
      }

      console.log('Data points found:', dataPoints.length);
      if (dataPoints.length > 0) {
        console.log('First data point structure:', dataPoints[0]);
      }

      if (dataPoints.length > 0) {
        // 🔍 DIAGNOSTIC: Check first data point structure from training
        console.log('🔍 TRAINING DATA - First data point:', JSON.stringify(dataPoints[0], null, 2));
        console.log('🔍 TRAINING DATA - Available fields:', Object.keys(dataPoints[0]));

        // Transform training results into chart data (shared mapper keeps the
        // Training and Prediction tabs visually identical).
        const chartData = dataPoints.map(apiPointToChartPoint);

        console.log('✓ Successfully created chart data:', chartData.length, 'points');
        console.log('Sample chart data point:', chartData[0]);
        console.log('🔍 TRAINING CHART DATA - Field counts:');
        console.log('  - actual:', chartData.filter(d => d.actual !== undefined && d.actual !== null).length);
        console.log('  - predicted:', chartData.filter(d => d.predicted !== undefined && d.predicted !== null).length);
        console.log('  - validation:', chartData.filter(d => d.validation !== undefined && d.validation !== null).length);
        console.log('  - sma_20:', chartData.filter(d => d.sma_20 !== undefined && d.sma_20 !== null).length);
        console.log('  - sma_50:', chartData.filter(d => d.sma_50 !== undefined && d.sma_50 !== null).length);
        console.log('  - ema_12:', chartData.filter(d => d.ema_12 !== undefined && d.ema_12 !== null).length);
        console.log('  - wma:', chartData.filter(d => d.wma !== undefined && d.wma !== null).length);
        console.log('  - macd:', chartData.filter(d => d.macd !== undefined && d.macd !== null).length);
        console.log('  - bb_upper:', chartData.filter(d => d.bb_upper !== undefined && d.bb_upper !== null).length);
        console.log('  - bb_middle:', chartData.filter(d => d.bb_middle !== undefined && d.bb_middle !== null).length);
        console.log('  - bb_lower:', chartData.filter(d => d.bb_lower !== undefined && d.bb_lower !== null).length);
        console.log('  - atr (>0):', chartData.filter(d => d.atr !== undefined && d.atr > 0).length);
        console.log('  - volume (raw):', chartData.filter(d => d.volume !== undefined && d.volume !== null).length);
        console.log('  - volume_sma:', chartData.filter(d => d.volume_sma !== undefined && d.volume_sma !== null).length);
        console.log('  - vwap (price indicator):', chartData.filter(d => d.vwap !== undefined && d.vwap !== null).length);
        console.log('  - obv:', chartData.filter(d => d.obv !== undefined && d.obv !== null).length);
        setIndicatorChartData(chartData);
        setSuccess(`Training completed! Loaded ${chartData.length} data points with predictions and indicators`);
        return true; // Return true to indicate successful processing
      } else {
        console.warn('❌ No data points found in training result');
        console.warn('Will attempt to load data via indicator service...');
        return false; // Return false to indicate no data processed
      }
    } catch (err) {
      console.error('❌ Error processing training results:', err);
      setError('Failed to process training results: ' + err.message);
      return false;
    }
  };

  const handleTrain = async () => {
    if (!solution || !solution.id) {
      setError(t('solutions.save_first_train'));
      return;
    }

    try {
      setLoading(true);
      setError(null);
      setTrainingSuggestions([]);
      setTrainingStatus(t('solutions.training_in_progress'));

      const data = {
        id: solution.id,
        validation: validation,
        train_ratio: trainRatio,
        start_date: trainStartDate.toISOString().split('T')[0],
        end_date: trainEndDate.toISOString().split('T')[0]
      };

      const response = await httpClient.post(API_ENDPOINTS.SOLUTION_TRAIN, data);

      console.log('Training response:', response);

      if (response.success && response.data) {
        // Check if training is async (status: 'training') or has immediate results
        if (response.data.status === 'training') {
          // Training is asynchronous - poll for results
          console.log('Training started asynchronously, polling for results...');
          setTrainingStatus(t('solutions.training_in_progress'));

          // Poll every 3 seconds for training completion
          const pollInterval = setInterval(async () => {
            try {
              const statusResponse = await httpClient.get(
                API_ENDPOINTS.SOLUTION_TRAINING_STATUS(solution.id)
              );

              if (statusResponse.success && statusResponse.data) {
                if (statusResponse.data.status === 'completed') {
                  clearInterval(pollInterval);
                  // FIXED: Access 'result' (singular) not 'results' (plural) from backend
                  const trainingResult = statusResponse.data.result;
                  setTrainingResult(trainingResult);
                  setTrainingStatus(t('solutions.training_complete'));
                  setSuccess('Training completed with RMSE: ' + (trainingResult?.rmse || 'N/A'));

                  console.log('📦 Training result received from backend:', trainingResult);
                  console.log('📊 Predictions count:', trainingResult?.predictions?.length || 0);

                  // Process training results for chart display
                  const hasPredictions = processTrainingResults(trainingResult);

                  // FIXED: Only load indicator data separately if training didn't provide complete data
                  // If training result includes predictions, it already has all indicators merged in
                  if (!hasPredictions) {
                    console.log('⚠️ Training result incomplete, loading indicators separately...');
                    await loadIndicatorChartData(false);
                  } else {
                    console.log('✅ Training result complete with predictions and indicators, skipping separate indicator load');
                  }

                  // Auto-fill prediction dates from training result
                  console.log('[SolutionModal] Training result prediction_dates:', trainingResult?.prediction_dates);
                  if (trainingResult?.prediction_dates) {
                    console.log('[SolutionModal] Auto-filling prediction dates from training result');
                    if (trainingResult.prediction_dates.prediction_start_date) {
                      setPredictStartDate(new Date(trainingResult.prediction_dates.prediction_start_date));
                      console.log('[SolutionModal] Set predictStartDate:', trainingResult.prediction_dates.prediction_start_date);
                    }
                    if (trainingResult.prediction_dates.prediction_end_date) {
                      setPredictEndDate(new Date(trainingResult.prediction_dates.prediction_end_date));
                      console.log('[SolutionModal] Set predictEndDate:', trainingResult.prediction_dates.prediction_end_date);
                    }
                    // Store model info for prediction tab
                    setPredictionModelInfo({
                      output_chunk_length: trainingResult.prediction_dates.output_chunk_length,
                      training_end_date: trainingResult.prediction_dates.training_end_date
                    });
                  }

                  setLoading(false);
                } else if (statusResponse.data.status === 'failed') {
                  clearInterval(pollInterval);
                  setError(statusResponse.data.error || 'Training failed');
                  setTrainingStatus('Training failed');
                  setLoading(false);
                }
                // If status is still 'training', continue polling
              }
            } catch (pollError) {
              clearInterval(pollInterval);
              setError('Error checking training status: ' + pollError.message);
              setLoading(false);
            }
          }, 3000); // Poll every 3 seconds

          // Set timeout after 10 minutes
          setTimeout(() => {
            clearInterval(pollInterval);
            if (loading) {
              setError('Training timeout - please check backend logs');
              setTrainingStatus(t('solutions.training_timeout'));
              setLoading(false);
            }
          }, 600000); // 10 minutes

        } else if (response.data.rmse !== undefined) {
          // Training completed immediately (synchronous)
          setTrainingResult(response.data);
          setTrainingStatus('Training completed successfully!');
          setSuccess('Training completed with RMSE: ' + (response.data.rmse || 'N/A'));

          // Process training results for chart display
          const hasPredictions = processTrainingResults(response.data);

          // Also try to load indicator data, preserving predictions if they exist
          await loadIndicatorChartData(hasPredictions);

          // Auto-fill prediction dates from training result (synchronous case)
          console.log('[SolutionModal] Sync training result prediction_dates:', response.data?.prediction_dates);
          if (response.data?.prediction_dates) {
            console.log('[SolutionModal] Auto-filling prediction dates from sync training result');
            if (response.data.prediction_dates.prediction_start_date) {
              setPredictStartDate(new Date(response.data.prediction_dates.prediction_start_date));
              console.log('[SolutionModal] Set predictStartDate:', response.data.prediction_dates.prediction_start_date);
            }
            if (response.data.prediction_dates.prediction_end_date) {
              setPredictEndDate(new Date(response.data.prediction_dates.prediction_end_date));
              console.log('[SolutionModal] Set predictEndDate:', response.data.prediction_dates.prediction_end_date);
            }
            // Store model info for prediction tab
            setPredictionModelInfo({
              output_chunk_length: response.data.prediction_dates.output_chunk_length,
              training_end_date: response.data.prediction_dates.training_end_date
            });
          }

          setLoading(false);
        } else {
          // Unknown response format
          console.warn('Unexpected training response format:', response.data);
          setError('Unexpected response from training service');
          setLoading(false);
        }
      } else {
        // Check if response contains suggestions
        if (response.data && response.data.suggestions && response.data.suggestions.length > 0) {
          setTrainingSuggestions(response.data.suggestions);
          setError(response.data.error || response.error?.message || 'Training failed');
        } else {
          throw new Error(response.error?.message || 'Training failed');
        }
        setTrainingStatus('Training failed');
        setLoading(false);
      }
    } catch (err) {
      setError('Training failed: ' + err.message);
      setTrainingStatus('Training failed');
      setLoading(false);
    }
  };

  const loadHistoricalPriceData = async () => {
    if (!ticker || !trainStartDate || !trainEndDate) {
      const msg = `Cannot load price data: ticker=${ticker}, startDate=${trainStartDate}, endDate=${trainEndDate}`;
      console.log(msg);
      setError(msg);
      return;
    }

    try {
      console.log('=== LOADING HISTORICAL PRICE DATA ===');
      const startDateStr = trainStartDate.toISOString().split('T')[0];
      const endDateStr = trainEndDate.toISOString().split('T')[0];
      const url = API_ENDPOINTS.COMPANY_HISTORICAL_DATA(ticker, startDateStr, endDateStr);
      console.log('Fetching from:', url);

      const response = await httpClient.get(url);
      console.log('Historical data response:', response);
      console.log('Response type:', typeof response);
      console.log('Response success:', response?.success);

      // Check for API errors first (404, 500, network errors, etc.)
      if (!response.success) {
        const errorStatus = response.error?.status || 'unknown';
        const errorMessage = response.error?.message || response.error?.data?.message || response.error?.data?.detail || 'Unknown error';

        console.error('❌ Backend API error:', {
          status: errorStatus,
          message: errorMessage,
          fullError: response.error
        });

        // Provide helpful error messages based on status
        let userMessage = '';
        if (errorStatus === 404) {
          userMessage = `Backend endpoint not found (404). The API endpoint '${url}' does not exist. Please check your backend URL configuration.`;
        } else if (errorStatus === 500) {
          userMessage = `Backend server error (500). ${errorMessage}. Check backend logs for details.`;
        } else if (errorStatus === 'unknown status' || errorMessage.includes('Network error')) {
          userMessage = `Network error: Cannot connect to backend at ${url}. Is the backend server running?`;
        } else {
          userMessage = `Backend error (${errorStatus}): ${errorMessage}`;
        }

        setError(userMessage);
        console.error('Full error details:', response.error);
        return;
      }

      console.log('Response data type:', typeof response?.data);
      console.log('Response data is array:', Array.isArray(response?.data));
      console.log('Response data length:', response?.data?.length);

      if (response.data && Array.isArray(response.data) && response.data.length > 0) {
        console.log('First data item:', response.data[0]);

        const chartData = response.data.map((item, index, array) => {
          const prevClose = index > 0 ? array[index - 1].close : item.close;
          const volumeColor = item.close >= prevClose ? '#26a69a' : '#ef5350';

          return {
            date: item.tradingdate || item.date,
            actual: item.close,
            close: item.close,
            open: item.open,
            high: item.high,
            low: item.low,
            volume: item.volume,
            volumeColor: volumeColor,

            // These will be empty but structure is ready
            predicted: null,
            validation: null,
            sma_20: null,
            sma_50: null,
            ema_12: null,
            rsi: null,
            macd: null,
            macd_signal: null,
            macd_histogram: null
          };
        });

        console.log('✓ Successfully loaded historical price data:', chartData.length, 'points');
        console.log('Sample chart data:', chartData.slice(0, 3));
        setIndicatorChartData(chartData);
        setSuccess(`✓ Loaded ${chartData.length} historical price points for visualization`);
      } else {
        const errMsg = `Invalid data format from backend: expected array of stock data, got ${typeof response?.data}`;
        console.warn(errMsg);
        setError(errMsg);
      }
    } catch (err) {
      const errMsg = `❌ Error loading historical price data: ${err.message}`;
      console.error(errMsg, err);
      setError(errMsg);
    }
  };

  const loadIndicatorChartData = async (preservePredictions = false) => {
    if (!solution || !solution.id) {
      console.log('Cannot load indicator data: solution not available');
      // Fallback to historical price data
      await loadHistoricalPriceData();
      return;
    }

    try {
      // Store current chart data if we need to preserve predictions
      const currentChartData = preservePredictions ? [...indicatorChartData] : [];

      const data = {
        solution_id: solution.id,
        symbol: ticker,
        start_date: trainStartDate.toISOString().split('T')[0],
        end_date: trainEndDate.toISOString().split('T')[0]
      };

      console.log('=== LOADING INDICATOR CHART DATA ===');
      console.log('Params:', data);
      console.log('Preserve predictions:', preservePredictions);

      const response = await indicatorService.calculateSolutionIndicators(solution.id, data);

      console.log('Indicator service RAW response:', response);
      console.log('Response type:', typeof response);
      console.log('Response keys:', Object.keys(response || {}));
      console.log('Has success field:', 'success' in (response || {}));
      console.log('Has data field:', 'data' in (response || {}));
      console.log('Is response an array:', Array.isArray(response));

      // Try multiple response formats
      let indicatorData = null;

      // Format 1: {success: true, data: [...]}
      if (response && response.success && response.data && Array.isArray(response.data)) {
        indicatorData = response.data;
        console.log('✓ Found data in response.data (format 1)');
      }
      // Format 2: Direct array
      else if (Array.isArray(response)) {
        indicatorData = response;
        console.log('✓ Response is direct array (format 2)');
      }
      // Format 3: {data: [...]} without success field
      else if (response && response.data && Array.isArray(response.data)) {
        indicatorData = response.data;
        console.log('✓ Found data in response.data without success field (format 3)');
      }
      // Format 4: Response has results field
      else if (response && response.results && Array.isArray(response.results)) {
        indicatorData = response.results;
        console.log('✓ Found data in response.results (format 4)');
      }
      // Format 5: Nested object structure {trend: {...}, momentum: {...}, volatility: {...}, volume: {...}}
      else if (response && typeof response === 'object' && !Array.isArray(response)) {
        console.log('✓ Response is nested object structure (format 5) - attempting to transform');

        // Check if response has category keys
        const hasCategories = ['trend', 'momentum', 'volatility', 'volume'].some(key => key in response);

        if (hasCategories) {
          console.log('Detected indicator categories in response');

          // Try to extract arrays from each category and merge them
          const allDataArrays = [];

          for (const [category, categoryData] of Object.entries(response)) {
            console.log(`Processing category: ${category}`, typeof categoryData);

            // Each category might have a 'data' or 'values' array
            if (categoryData && typeof categoryData === 'object') {
              if (Array.isArray(categoryData.data)) {
                allDataArrays.push({ category, data: categoryData.data });
              } else if (Array.isArray(categoryData.values)) {
                allDataArrays.push({ category, data: categoryData.values });
              } else if (Array.isArray(categoryData)) {
                allDataArrays.push({ category, data: categoryData });
              }
            }
          }

          if (allDataArrays.length > 0) {
            // Merge all indicator data by date
            const mergedData = {};

            // Track field normalizations for debugging
            let normalizedFields = new Set();

            allDataArrays.forEach(({ category, data }) => {
              data.forEach(item => {
                const dateKey = item.date || item.tradingdate || item.timestamp;
                if (!mergedData[dateKey]) {
                  mergedData[dateKey] = { date: dateKey };
                }
                // Merge indicator values into the date entry
                Object.assign(mergedData[dateKey], item);

                // ===== FIELD NORMALIZATION =====
                // Backend returns different field names than frontend expects
                // Map backend field names to frontend field names

                // MACD: Backend returns 'signal', frontend expects 'macd_signal'
                if (item.signal !== undefined && mergedData[dateKey].macd_signal === undefined) {
                  mergedData[dateKey].macd_signal = item.signal;
                  normalizedFields.add('signal → macd_signal');
                }

                // MACD: Backend returns 'histogram', ensure it's also available as 'macd_histogram'
                if (item.histogram !== undefined && mergedData[dateKey].macd_histogram === undefined) {
                  mergedData[dateKey].macd_histogram = item.histogram;
                  normalizedFields.add('histogram → macd_histogram');
                }

                // RSI: Backend only returns 'rsi', no signal line exists
                // Calculate RSI signal as 9-period SMA of RSI (optional enhancement)
                // For now, just use null to prevent chart errors
                if (item.rsi !== undefined && mergedData[dateKey].rsi_signal === undefined) {
                  mergedData[dateKey].rsi_signal = null;
                  normalizedFields.add('rsi → rsi_signal (null)');
                }

                // Volume Moving Average: Check for actual volume MA field variations
                // Note: VWAP is a price indicator and OBV is cumulative, keep them separate
                const volumeMaVariants = ['volume_sma', 'vol_sma', 'volume_ma', 'vol_ma', 'sma_volume'];
                const foundVolumeMa = volumeMaVariants.find(field => item[field] !== undefined);
                if (foundVolumeMa && mergedData[dateKey].volume_sma === undefined) {
                  mergedData[dateKey].volume_sma = item[foundVolumeMa];
                  if (foundVolumeMa !== 'volume_sma') {
                    normalizedFields.add(`${foundVolumeMa} → volume_sma`);
                  }
                }
              });
            });

            if (normalizedFields.size > 0) {
              console.log('✓ Field normalizations applied:', Array.from(normalizedFields));
            }

            // Convert merged object to array
            indicatorData = Object.values(mergedData).sort((a, b) =>
              new Date(a.date) - new Date(b.date)
            );

            console.log(`✓ Successfully merged ${allDataArrays.length} indicator categories into ${indicatorData.length} data points`);
            console.log('First merged data item (with field normalization):', indicatorData[0]);
          }
        }
      }

      console.log('Indicator data found:', indicatorData ? indicatorData.length : 0, 'points');

      if (indicatorData && indicatorData.length > 0) {
        console.log('First indicator data item:', indicatorData[0]);
        console.log('🔍 RAW BACKEND DATA - Full first item:', JSON.stringify(indicatorData[0], null, 2));

        // Check if price data exists in indicator response
        const hasPriceData = indicatorData[0].close !== undefined ||
                            indicatorData[0].open !== undefined ||
                            indicatorData[0].high !== undefined ||
                            indicatorData[0].actual_price !== undefined;

        console.log('🔍 Backend has price data:', hasPriceData);

        if (!hasPriceData) {
          console.warn('⚠️ Indicator service returned NO price data - loading historical prices...');

          // Load historical price data first
          try {
            const startDateStr = trainStartDate.toISOString().split('T')[0];
            const endDateStr = trainEndDate.toISOString().split('T')[0];
            const priceUrl = API_ENDPOINTS.COMPANY_HISTORICAL_DATA(ticker, startDateStr, endDateStr);
            console.log('Fetching historical prices from:', priceUrl);

            const priceResponse = await httpClient.get(priceUrl);

            if (priceResponse.success && priceResponse.data && Array.isArray(priceResponse.data)) {
              console.log('✓ Loaded', priceResponse.data.length, 'historical price points');
              console.log('🔍 RAW PRICE DATA - First item:', JSON.stringify(priceResponse.data[0], null, 2));

              // Check ORIGINAL indicator data before merge
              console.log('🔍 ORIGINAL indicator data (first item):', JSON.stringify(indicatorData[0], null, 2));
              console.log('🔍 ALL FIELDS in indicator data:', Object.keys(indicatorData[0] || {}));

              // Check for all selected indicators with different possible field names
              const wmaFieldVariants = ['wma', 'WMA', 'weighted_ma', 'weighted_moving_average'];
              const foundWmaField = wmaFieldVariants.find(field => indicatorData[0]?.[field] !== undefined);
              console.log('🔍 WMA field name found:', foundWmaField || 'NONE');

              const rsiFieldVariants = ['rsi', 'RSI', 'rsi_value', 'relative_strength_index'];
              const foundRsiField = rsiFieldVariants.find(field => indicatorData[0]?.[field] !== undefined);
              console.log('🔍 RSI field name found:', foundRsiField || 'NONE');

              // Check data counts for YOUR selected indicators
              console.log('🔍 Indicator data counts:',{
                wma: indicatorData.filter(d => d.wma !== undefined && d.wma !== null).length,
                macd: indicatorData.filter(d => d.macd !== undefined && d.macd !== null).length,
                atr: indicatorData.filter(d => d.atr !== undefined && d.atr !== null && d.atr > 0).length,
                obv: indicatorData.filter(d => d.obv !== undefined && d.obv !== null).length
              });

              // 🔍 DIAGNOSTIC: Check volume-related fields from backend
              const volumeFields = ['volume', 'volume_sma', 'vol_sma', 'volume_ma', 'vol_ma', 'sma_volume', 'vwap', 'obv'];
              const foundVolumeFields = {};
              volumeFields.forEach(field => {
                const count = indicatorData.filter(d => d[field] !== undefined && d[field] !== null).length;
                if (count > 0) foundVolumeFields[field] = count;
              });
              console.log('🔍 Volume-related fields from backend:', foundVolumeFields);
              if (indicatorData[0]) {
                console.log('🔍 Sample volume data from first point:', {
                  volume: indicatorData[0].volume,
                  volume_sma: indicatorData[0].volume_sma,
                  vol_sma: indicatorData[0].vol_sma,
                  vwap: indicatorData[0].vwap,
                  obv: indicatorData[0].obv
                });
              }

              // Create a map of indicators by date (normalized to date-only format)
              const indicatorMap = new Map();
              indicatorData.forEach(item => {
                // Normalize date: extract just YYYY-MM-DD
                const normalizedDate = item.date ? item.date.split('T')[0] : null;
                if (normalizedDate) {
                  indicatorMap.set(normalizedDate, item);
                }
              });

              console.log('🔍 Indicator map size:', indicatorMap.size);
              console.log('🔍 Sample indicator map key:', Array.from(indicatorMap.keys())[0]);

              // Merge price data with indicators
              indicatorData = priceResponse.data.map(priceItem => {
                const dateValue = priceItem.time || priceItem.tradingdate || priceItem.date;
                // Normalize date for lookup: extract just YYYY-MM-DD
                const normalizedDate = dateValue ? dateValue.split('T')[0] : null;
                const indicators = normalizedDate ? indicatorMap.get(normalizedDate) : {};

                return {
                  ...indicators,
                  date: dateValue,
                  close: priceItem.close,
                  open: priceItem.open,
                  high: priceItem.high,
                  low: priceItem.low,
                  volume: priceItem.volume
                };
              });

              console.log('✓ Merged price data with indicators:', indicatorData.length, 'points');
              console.log('🔍 Sample merged data:', indicatorData[0]);
              console.log('🔍 Merged data has indicators:', {
                hasRSI: indicatorData[0]?.rsi !== undefined,
                hasMACD: indicatorData[0]?.macd !== undefined,
                hasSMA: indicatorData[0]?.sma_20 !== undefined,
                keys: Object.keys(indicatorData[0] || {})
              });

              // Check RSI data specifically
              const rsiDataPoints = indicatorData.filter(d => d.rsi !== undefined && d.rsi !== null && !isNaN(d.rsi));
              console.log('🔍 RSI data points:', rsiDataPoints.length, 'out of', indicatorData.length);
              if (rsiDataPoints.length > 0) {
                console.log('🔍 Sample RSI values:', rsiDataPoints.slice(0, 5).map(d => ({ date: d.date, rsi: d.rsi, rsi_signal: d.rsi_signal })));
              }
            } else {
              console.error('❌ Failed to load historical prices');
              setError('Indicator service returned no price data and historical prices unavailable');
              return;
            }
          } catch (err) {
            console.error('❌ Error loading historical prices:', err);
            setError('Failed to load price data: ' + err.message);
            return;
          }
        }

        // Transform data for professional trading charts
        const chartData = indicatorData.map((item, index, array) => {
          // Calculate volume color based on price change
          const prevClose = index > 0 ? array[index - 1].close : item.close;
          const volumeColor = item.close >= prevClose ? '#26a69a' : '#ef5350';

          // 🔍 DIAGNOSTIC: Log first item to verify all fields
          if (index === 0) {
            console.log('🔍 CHART DATA MAPPING - First item from backend:', JSON.stringify(item, null, 2));
            console.log('🔍 Available fields:', Object.keys(item));
            console.log('🔍 Field values:', {
              close: item.close,
              actual_price: item.actual_price,
              predicted_price: item.predicted_price,
              validation_price: item.validation_price,
              sma_20: item.sma_20,
              sma_50: item.sma_50,
              ema_12: item.ema_12,
              rsi: item.rsi,
              macd: item.macd,
              macd_signal: item.macd_signal,
              atr: item.atr,
              obv: item.obv
            });
          }

          return {
            date: item.date,
            // Price data - consistent field mapping with fallbacks
            close: item.close,
            actual: item.actual_price !== undefined ? item.actual_price : item.close,
            // Training predictions with multiple field name attempts
            predicted: item.predicted_price || item.predicted || item.prediction || item.predict,
            validation: item.validation_price || item.validation || item.val,

            // Technical indicators - organized by category
            // Trend indicators with field name variations
            trend: item.trend_value || item.trend,
            sma_20: item.sma_20 || item.SMA_20 || item.sma20,
            sma_50: item.sma_50 || item.SMA_50 || item.sma50,
            sma_200: item.sma_200 || item.SMA_200 || item.sma200,
            ema_12: item.ema_12 || item.EMA_12 || item.ema12,
            ema_26: item.ema_26 || item.EMA_26 || item.ema26,
            wma: item.wma || item.WMA || item.weighted_ma,

            // Momentum indicators with field name variations
            momentum: item.momentum_value || item.momentum,
            rsi: item.rsi || item.RSI,
            rsi_signal: item.rsi_signal || item.rsi_sig,
            macd: item.macd || item.MACD,
            macd_signal: item.macd_signal || item.signal || item.macd_sig,
            macd_histogram: item.macd_histogram || item.histogram || item.macd_hist,

            // Volatility indicators with field name variations
            volatility: item.volatility_value || item.volatility,
            bb_upper: item.bollinger_upper || item.bb_upper || item.upper_band,
            bb_middle: item.bollinger_middle || item.bb_middle || item.middle_band,
            bb_lower: item.bollinger_lower || item.bb_lower || item.lower_band,
            atr: item.atr || item.ATR,

            // Volume indicators with field name variations
            volume: item.volume_value || item.volume,
            volumeColor: volumeColor,
            volume_sma: item.volume_sma || item.vol_sma || item.volume_ma || item.vol_ma || item.sma_volume,  // Volume Moving Average
            vwap: item.vwap || item.VWAP,  // VWAP (price indicator)
            obv: item.obv || item.OBV  // OBV (cumulative volume indicator)
          };
        });

        console.log('✓ Successfully loaded indicator chart data:', chartData.length, 'points');
        console.log('🔍 DIAGNOSTIC - First 3 chart points:', JSON.stringify(chartData.slice(0, 3), null, 2));
        console.log('🔍 DIAGNOSTIC - Sample actual values:', chartData.slice(0, 5).map(d => ({ date: d.date, actual: d.actual, close: d.close })));

        // Merge with existing predictions if preservePredictions is true
        let finalChartData = chartData;
        if (preservePredictions && currentChartData.length > 0) {
          console.log('🔄 Merging indicator data with existing training predictions...');
          finalChartData = mergeChartData(currentChartData, chartData);
          const predictionCount = finalChartData.filter(d => d.predicted !== undefined && d.predicted !== null).length;
          console.log('✓ Merged data contains', predictionCount, 'predictions');
        }

        // 🔍 FINAL DIAGNOSTIC: Verify all series data
        console.log('🔍 FINAL CHART DATA VERIFICATION:');
        console.log('  - Total points:', finalChartData.length);
        console.log('  - Points with actual:', finalChartData.filter(d => d.actual !== undefined && d.actual !== null).length);
        console.log('  - Points with predicted:', finalChartData.filter(d => d.predicted !== undefined && d.predicted !== null).length);
        console.log('  - Points with validation:', finalChartData.filter(d => d.validation !== undefined && d.validation !== null).length);
        console.log('  - Points with sma_20:', finalChartData.filter(d => d.sma_20 !== undefined && d.sma_20 !== null).length);
        console.log('  - Points with sma_50:', finalChartData.filter(d => d.sma_50 !== undefined && d.sma_50 !== null).length);
        console.log('  - Points with ema_12:', finalChartData.filter(d => d.ema_12 !== undefined && d.ema_12 !== null).length);
        console.log('  - Points with wma:', finalChartData.filter(d => d.wma !== undefined && d.wma !== null).length);
        console.log('  - Points with macd:', finalChartData.filter(d => d.macd !== undefined && d.macd !== null).length);
        console.log('  - Points with bb_upper:', finalChartData.filter(d => d.bb_upper !== undefined && d.bb_upper !== null).length);
        console.log('  - Points with bb_middle:', finalChartData.filter(d => d.bb_middle !== undefined && d.bb_middle !== null).length);
        console.log('  - Points with bb_lower:', finalChartData.filter(d => d.bb_lower !== undefined && d.bb_lower !== null).length);
        console.log('  - Points with atr (>0):', finalChartData.filter(d => d.atr !== undefined && d.atr !== null && d.atr > 0).length);
        console.log('  - Points with volume:', finalChartData.filter(d => d.volume !== undefined && d.volume !== null).length);
        console.log('  - Points with volume_sma:', finalChartData.filter(d => d.volume_sma !== undefined && d.volume_sma !== null).length);
        console.log('  - Points with obv:', finalChartData.filter(d => d.obv !== undefined && d.obv !== null).length);
        console.log('🔍 Sample final data (first 2 points):', JSON.stringify(finalChartData.slice(0, 2), null, 2));

        setIndicatorChartData(finalChartData);
        setSuccess(`Loaded ${finalChartData.length} data points with indicators`);
      } else {
        console.warn('❌ Indicator service returned no data, trying historical price data fallback...');
        await loadHistoricalPriceData();
      }
    } catch (err) {
      console.error('❌ Failed to load indicator chart data:', err);
      console.log('Attempting historical price data fallback...');
      await loadHistoricalPriceData();
    }
  };

  const handleRefreshCharts = async () => {
    setLoading(true);
    setError(null);
    try {
      await loadIndicatorChartData();
    } catch (err) {
      setError('Failed to refresh charts: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const calculateRecommendedDateRange = async (endDate) => {
    if (!modelId || !endDate) return;

    try {
      setCalculatingDates(true);
      setDateRangeRecommendation(null);

      const data = {
        model_id: modelId,
        end_date: endDate.toISOString().split('T')[0],
        validation: validation,
        train_ratio: trainRatio,
        ticker: ticker
      };

      const response = await httpClient.post(
        API_ENDPOINTS.SOLUTION_CALCULATE_DATE_RANGE,
        data
      );

      if (response.success && response.data) {
        setDateRangeRecommendation(response.data);

        // Auto-fill the start date (calculated as end_date - date_offset)
        const recommendedStartDate = new Date(response.data.start_date);
        setTrainStartDate(recommendedStartDate);

        // If end_date was adjusted due to future covariate constraint, also update the UI
        if (response.data.future_covariate_constraint_applied) {
          const adjustedEndDate = new Date(response.data.end_date);
          setTrainEndDate(adjustedEndDate);
          setError(
            `⚠️ End date adjusted for model with future covariates: ` +
            `From ${response.data.original_requested_end_date} to ${response.data.end_date}. ` +
            `This model needs ${response.data.future_covariate_days_needed} days of future data for prediction. ` +
            `Maximum allowed end date is ${response.data.max_end_date}.`
          );
        }
        // Show info message if dates were adjusted
        else if (response.data.adjusted) {
          setSuccess(
            `Date range auto-calculated: ${response.data.required_points} points required, ` +
            `${response.data.recommended_points} recommended. Start date set to ${response.data.start_date}. ` +
            `Prediction will start from ${new Date(new Date(response.data.end_date).getTime() + 86400000).toISOString().split('T')[0]}.`
          );
        }

        // Add info about future covariates if model supports them
        if (response.data.supports_future_covariates && !response.data.future_covariate_constraint_applied) {
          setSuccess(
            (prevMsg) => (prevMsg || '') +
            ` Note: This model uses future covariates. ` +
            `End date should be at least ${response.data.requirements?.output_chunk_length || 10} days before today for accurate predictions.`
          );
        }
      }
    } catch (err) {
      console.error('Failed to calculate date range:', err);
    } finally {
      setCalculatingDates(false);
    }
  };

  const handleTrainEndDateChange = (date) => {
    setTrainEndDate(date);
    // Auto-calculate start date when end date changes
    if (date && modelId) {
      calculateRecommendedDateRange(date);
    }
  };

  const handlePredict = async () => {
    if (!solution || !solution.id) {
      setError(t('solutions.save_first_predict'));
      return;
    }

    try {
      setLoading(true);
      setError(null);

      const data = {
        id: solution.id,
        start_date: predictStartDate.toISOString().split('T')[0],
        end_date: predictEndDate.toISOString().split('T')[0]
      };

      const response = await httpClient.post(API_ENDPOINTS.SOLUTION_PREDICT, data);

      if (response.success && response.data) {
        setPredictionResult(response.data);
        setPredictionChartData(buildPredictionChartData(response.data));
        setSuccess(t('solutions.predict_success'));
      } else {
        throw new Error(response.error?.message || 'Prediction failed');
      }
    } catch (err) {
      setError('Prediction failed: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    resetForm();
    setActiveTab('general');
    onHide();
  };

  const handleOverlayClick = (e) => {
    // Only close if clicking directly on the overlay, not on child elements
    if (e.target === e.currentTarget) {
      handleClose();
    }
  };

  if (!show) return null;

  return (
    <div className="custom-modal-overlay" onClick={handleOverlayClick}>
      <div className="custom-modal-dialog" onClick={(e) => e.stopPropagation()}>
        <div className="custom-modal-content">
          <div className="custom-modal-header">
            <h4 className="custom-modal-title">
              {solution ? t('solutions.modal_title_edit') : t('solutions.modal_title_add')}
            </h4>
            <button
              type="button"
              className="custom-modal-close"
              onClick={handleClose}
              aria-label="Close"
            >
              ×
            </button>
          </div>

          <div className="custom-modal-body">
            {error && <Alert variant="danger" dismissible onClose={() => setError(null)}>{error}</Alert>}
            {success && <Alert variant="success" dismissible onClose={() => setSuccess(null)}>{success}</Alert>}

        {/* Custom Tab Navigation - Replacing react-bootstrap Tabs */}
        <ul className="nav nav-tabs mb-3">
          <li className="nav-item">
            <button
              className={`nav-link ${activeTab === 'general' ? 'active' : ''}`}
              onClick={() => setActiveTab('general')}
              type="button"
            >
              {t('solutions.tab_general')}
            </button>
          </li>
          <li className="nav-item">
            <button
              className={`nav-link ${activeTab === 'training' ? 'active' : ''} ${!solution || !solution.id ? 'disabled' : ''}`}
              onClick={() => solution && solution.id && setActiveTab('training')}
              type="button"
              disabled={!solution || !solution.id}
            >
              {t('solutions.tab_training')}
            </button>
          </li>
          <li className="nav-item">
            <button
              className={`nav-link ${activeTab === 'prediction' ? 'active' : ''} ${!solution || !solution.id ? 'disabled' : ''}`}
              onClick={() => solution && solution.id && setActiveTab('prediction')}
              type="button"
              disabled={!solution || !solution.id}
            >
              {t('solutions.tab_prediction')}
            </button>
          </li>
        </ul>

        {/* Tab Content */}
        <div className="tab-content">
          {/* Tab 1: General Information */}
          {activeTab === 'general' && (
            <div className="tab-pane-content">
            <Form>
              <Row className="mb-3">
                <Col md={6}>
                  <Form.Group>
                    <Form.Label>{t('solutions.sol_name_required')}</Form.Label>
                    <Form.Control
                      type="text"
                      placeholder={t('solutions.sol_name_placeholder')}
                      value={solutionName}
                      onChange={(e) => setSolutionName(e.target.value)}
                      required
                    />
                  </Form.Group>
                </Col>
                <Col md={6}>
                  <Form.Group>
                    <Form.Label>{t('solutions.symbol_label')}</Form.Label>
                    <Form.Select
                      value={ticker}
                      onChange={(e) => setTicker(e.target.value)}
                      required
                    >
                      <option value="">{t('solutions.select_ticker')}</option>
                      {tickers.map((tkr) => (
                        <option key={tkr.ticker} value={tkr.ticker}>
                          {tkr.ticker}
                        </option>
                      ))}
                    </Form.Select>
                  </Form.Group>
                </Col>
              </Row>

              <Row className="mb-3">
                <Col md={6}>
                  <Form.Group>
                    <Form.Label>{t('solutions.model_label_required')}</Form.Label>
                    <Form.Select
                      value={modelId}
                      onChange={handleModelChange}
                      required
                    >
                      <option value="">{t('solutions.select_model')}</option>
                      {models.map((model) => (
                        <option key={model.id} value={model.id}>
                          {model.model_name} - {model.model_type}/{model.model_sub_type}
                        </option>
                      ))}
                    </Form.Select>
                  </Form.Group>
                </Col>
                <Col md={6}>
                  <Form.Group>
                    <Form.Label>{t('solutions.target_required')}</Form.Label>
                    <Form.Select
                      value={target}
                      onChange={(e) => setTarget(e.target.value)}
                      required
                    >
                      <option value="close">{t('solutions.target_close')}</option>
                      <option value="open">{t('solutions.target_open')}</option>
                    </Form.Select>
                  </Form.Group>
                </Col>
              </Row>

              {selectedModel && (
                <Row className="mb-3">
                  <Col>
                    <div className="model-parameters-readonly">
                      <h6>{t('solutions.model_params_title')}</h6>
                      <div className="param-grid">
                        <div><strong>Model Type:</strong> {selectedModel.model_type}</div>
                        <div><strong>Sub-Type:</strong> {selectedModel.model_sub_type}</div>
                        <div><strong>Past Covariate:</strong> {selectedModel.past_covariate ? 'Yes' : 'No'}</div>
                        <div><strong>Future Covariate:</strong> {selectedModel.future_covariate ? 'Yes' : 'No'}</div>
                      </div>
                    </div>
                  </Col>
                </Row>
              )}

              <Row>
                <Col>
                  <h6 className="mt-3 mb-3">{t('solutions.tech_indicators')}</h6>
                  <IndicatorSelector
                    solutionId={solution?.id}
                    onIndicatorsChange={handleIndicatorsChange}
                    modelCovariateConfig={selectedModel ? {
                      hasPastCovariate: Boolean(selectedModel.past_covariate),
                      hasFutureCovariate: Boolean(selectedModel.future_covariate)
                    } : null}
                  />
                  {selectedModel && (
                    <div className="covariate-model-summary mt-2">
                      <small className="text-muted">
                        <strong>{t('solutions.model_covariate_support')}</strong>{' '}
                        {selectedModel.past_covariate && selectedModel.future_covariate && (
                          <span className="badge bg-success me-1">Past + Future + Both</span>
                        )}
                        {selectedModel.past_covariate && !selectedModel.future_covariate && (
                          <span className="badge bg-info me-1">Past Only</span>
                        )}
                        {!selectedModel.past_covariate && selectedModel.future_covariate && (
                          <span className="badge bg-warning me-1">Future Only</span>
                        )}
                        {!selectedModel.past_covariate && !selectedModel.future_covariate && (
                          <span className="badge bg-secondary me-1">No Covariate</span>
                        )}
                      </small>
                    </div>
                  )}
                </Col>
              </Row>

              <div className="d-flex justify-content-end mt-3">
                <Button
                  variant="primary"
                  onClick={handleSaveGeneral}
                  disabled={loading || !solutionName || !ticker || !modelId}
                >
                  {loading ? <><Spinner size="sm" /> {t('solutions.saving_btn')}</> : t('solutions.save_solution_btn')}
                </Button>
              </div>
            </Form>
            </div>
          )}

          {/* Tab 2: Training */}
          {activeTab === 'training' && solution && solution.id && (
            <div className="tab-pane-content">
            <Form>
              {/* Compact Training Configuration */}
              <div className="mb-2">
                <h6 className="text-muted mb-2" style={{fontSize: '0.9rem'}}>{t('solutions.training_config')}</h6>
              </div>

              {/* Compact Form Controls in Single Row */}
              <Row className="mb-2 g-2 align-items-start">
                <Col md={3}>
                  <Form.Group>
                    <Form.Label style={{fontSize: '0.85rem', marginBottom: '2px'}}>{t('solutions.end_date_required')}</Form.Label>
                    <DatePicker
                      selected={trainEndDate}
                      onChange={handleTrainEndDateChange}
                      dateFormat="yyyy-MM-dd"
                      className="form-control form-control-sm"
                      disabled={!modelId}
                    />
                    {!modelId && (
                      <Form.Text style={{fontSize: '0.75rem'}}>
                        {t('solutions.select_model_first')}
                      </Form.Text>
                    )}
                  </Form.Group>
                </Col>
                <Col md={3}>
                  <Form.Group>
                    <Form.Label style={{fontSize: '0.85rem', marginBottom: '2px'}}>
                      Start Date {calculatingDates && <Spinner size="sm" className="ms-1" />}
                    </Form.Label>
                    <DatePicker
                      selected={trainStartDate}
                      onChange={(date) => setTrainStartDate(date)}
                      dateFormat="yyyy-MM-dd"
                      className="form-control form-control-sm"
                      disabled={calculatingDates}
                    />
                    {dateRangeRecommendation && (
                      <Form.Text className="text-success" style={{fontSize: '0.75rem'}}>
                        Auto: {dateRangeRecommendation.estimated_points} days
                      </Form.Text>
                    )}
                  </Form.Group>
                </Col>
                <Col md={2}>
                  <Form.Group>
                    <Form.Label style={{fontSize: '0.85rem', marginBottom: '2px'}}>{t('solutions.train_ratio_label')}</Form.Label>
                    <Form.Control
                      size="sm"
                      type="number"
                      min="0.1"
                      max="0.9"
                      step="0.1"
                      value={trainRatio}
                      onChange={(e) => setTrainRatio(parseFloat(e.target.value))}
                    />
                  </Form.Group>
                </Col>
                <Col md={2}>
                  <Form.Group>
                    <Form.Check
                      type="checkbox"
                      label={<span style={{fontSize: '0.85rem'}}>{t('solutions.enable_validation')}</span>}
                      checked={validation}
                      onChange={(e) => setValidation(e.target.checked)}
                    />
                  </Form.Group>
                </Col>
                <Col md={2}>
                  <Button
                    variant="success"
                    size="sm"
                    onClick={handleTrain}
                    disabled={loading}
                    className="w-100"
                  >
                    {loading ? <><Spinner size="sm" /> {t('solutions.training_btn')}</> : t('solutions.train_btn')}
                  </Button>
                </Col>
              </Row>

              {/* Training Status */}
              {trainingStatus && (
                <Alert variant={trainingStatus.includes('failed') ? 'danger' : trainingStatus.includes('progress') ? 'info' : 'success'} className="py-2 mb-2">
                  <small>{trainingStatus}</small>
                </Alert>
              )}

              {/* RMSE Display */}
              {trainingResult && trainingResult.rmse && (
                <Alert variant="success" className="py-2 mb-2">
                  <small><strong>RMSE:</strong> {typeof trainingResult.rmse === 'number' ? trainingResult.rmse.toFixed(6) : trainingResult.rmse}</small>
                </Alert>
              )}

              {/* Date Range Recommendation */}
              {dateRangeRecommendation && (
                <Alert variant="info" className="mb-2 py-2">
                  <div className="d-flex justify-content-between align-items-start">
                    <div>
                      <strong style={{fontSize: '0.9rem'}}>Date Range Recommendation:</strong>
                      <ul className="mb-0 mt-1" style={{fontSize: '0.85rem'}}>
                        <li>Required: {dateRangeRecommendation.required_points} points</li>
                        <li>Recommended: {dateRangeRecommendation.recommended_points} points</li>
                        <li>Estimated: {dateRangeRecommendation.estimated_points} points</li>
                        {dateRangeRecommendation.requirements && (
                          <>
                            <li>Input chunk: {dateRangeRecommendation.requirements.input_chunk_length}</li>
                            <li>Output chunk: {dateRangeRecommendation.requirements.output_chunk_length}</li>
                          </>
                        )}
                      </ul>
                    </div>
                    <Button
                      variant="link"
                      size="sm"
                      onClick={() => setDateRangeRecommendation(null)}
                      className="text-muted p-0"
                    >
                      ×
                    </Button>
                  </div>
                </Alert>
              )}

              {/* Training Failure Suggestions */}
              {trainingSuggestions.length > 0 && (
                <Alert variant="warning" className="mt-2 py-2">
                  <Alert.Heading style={{fontSize: '0.95rem'}}>Training Failed - Suggested Solutions:</Alert.Heading>
                  <hr className="my-2" />
                  {trainingSuggestions.map((suggestion, index) => (
                    <div key={index} className="mb-2">
                      <h6 className="text-danger" style={{fontSize: '0.9rem'}}>{suggestion.title}</h6>
                      <p className="mb-1" style={{fontSize: '0.85rem'}}><strong>Description:</strong> {suggestion.description}</p>
                      <p className="mb-0 text-muted" style={{fontSize: '0.85rem'}}><strong>Action:</strong> {suggestion.action}</p>
                      {index < trainingSuggestions.length - 1 && <hr className="my-2" />}
                    </div>
                  ))}
                </Alert>
              )}

              {/* Debug Info Panel */}
              {process.env.NODE_ENV === 'development' && (
                <Alert variant="info" className="mt-2 py-2">
                  <div className="d-flex justify-content-between align-items-start">
                    <div>
                      <strong style={{fontSize: '0.85rem'}}>Debug Info:</strong>
                      <ul className="mb-0 mt-1" style={{fontSize: '0.75rem'}}>
                        <li>Chart Data Points: {indicatorChartData.length}</li>
                        <li>Training Result: {trainingResult ? 'Available' : 'Not available'}</li>
                        <li>RMSE: {trainingResult?.rmse || 'N/A'}</li>
                        <li>Ticker: {ticker || 'Not selected'}</li>
                        <li>Check browser console (F12) for detailed logs</li>
                      </ul>
                    </div>
                    <Button
                      variant="outline-primary"
                      size="sm"
                      onClick={handleRefreshCharts}
                      disabled={loading || !ticker}
                    >
                      {loading ? <><Spinner size="sm" /> Refreshing...</> : '🔄 Refresh Charts'}
                    </Button>
                  </div>
                </Alert>
              )}

              {/* Manual Refresh Button for Production */}
              {indicatorChartData.length === 0 && trainingResult && (
                <div className="mt-2 mb-2 text-center">
                  <Button
                    variant="primary"
                    size="sm"
                    onClick={handleRefreshCharts}
                    disabled={loading}
                  >
                    {loading ? <><Spinner size="sm" /> Loading...</> : '📊 Load Chart Data'}
                  </Button>
                  <div className="mt-1">
                    <small className="text-muted">Click to load historical price data for visualization</small>
                  </div>
                </div>
              )}

              {/* Professional Trading Charts - react-financial-charts */}
              <div className="mt-3">
                <div className="card border shadow-sm">
                  <div className="card-header bg-primary text-white py-2">
                    <h6 className="mb-0" style={{fontSize: '0.9rem'}}>📊 Training Results - Professional Trading View</h6>
                  </div>
                  <div className="card-body p-3" style={{backgroundColor: '#f8f9fa'}}>
                    {indicatorChartData.length > 0 ? (
                      <div id="trading-charts-container" style={{minWidth: '1100px', overflow: 'auto'}}>
                        <FinancialTrainingChart data={indicatorChartData} ticker={ticker} />
                      </div>
                    ) : (
                      <div className="d-flex align-items-center justify-content-center text-muted" style={{minHeight: '400px'}}>
                        <div className="text-center" style={{maxWidth: '600px', padding: '20px'}}>
                          <div className="mb-3" style={{fontSize: '3rem', opacity: 0.3}}>📊</div>
                          <small>{t('solutions.pro_chart_hint')}</small>
                          <div className="mt-2" style={{fontSize: '0.75rem', opacity: 0.7}}>
                            Including: Price predictions, Volume analysis, RSI, MACD and more
                          </div>

                          {/* Detailed Debug Information */}
                          <div className="mt-4 p-3" style={{backgroundColor: '#e9ecef', borderRadius: '8px', textAlign: 'left', border: '1px solid #dee2e6'}}>
                            <div style={{color: '#495057', fontSize: '0.8rem', fontFamily: 'monospace'}}>
                              <div><strong>Chart Data Status:</strong></div>
                              <div className="mt-2">• Data points loaded: {indicatorChartData.length}</div>
                              <div>• Training result exists: {trainingResult ? 'Yes' : 'No'}</div>
                              <div>• Ticker selected: {ticker || 'None'}</div>
                              <div>• Solution ID: {solution?.id || 'Not saved'}</div>
                              <div>• Date range: {trainStartDate ? trainStartDate.toISOString().split('T')[0] : 'Not set'} to {trainEndDate ? trainEndDate.toISOString().split('T')[0] : 'Not set'}</div>

                              <div className="mt-3">
                                <strong>Troubleshooting:</strong>
                              </div>
                              <div className="mt-2">
                                {!ticker && <div style={{color: '#ef5350'}}>❌ No ticker selected (Go to General tab)</div>}
                                {!solution?.id && <div style={{color: '#ef5350'}}>❌ Solution not saved (Click "Save Solution")</div>}
                                {ticker && solution?.id && indicatorChartData.length === 0 && (
                                  <div style={{color: '#ffc107'}}>⚠️ Data loaded but empty. Check browser console (F12) for API errors.</div>
                                )}
                              </div>

                              <div className="mt-3">
                                <Button
                                  variant="outline-light"
                                  size="sm"
                                  onClick={() => {
                                    // Generate test data
                                    const testData = [];
                                    const startDate = new Date('2024-01-01');
                                    for (let i = 0; i < 100; i++) {
                                      const date = new Date(startDate);
                                      date.setDate(date.getDate() + i);
                                      const price = 100 + Math.random() * 20;
                                      testData.push({
                                        date: date.toISOString().split('T')[0],
                                        actual: price,
                                        close: price,
                                        predicted: price + (Math.random() - 0.5) * 2,
                                        volume: Math.floor(Math.random() * 1000000),
                                        volumeColor: Math.random() > 0.5 ? '#26a69a' : '#ef5350',
                                        sma_20: price * 0.98,
                                        rsi: 30 + Math.random() * 40,
                                        macd: (Math.random() - 0.5) * 5,
                                        macd_signal: (Math.random() - 0.5) * 4,
                                        macd_histogram: (Math.random() - 0.5) * 2
                                      });
                                    }
                                    setIndicatorChartData(testData);
                                    setSuccess('Test data loaded! Charts should now display.');
                                  }}
                                >
                                  🧪 Load Test Data (Verify Charts Work)
                                </Button>
                              </div>
                            </div>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </Form>
            </div>
          )}

          {/* Tab 3: Prediction */}
          {activeTab === 'prediction' && solution && solution.id && (
            <div className="tab-pane-content">
            <Form>
              {/* Model Info Banner */}
              {predictionModelInfo && predictionModelInfo.training_end_date && (
                <Alert variant="info" className="py-2 mb-3">
                  <small>
                    <strong>{t('solutions.model_ready_prefix')}</strong> Trained until {predictionModelInfo.training_end_date}
                    {predictionModelInfo.output_chunk_length && (
                      <span> | <strong>{t('solutions.max_prediction_prefix')} {predictionModelInfo.output_chunk_length} {t('solutions.days_unit')}</strong> {t('solutions.auto_adjusted')}</span>
                    )}
                  </small>
                </Alert>
              )}

              <Row className="mb-3">
                <Col md={5}>
                  <Form.Group>
                    <Form.Label>{t('solutions.date_start')}</Form.Label>
                    <DatePicker
                      selected={predictStartDate}
                      onChange={(date) => setPredictStartDate(date)}
                      dateFormat="yyyy-MM-dd"
                      className="form-control"
                    />
                  </Form.Group>
                </Col>
                <Col md={5}>
                  <Form.Group>
                    <Form.Label>{t('solutions.date_end')}</Form.Label>
                    <div className="d-flex">
                      <DatePicker
                        selected={predictEndDate}
                        onChange={(date) => setPredictEndDate(date)}
                        dateFormat="yyyy-MM-dd"
                        className="form-control"
                      />
                      {predictionModelInfo && predictionModelInfo.output_chunk_length && (
                        <Button
                          variant="outline-secondary"
                          size="sm"
                          className="ms-2"
                          onClick={setMaxPrediction}
                          title={`Set to max ${predictionModelInfo.output_chunk_length} days`}
                        >
                          Max
                        </Button>
                      )}
                    </div>
                  </Form.Group>
                </Col>
                <Col md={2} className="d-flex align-items-end">
                  <Button
                    variant="primary"
                    onClick={handlePredict}
                    disabled={loading}
                    className="w-100"
                  >
                    {loading ? <><Spinner size="sm" /> {t('solutions.predicting_btn')}</> : t('solutions.predict_btn')}
                  </Button>
                </Col>
              </Row>

              {/* Professional Prediction Chart using react-financial-charts */}
              <div className="mt-4">
                <div className="card border shadow-sm">
                  <div className="card-header bg-success text-white py-2">
                    <h6 className="mb-0" style={{fontSize: '0.9rem'}}>
                      📈 Prediction Results - {ticker || 'Stock'}
                      {predictionChartData.length > 0 && (
                        <span className="ms-2 badge bg-light text-success">
                          {predictionChartData.length} data points
                        </span>
                      )}
                    </h6>
                  </div>
                  <div className="card-body p-3" style={{backgroundColor: '#f8f9fa'}}>
                    {predictionChartData.length > 0 ? (
                      <div style={{minWidth: '1100px', overflow: 'auto'}}>
                        <FinancialPredictionChart data={predictionChartData} ticker={ticker} />
                      </div>
                    ) : (
                      <div className="d-flex align-items-center justify-content-center text-muted" style={{minHeight: '300px'}}>
                        <div className="text-center">
                          <div className="mb-3" style={{fontSize: '3rem', opacity: 0.3}}>📊</div>
                          <p className="mb-2">{t('solutions.no_prediction_yet')}</p>
                          <small>{t('solutions.select_predict_hint')}</small>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </Form>
            </div>
          )}
        </div>
        {/* End of Tab Content */}
          </div>

          <div className="custom-modal-footer">
            <Button variant="secondary" onClick={handleClose}>
              {t('solutions.close_btn')}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SolutionModal;
