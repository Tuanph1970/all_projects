// CD-3 — Chart Decomposition Service API client
import httpClient from './httpClient';
import { API_ENDPOINTS } from '../constants/api';

class ChartDecompService {

  async modwt({ series, wavelet = 'sym8', level = 6, boundary = 'periodic' }) {
    return httpClient.post(API_ENDPOINTS.CHART_DECOMP_MODWT, { series, wavelet, level, boundary });
  }

  async emd({ series, max_imfs = 0 }) {
    return httpClient.post(API_ENDPOINTS.CHART_DECOMP_EMD, { series, max_imfs });
  }

  async eemd({ series, n_trials = 100, noise_width = 0.2, seed = 42 }) {
    return httpClient.post(API_ENDPOINTS.CHART_DECOMP_EEMD, { series, n_trials, noise_width, seed });
  }

  async vmd({ series, K = 5, alpha = 1500, tol = 1e-7 }) {
    return httpClient.post(API_ENDPOINTS.CHART_DECOMP_VMD, { series, K, alpha, tol });
  }

  async cwt({ series, wavelet = 'cmor1.5-1.0', n_scales = 64, sampling_period = 1.0 }) {
    return httpClient.post(API_ENDPOINTS.CHART_DECOMP_CWT, { series, wavelet, n_scales, sampling_period });
  }

  async hht({ series, n_freq_bins = 120, smoothing_sigma = [1.5, 4.0], max_imfs = 0 }) {
    return httpClient.post(API_ENDPOINTS.CHART_DECOMP_HHT, { series, n_freq_bins, smoothing_sigma, max_imfs });
  }

  async hurst({ series, wavelet = 'db4', j_lo = 2, j_hi = 8 }) {
    return httpClient.post(API_ENDPOINTS.CHART_DECOMP_HURST, { series, wavelet, j_lo, j_hi });
  }

  async coherence({ x, y, wavelet = 'cmor1.5-1.0', n_scales = 64, smoothing_sigma_time = 0.25, smoothing_sigma_scale = 0.6 }) {
    return httpClient.post(API_ENDPOINTS.CHART_DECOMP_COHERENCE, { x, y, wavelet, n_scales, smoothing_sigma_time, smoothing_sigma_scale });
  }

  async harForecast({ log_rv, ridge_alpha = 5.0, min_train = 252, refit_every = 60 }) {
    return httpClient.post(API_ENDPOINTS.CHART_DECOMP_HAR, { log_rv, ridge_alpha, min_train, refit_every });
  }

  async vmdHarForecast({ log_rv, K = 4, alpha = 2000, window = 1000, edge_lag = 5, ridge_alpha = 5.0, min_train = 252, refit_vmd_every = 20, refit_model_every = 60 }) {
    return httpClient.post(API_ENDPOINTS.CHART_DECOMP_VMD_HAR, { log_rv, K, alpha, window, edge_lag, ridge_alpha, min_train, refit_vmd_every, refit_model_every });
  }

  async realizedVol({ returns, n_intraday = null }) {
    return httpClient.post(API_ENDPOINTS.CHART_DECOMP_REALIZED_VOL, { returns, n_intraday });
  }

  async volTargetBacktest({ returns, vol_forecasts, target_ann_vol = 0.15, max_leverage = 3.0, cost_bps = 2.0, lookback_vol = 21 }) {
    return httpClient.post(API_ENDPOINTS.CHART_DECOMP_BACKTEST, { returns, vol_forecasts, target_ann_vol, max_leverage, cost_bps, lookback_vol });
  }

  // ── Part II: pattern detection (CD-617) ──────────────────────────────────

  async patternPipeline({
    series,
    wavelet = 'sym8', level = 4, k_drop = 1, denoise_method = 'drop',
    order = 10, threshold = 0.08, threshold_mode = 'range_frac', min_gap = 8,
    detectors = [],
    compute_fpr = false, n_null = 100, fpr_seed = null,
  }) {
    return httpClient.post(API_ENDPOINTS.CHART_DECOMP_PAT_PIPELINE, {
      series, wavelet, level, k_drop, denoise_method,
      order, threshold, threshold_mode, min_gap,
      detectors, compute_fpr, n_null, fpr_seed,
    });
  }

  async patternNullFPR({ series, detectors = [], n_null = 100, seed = null }) {
    return httpClient.post(API_ENDPOINTS.CHART_DECOMP_PAT_NULL_FPR,
      { series, detectors, n_null, seed });
  }

  async forecastCompare({ log_rv, har = {}, vmd = {} }) {
    return httpClient.post(API_ENDPOINTS.CHART_DECOMP_COMPARE, {
      log_rv,
      har_ridge_alpha:       har.ridge_alpha       ?? 5.0,
      har_min_train:         har.min_train         ?? 252,
      har_refit_every:       har.refit_every       ?? 60,
      vmd_K:                 vmd.K                 ?? 4,
      vmd_alpha:             vmd.alpha             ?? 2000,
      vmd_window:            vmd.window            ?? 1000,
      vmd_edge_lag:          vmd.edge_lag          ?? 5,
      vmd_ridge_alpha:       vmd.ridge_alpha       ?? 5.0,
      vmd_min_train:         vmd.min_train         ?? 252,
      vmd_refit_vmd_every:   vmd.refit_vmd_every   ?? 20,
      vmd_refit_model_every: vmd.refit_model_every ?? 60,
    });
  }
}

const chartDecompService = new ChartDecompService();
export default chartDecompService;
