from django.urls import path
from . import (views, view_time_series, views_solution, view_agents, view_authenticate, view_technical_indicators, \
    view_file_upload_manager, view_portfolio, view_recommendations,
    view_stock_screener,
    view_stock_list,
    view_stocks_by_industry, \
    view_fundamental_analysis, view_technical_analysis_advanced, view_ai_insights, view_indicators, view_chatbot_agent, view_simulation)

urlpatterns = [
    path('', views.ApiOverview, name='home'),
    path('companies/groups/<str:group>',views.get_company_by_group),
    path('companies/all/',views.get_all_companies),
    path('companies/industries/<int:industry_id>',views.get_companies_by_industry),
    path('companies/top_gainers/',views.get_top_gainers),
    path('companies/top_losers/',views.get_top_losers),
    path('companies/top_actives/',views.get_top_actives),
    path('companies/industries/',views.get_industries),
    path('company/historical-data/<str:ticker>',views.getAllHistoricalData),
    path('priceboards',views.viewPriceBoardApi),
    path('reports/financial/incomestatements/<str:symbol>',views.viewFinancialReportIncomeStatement),
    path('reports/financial/cashflow/<str:symbol>',views.viewFinancialReportCashFlow),
    path('reports/financial/balancesheet/<str:symbol>',views.viewFinancialReportBalanceSheet),
    path('reports/financial/ratio/<str:symbol>',views.viewFinancialRatio),

    path('market/indexseries/',views.viewMarketIndexSeries),
    path('market/latestindicesseries/',views.viewMarketLatestIndicesSeries),
    path('company/profile/<str:ticker>',views.viewCompanyProfile),
    path('company/overview/<str:ticker>',views.viewCompanyOverview),
    path('company/news/<str:ticker>',views.viewCompanyNews),
    path('company/events/<str:ticker>',views.viewCompanyEvents),
    path('company/dividends/<str:ticker>',views.viewCompanyDividends),
    path('company/historical-data/',views.getCompanyHistoricalData),
    path('company/tickers/',views_solution.get_predict_tickers),
    path('company/technical/macd/',views.getMACD),
    path('company/technical/candlestick/',views.getCandleStick),
    path('company/technical/sma/',views.getSMA),
    path('company/technical/ema/',views.getEMA),
    path('company/technical/volume/',views.getVolume),
    path('company/technical/psar/',views.getPSAR),
    path('company/technical/rsi/',views.getRSI),
    path('predict/getmodels/',views.getPredictModels),

    path('predict/model/parameters/default/',views.getDefaultModelParameters),
    path('predict/model/rnn/',views.RNNModel),
    path('predict/model/blockrnn/',views.BlockRNNModel),
    path('predict/model/catboost/',views.CatBoostModel),
    path('predict/model/dlinear/',views.DLinearModel),
    path('predict/model/lightgbm/',views.LightGBMModel),
    path('predict/model/nbeats/',views.NBeatsModel),
    path('predict/model/nhits/',views.NHitsModel),
    path('predict/model/nlinear/',views.NLinearModel),
    path('predict/model/randomforest/',views.RandomForestModel),
    path('predict/model/tcn/',views.TCNModel),
    path('predict/model/tft/',views.TFTModel),
    path('predict/model/tide/',views.TiDEModel),
    path('predict/model/transformer/',views.TransformerModel),
    path('predict/model/xgboost/',views.XGBoostModel),
    path('predict/model/all/',views.get_models),
    path('predict/models/all/',views.get_models),  # Alternative route for compatibility
    path('predict/model/types/',views.get_model_types),  # New endpoint for model types
    path('predict/model/<int:id>',views.getModelById),
    path('predict/model/params/options/',views.get_options_by_parameter),
    path('predict/model/delete/<str:id>',views.delete_model),
    path('predict/model/parameters/detail/<str:model_type>',views.get_model_parameters_detail),
    path('predict/model/parameters/',views.get_model_parameter_fields),
    path('predict/model/parameters/default-values/',views.getModelsDefaultParamters),
    path('predict/time_series/add/',view_time_series.create_time_series),
    path('predict/time_series/update/',view_time_series.update_time_series),
    path('predict/time_series/delete/<str:id>',view_time_series.delete_series_by_id),
    path('predict/time_series/all/',view_time_series.get_time_series),
    path('predict/time_series/categories/',view_time_series.get_series_categories),
    path('predict/time_series/<str:id>/',view_time_series.get_seriesById),
    path('predict/time_series/covariates/',view_time_series.get_series_by_ids),
    path('predict/time_series/update_batch/',view_time_series.update_series_batch),
    path('predict/solution/tickers/',views_solution.get_predict_tickers),
    path('predict/solution/models/',views_solution.get_predict_models),
    path('predict/solution/all/',views_solution.get_solutions),
    path('predict/solution/covariates/',views_solution.get_predict_covariates),
    path('predict/solution/create/',views_solution.create_predict_solution),
    path('predict/solution/update/',views_solution.update_predict_solution),
    path('predict/solution/<int:id>',views_solution.get_solution_by_id),
    path('predict/solution/delete/<int:id>',views_solution.delete_solution_by_id),
    path('predict/solution/ticker/time_range/<str:ticker>',views_solution.get_ticker_time_range),
    path('predict/solution/calculate-date-range/',views_solution.calculate_date_range),
    path('predict/solution/train/',views_solution.train_solution),
    path('predict/solution/<int:solution_id>/training-status/',views_solution.get_training_status),
    path('predict/solution/predict/',views_solution.predict_solution),
    path('agent/all/',view_agents.getDefaultAgents),
    path('agent/get_agent/',view_agents.run_agent),
    path('agent/get_ml_agent/',view_agents.run_ml_agent),
    path('authenticate/login/',view_authenticate.login),
    path('authenticate/register/',view_authenticate.signup),
    path('authenticate/change-password/',view_authenticate.change_pass),
    path('authenticate/reset-password/',view_authenticate.reset_pass),
    # technica analysis
    path('technical/indicators/<str:group_name>',view_technical_indicators.get_indicator_by_group),
    path('technical/indicator-params',view_technical_indicators.get_indicator_parameters ),
    # fileupload managers
    path('chatbot/file_uploads',view_file_upload_manager.insert_file),

    # Chatbot Agent endpoints - LLM-based intelligent routing
    path('chatbot/ask/', view_chatbot_agent.ask_question),
    path('chatbot/capabilities/', view_chatbot_agent.get_capabilities),
    path('chatbot/categories/', view_chatbot_agent.get_question_categories),
    path('chatbot/feedback/', view_chatbot_agent.provide_feedback),
    path('chatbot/health/', view_chatbot_agent.health_check),

    # portfolio management
    path('portfolio/get/', view_portfolio.get_portfolio),
    path('portfolio/add/', view_portfolio.add_stock),
    path('portfolio/buy/', view_portfolio.buy_stock),
    path('portfolio/sell/', view_portfolio.sell_stock),
    path('portfolio/remove/', view_portfolio.remove_stock),
    path('portfolio/summary/', view_portfolio.get_portfolio_summary),
    path('portfolio/stockoptions/', view_portfolio.get_stock_options),
    path('portfolio/performance/', view_portfolio.get_portfolio_performance),
    path('portfolio/metrics/', view_portfolio.get_portfolio_metrics),

    # stock data sync endpoints
    path('portfolio/sync-status/', view_portfolio.get_sync_status),
    path('portfolio/sync/<str:symbol>/', view_portfolio.trigger_sync),
    path('portfolio/with-sync/', view_portfolio.get_portfolio_with_sync),

    # stock search
    path('search/', view_portfolio.search_stocks),
    
    # price alerts
    path('portfolio/alerts/', view_portfolio.get_user_alerts),
    path('portfolio/alerts/create/', view_portfolio.create_alert),
    path('portfolio/alerts/<int:alert_id>/', view_portfolio.update_alert),
    path('portfolio/alerts/<int:alert_id>/delete/', view_portfolio.delete_alert),
    path('portfolio/alerts/<int:alert_id>/toggle/', view_portfolio.toggle_alert),

    #







    # recommendations
    path('portfolio/recommendations/', view_recommendations.get_recommendations),

    # prospective stocks
    path('portfolio/prospective/', view_portfolio.get_prospective_stocks),

    # Stock Screener endpoints
    path('stocks/screener/', view_stock_screener.screen_stocks),
    path('stocks/screener/criteria/', view_stock_screener.get_screening_criteria),
    path('stocks/screener/advanced/', view_stock_screener.advanced_stock_screen),

    # Stock List endpoints
    path('stocks/list/', view_stock_list.get_all_stocks),
    path('stocks/list/exchange/<str:exchange>/', view_stock_list.get_stocks_by_exchange),
    path('stocks/list/details/<str:symbol>/', view_stock_list.get_stock_details),
    path('stocks/list/multiple/', view_stock_list.get_multiple_stock_details),
    path('stocks/list/search/', view_stock_list.get_stock_search_suggestions),

    # Stocks by Industry endpoints
    path('stocks/industries/', view_stocks_by_industry.get_all_industries),
    path('stocks/industries/<str:industry_code>/', view_stocks_by_industry.get_stocks_by_industry_code),
    path('stocks/industries/<str:industry_code>/analysis/', view_stocks_by_industry.get_industry_analysis),
    path('stocks/industries/<str:industry_code>/performance/', view_stocks_by_industry.get_industry_performance),
    path('stocks/industries/compare/', view_stocks_by_industry.compare_industries),
    
    # Fundamental Analysis endpoints
    path('analysis/fundamental/<str:symbol>/', view_fundamental_analysis.get_fundamental_analysis),
    path('analysis/fundamental/<str:symbol>/statements/', view_fundamental_analysis.get_financial_statements),
    path('analysis/fundamental/compare/', view_fundamental_analysis.compare_fundamental_ratios),
    
    # Technical Analysis endpoints
    path('analysis/technical/<str:symbol>/', view_technical_analysis_advanced.get_technical_analysis),
    path('analysis/technical/<str:symbol>/indicators/', view_technical_analysis_advanced.get_technical_indicators),
    path('analysis/technical/<str:symbol>/intraday/', view_technical_analysis_advanced.get_intraday_analysis),

    # AI Insights endpoints
    path('ai/insights/overview/', view_ai_insights.get_ai_insights_overview),
    path('ai/insights/comprehensive/', view_ai_insights.get_comprehensive_ai_analysis),
    path('ai/insights/patterns/', view_ai_insights.detect_patterns),
    path('ai/insights/sentiment/', view_ai_insights.analyze_sentiment),
    path('ai/insights/risk/', view_ai_insights.assess_risk),
    path('ai/insights/prediction/', view_ai_insights.predict_prices),
    path('ai/insights/indicators/', view_ai_insights.calculate_technical_indicators),
    path('ai/insights/indicators/available/', view_ai_insights.get_available_indicators),
    path('ai/insights/score/', view_ai_insights.get_ai_score),

    # Technical Indicators for Solutions endpoints
    path('predict/indicators/all/', view_indicators.get_all_indicators),
    path('predict/indicators/type/<str:indicator_type>/', view_indicators.get_indicators_by_type),
    path('predict/indicators/<int:indicator_id>/', view_indicators.get_indicator_by_id),
    path('predict/indicators/calculate/', view_indicators.calculate_indicator),
    path('predict/indicators/create/', view_indicators.create_indicator),
    path('predict/indicators/<int:indicator_id>/update/', view_indicators.update_indicator),
    path('predict/indicators/<int:indicator_id>/delete/', view_indicators.delete_indicator),
    path('predict/solution/<int:solution_id>/indicators/', view_indicators.get_solution_indicators),
    path('predict/solution/<int:solution_id>/indicators/add/', view_indicators.add_solution_indicator),
    path('predict/solution/<int:solution_id>/indicators/<int:indicator_id>/', view_indicators.update_solution_indicator),
    path('predict/solution/<int:solution_id>/indicators/<int:indicator_id>/delete/', view_indicators.remove_solution_indicator),
    path('predict/solution/<int:solution_id>/indicators/set/', view_indicators.set_solution_indicators),
    path('predict/solution/<int:solution_id>/indicators/calculate/', view_indicators.calculate_solution_indicators),
    path('predict/solution/<int:solution_id>/indicators/validate/', view_indicators.validate_solution_indicators),
    path('predict/solution/<int:solution_id>/covariate-compatibility/', view_indicators.check_covariate_compatibility),

    # Stock Trading Simulation with AI endpoints
    path('simulation/run/', view_simulation.run_simulation),
    path('simulation/models/', view_simulation.get_available_models),
    path('simulation/template/', view_simulation.get_simulation_template),
    path('simulation/trained-solutions/', view_simulation.get_trained_solutions),

]