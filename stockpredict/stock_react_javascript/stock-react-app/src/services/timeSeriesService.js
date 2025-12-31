import { API_ENDPOINTS } from '../constants/api';

/**
 * Time Series Service
 * Routes to Prediction Service via /api/v2/predict/time_series
 */
class TimeSeriesService {
  /**
   * Get all time series
   */
  async getAllTimeSeries() {
    const response = await fetch(API_ENDPOINTS.TIME_SERIES_LIST);
    if (!response.ok) {
      throw new Error('Failed to fetch time series');
    }
    return response.json();
  }

  /**
   * Get specific time series details
   */
  async getTimeSeriesById(seriesId) {
    const response = await fetch(API_ENDPOINTS.TIME_SERIES_DETAIL(seriesId));
    if (!response.ok) {
      throw new Error('Failed to fetch time series details');
    }
    return response.json();
  }

  /**
   * Create a new time series
   */
  async createTimeSeries(data) {
    const response = await fetch(API_ENDPOINTS.TIME_SERIES_CREATE, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    });
    if (!response.ok) {
      throw new Error('Failed to create time series');
    }
    return response.json();
  }

  /**
   * Update an existing time series
   */
  async updateTimeSeries(data) {
    const response = await fetch(API_ENDPOINTS.TIME_SERIES_UPDATE(data.id), {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    });
    if (!response.ok) {
      throw new Error('Failed to update time series');
    }
    return response.json();
  }

  /**
   * Delete a time series
   */
  async deleteTimeSeries(seriesId) {
    const response = await fetch(API_ENDPOINTS.TIME_SERIES_DELETE(seriesId), {
      method: 'DELETE',
    });
    if (!response.ok) {
      throw new Error('Failed to delete time series');
    }
    return response.ok;
  }

  /**
   * Get time series by IDs
   */
  async getTimeSeriesByIds(timeSeriesIds) {
    const response = await fetch(API_ENDPOINTS.TIME_SERIES_BY_IDS, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ time_series: timeSeriesIds }),
    });
    if (!response.ok) {
      throw new Error('Failed to fetch time series by IDs');
    }
    return response.json();
  }

  /**
   * Update time series batch
   */
  async updateTimeSeriesBatch(seriesData) {
    const response = await fetch(API_ENDPOINTS.TIME_SERIES_BATCH_UPDATE, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(seriesData),
    });
    if (!response.ok) {
      throw new Error('Failed to update time series batch');
    }
    return response.ok;
  }
}

export default new TimeSeriesService();
