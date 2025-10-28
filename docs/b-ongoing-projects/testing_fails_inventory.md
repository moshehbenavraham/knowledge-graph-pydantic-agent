# Test Failures Inventory

**Generated**: 2025-10-28 03:29:21
**Test Run Date**: 2025-10-28

---

## Executive Summary

- **Total Tests Collected**: 3858
- **Passed**: 3120 (80.9%)
- **Failed**: 619 (16.0%)
- **Errors**: 19 (0.5%)
- **Skipped**: 100 (2.6%)
- **Warnings**: 419

---

## Analysis Phases

**Total Failures to Analyze**: 619 failures + 19 errors = 638 test issues

### Phase 1: Integration Tests (99 failures) - COMPLETED
**Files**: tests/integration/*
- test_chat_endpoints_comprehensive.py (38)
- test_api_main_comprehensive.py (25)
- test_ui_all_comprehensive.py (17)
- test_rag_tools_comprehensive.py (14)
- test_health_utils_comprehensive.py (3)
- test_additional_coverage.py (1)
- test_web_search_tools_comprehensive.py (1)

**Full analysis moved to**: [testing_fails_phase1_integration.md](./testing_fails_phase1_integration.md)

### Phase 2: UI Tests (83 failures) - COMPLETED
**Files**: tests/ui/*
- test_memory_handler_edge_cases.py (18)
- test_memory_handler_ultra_comprehensive.py (12)
- test_memory_handler.py (11)
- test_streaming_handler.py (10)
- test_streamlit_app_core.py (10)
- test_upload_handler_edge_cases.py (9)
- test_streamlit_app_ultra_comprehensive.py (6)
- test_mcp_handler_comprehensive.py (3)
- test_dashboard_utils_comprehensive.py (1)
- test_streaming_handler_ultra_comprehensive.py (1)
- test_upload_handler_render_section.py (1)
- test_dashboard_handler.py (1)

**Full analysis moved to**: [testing_fails_phase2_ui.md](./testing_fails_phase2_ui.md)

### Phase 3: API Tests (80 failures) - COMPLETED
**Files**: tests/api/*
- test_documents_endpoints_comprehensive.py (21)
- test_chat_endpoints_comprehensive.py (14)
- test_main_comprehensive.py (13)
- test_streaming_comprehensive.py (7)
- test_dependencies_comprehensive.py (5)
- test_endpoints.py (5)
- test_search_endpoints_ultra_comprehensive.py (4)
- test_analytics_endpoints_comprehensive.py (4)
- test_chat_endpoints_ultra_comprehensive.py (4)
- test_documents_endpoints_enhanced.py (1)
- test_streaming_ultra_comprehensive.py (1)
- test_telemetry_comprehensive.py (1)

**Full analysis moved to**: [testing_fails_phase3_api.md](./testing_fails_phase3_api.md)

### Phase 4: Agentic RAG + Storage (77 failures) - COMPLETED
**Files**: tests/agentic_rag/* + tests/storage/*
- test_connection_manager_comprehensive.py (17)
- test_supabase_rest_store.py (23)
- test_pipeline_comprehensive.py (10)
- test_neo4j_store_comprehensive.py (8)
- test_intent_analyzer_comprehensive.py (5)
- test_chunker_comprehensive.py (4)
- test_ranker_comprehensive.py (4)
- test_graphiti_client_edge_cases.py (4)
- test_embedder_ultra_comprehensive.py (1)
- test_graphiti_client_comprehensive.py (1)

**Full analysis moved to**: [testing_fails_phase4_rag_storage.md](./testing_fails_phase4_rag_storage.md)

### Phase 5: Auth + Config (59 failures) - COMPLETED
**Files**: tests/auth/* + tests/config/*
- test_streamlit_auth_ultra_comprehensive.py (16)
- test_config_modules_comprehensive.py (15)
- test_settings_comprehensive.py (8)
- test_user_profile_ultra_comprehensive.py (6)
- test_oauth_analytics_comprehensive.py (4)
- test_email_verification_comprehensive.py (3)
- test_migrate_yaml_to_db_ultra_comprehensive.py (3)
- test_captcha_comprehensive.py (2)
- test_enforce_2fa_comprehensive.py (1)
- test_oauth_profile_comprehensive.py (1)

**Full analysis moved to**: [testing_fails_phase5_auth_config.md](./testing_fails_phase5_auth_config.md)

### Phase 6: Root Level Tests Part 1 (72 failures) - COMPLETED
**Files**: tests/test_*.py (first half)
- test_integration.py (20)
- test_user_profile.py (18)
- test_e2e.py (16)
- test_password_reset.py (16)
- test_config.py (12)

**Full analysis moved to**: [testing_fails_phase6_root_tests_part1.md](./testing_fails_phase6_root_tests_part1.md)

### Phase 7: Root Level Tests Part 2 (70 failures) - COMPLETED
**Files**: tests/test_*.py (second half)
- test_oauth_handler.py (12)
- test_phase2_search.py (9)
- test_hybrid_search_extended.py (6)
- test_memory.py (6)
- test_phase2_ingestion.py (6)
- test_clients.py (5)
- test_migrate_yaml_to_db.py (5)
- test_auth_integration.py (4)
- test_unified_agent.py (3)
- test_db_cli.py (1)
- test_image_analysis.py (1)
- test_main.py (1)
- test_sql_query.py (1)

**Full analysis moved to**: [testing_fails_phase7_root_tests_part2.md](./testing_fails_phase7_root_tests_part2.md)

### Phase 8: Tools + Utils + RAG Pipeline (58 failures) - COMPLETED
**Files**: tests/tools/* + tests/utils/* + tests/rag_pipeline/*
- test_web_search_comprehensive.py (17)
- test_rag_comprehensive.py (11)
- test_db_handler.py (9)
- test_cache_comprehensive.py (7)
- test_text_processor.py (4)
- test_health.py (4)
- test_health_comprehensive.py (3)
- test_code_execution_comprehensive.py (2)
- test_rate_limiting_comprehensive.py (1)

**Full analysis moved to**: [testing_fails_phase8_tools_utils_rag.md](./testing_fails_phase8_tools_utils_rag.md)

### Phase 9: Constitution Validator + Analytics (40 failures + 19 errors) - COMPLETED
**Files**: tests/constitution_validator/* + tests/analytics/*
- test_principles_ultra_comprehensive.py (14 failures)
- test_reporter_comprehensive.py (5 failures + 19 errors)
- test_scanners_ultra_comprehensive.py (1 failure)
- test_analytics_logger.py (1 failure)

**Full analysis moved to**: [testing_fails_phase9_constitution_analytics.md](./testing_fails_phase9_constitution_analytics.md)

---

## Failures by Category

### Agentic Rag (54 failures)

#### tests/agentic_rag/storage/test_connection_manager_comprehensive.py (17 failures)

- `test_check_circuit_breaker_open`
- `test_check_circuit_breaker_open_recovery`
- `test_circuit_breaker_recovery_cycle`
- `test_close_all_connections`
- `test_connection_manager_init_without_config`
- `test_health_check_all_healthy`
- `test_health_check_includes_metrics`
- `test_health_check_neo4j_disabled`
- `test_health_check_neo4j_unhealthy`
- `test_health_check_postgresql_unhealthy`
- `test_health_check_redis_unavailable`
- `test_metrics_accumulation`
- `test_multiple_service_metrics`
- `test_record_failure_below_threshold`
- `test_record_failure_reaches_threshold`
- `test_update_query_metrics_first_query`
- `test_update_query_metrics_postgresql`

#### tests/agentic_rag/ingestion/test_pipeline_comprehensive.py (10 failures)

- `test_ingest_document_empty_content`
- `test_ingest_document_exception_handling`
- `test_ingest_document_no_chunks_created`
- `test_ingest_document_no_metadata`
- `test_ingest_document_success`
- `test_ingest_document_updates_stats`
- `test_ingest_document_with_neo4j`
- `test_pipeline_context_manager`
- `test_pipeline_initialize_already_initialized`
- `test_pipeline_initialize_rest_api_mode`

#### tests/agentic_rag/storage/test_neo4j_store_comprehensive.py (8 failures)

- `test_execute_query_no_parameters`
- `test_find_paths_no_path_exists`
- `test_get_entity_timeline_empty`
- `test_get_graph_statistics_empty_graph`
- `test_search_entities_fuzzy_search`
- `test_search_entities_no_results`
- `test_search_episodes_with_entity_filter`
- `test_search_episodes_with_time_range`

#### tests/agentic_rag/search/test_intent_analyzer_comprehensive.py (5 failures)

- `TestEntityExtraction::test_extract_entities_order_preserved`
- `TestFactIndicatorDetection::test_find_fact_indicators_multiple`
- `TestPatternMatching::test_relationship_keyword_case_insensitive`
- `TestVectorIntentScoring::test_score_vector_intent_default`
- `TestVectorIntentScoring::test_score_vector_intent_reduced_by_temporal`

#### tests/agentic_rag/ingestion/test_chunker_comprehensive.py (4 failures)

- `TestEdgeCases::test_chunk_no_paragraph_breaks`
- `TestSemanticChunkerChunking::test_semantic_chunk_with_metadata`
- `TestSemanticChunkerLLMSplitting::test_llm_split_section_success`
- `TestSemanticChunkerSectionChunking::test_semantic_chunk_sections_single_section`

#### tests/agentic_rag/search/test_ranker_comprehensive.py (4 failures)

- `TestDiversityEnforcement::test_diversity_same_document_penalty`
- `TestFactorScoring::test_similarity_score`
- `TestFeedbackReranking::test_rerank_with_mixed_feedback`
- `TestFeedbackReranking::test_rerank_with_negative_feedback`

#### tests/agentic_rag/storage/test_graphiti_client_edge_cases.py (4 failures)

- `test_calculate_relevance_mixed`
- `test_extract_entities_simple_false_positives`
- `test_extract_relationships_error_handling`
- `test_search_entities_only`

#### tests/agentic_rag/ingestion/test_embedder_ultra_comprehensive.py (1 failures)

- `TestBackwardCompatibility::test_generate_embeddings_with_client`

#### tests/agentic_rag/storage/test_graphiti_client_comprehensive.py (1 failures)

- `TestSearch::test_search_entities_only`

### Analytics (1 failures)

#### tests/analytics/test_analytics_logger.py (1 failures)

- `TestAnalyticsLogger::test_get_stats`

### Api (80 failures)

#### tests/api/endpoints/test_documents_endpoints_comprehensive.py (21 failures)

- `TestDeleteDocument::test_delete_document_failure`
- `TestDeleteDocument::test_delete_document_not_found`
- `TestDeleteDocument::test_delete_document_success`
- `TestDocumentIngestion::test_ingest_document_failure`
- `TestDocumentIngestion::test_ingest_document_success`
- `TestDocumentListing::test_list_documents_empty`
- `TestDocumentListing::test_list_documents_failure`
- `TestDocumentListing::test_list_documents_pagination`
- `TestDocumentListing::test_list_documents_with_data`
- `TestDocumentListing::test_list_documents_with_source_filter`
- `TestDocumentStats::test_get_document_stats_not_found`
- `TestDocumentStats::test_get_document_stats_success`
- `TestGetDocument::test_get_document_failure`
- `TestGetDocument::test_get_document_not_found`
- `TestGetDocument::test_get_document_success`
- `TestGetDocument::test_get_document_with_chunks`
- `TestReindexDocument::test_reindex_document_not_found`
- `TestReindexDocument::test_reindex_document_success`
- `TestUpdateDocument::test_update_document_no_updates`
- `TestUpdateDocument::test_update_document_not_found`
- `TestUpdateDocument::test_update_document_title`

#### tests/api/test_chat_endpoints_comprehensive.py (14 failures)

- `test_chat_empty_message`
- `test_chat_endpoint_cache_hit`
- `test_chat_endpoint_error`
- `test_chat_endpoint_success`
- `test_chat_endpoint_with_parameters`
- `test_chat_endpoint_with_sources`
- `test_chat_metrics_recorded`
- `test_chat_missing_session_id`
- `test_chat_no_usage_in_result`
- `test_chat_result_as_string`
- `test_chat_stream_endpoint_success`
- `test_chat_stream_error`
- `test_chat_stream_with_parameters`
- `test_websocket_chat_message_handler`

#### tests/api/test_main_comprehensive.py (13 failures)

- `test_clear_cache_endpoint_all`
- `test_clear_cache_endpoint_error`
- `test_clear_cache_endpoint_pattern`
- `test_concurrent_requests`
- `test_cors_middleware`
- `test_full_lifecycle`
- `test_openapi_schema`
- `test_request_logging_middleware`
- `test_setup_tracing_runtime_error`
- `test_setup_tracing_with_jaeger`
- `test_setup_tracing_with_otlp`
- `test_status_endpoint`
- `test_status_endpoint_degraded`

#### tests/api/test_streaming_comprehensive.py (7 failures)

- `TestSSEManager::test_stream_agent_response_cancelled`
- `TestSSEManager::test_stream_agent_response_error`
- `TestSSEManager::test_stream_agent_response_success`
- `TestWebSocketManager::test_handle_agent_stream_disconnect`
- `TestWebSocketManager::test_handle_agent_stream_error`
- `TestWebSocketManager::test_handle_agent_stream_success`
- `TestWebSocketManager::test_send_message_error_disconnects`

#### tests/api/test_dependencies_comprehensive.py (5 failures)

- `test_get_api_settings_full_features`
- `test_get_api_settings_minimal`
- `test_get_neo4j_session`
- `test_get_postgres_session`
- `test_session_cleanup_on_exception`

#### tests/api/test_endpoints.py (5 failures)

- `TestChatEndpoints::test_chat_endpoint_validation_error`
- `TestDocumentEndpoints::test_ingest_document_validation_error`
- `TestErrorHandling::test_validation_error`
- `TestHealthChecks::test_health_endpoint`
- `TestSearchEndpoints::test_search_endpoint_validation_error`

#### tests/api/endpoints/test_search_endpoints_ultra_comprehensive.py (4 failures)

- `TestExecuteAdaptiveSearch::test_execute_adaptive_graph_heavy`
- `TestExecuteAdaptiveSearch::test_execute_adaptive_vector_heavy`
- `TestSearchEndpoint::test_search_error_handling`
- `TestSearchEndpoint::test_search_unsupported_type`

#### tests/api/test_analytics_endpoints_comprehensive.py (4 failures)

- `test_analytics_health_degraded_db_issue`
- `test_analytics_health_degraded_missing_tables`
- `test_analytics_health_healthy`
- `test_analytics_health_proper_table_check`

#### tests/api/test_chat_endpoints_ultra_comprehensive.py (4 failures)

- `TestChatEndpoint::test_chat_caches_response`
- `TestChatStreamEndpoint::test_chat_stream_error`
- `TestExtractSourcesHelper::test_extract_sources_content_truncation`
- `TestWebSocketEndpoint::test_websocket_message_handling`

#### tests/api/test_documents_endpoints_enhanced.py (1 failures)

- `TestGetDocument::test_get_document_with_chunks`

#### tests/api/test_streaming_ultra_comprehensive.py (1 failures)

- `TestSSEManagerStreamAgentResponse::test_stream_agent_response_success`

#### tests/api/test_telemetry_comprehensive.py (1 failures)

- `TestOpenTelemetryConfig::test_setup_tracing_console_export`

### Auth (36 failures)

#### tests/auth/test_streamlit_auth_ultra_comprehensive.py (16 failures)

- `TestCheckOAuthCallback::test_check_oauth_callback_google_success`
- `TestCreateDBSession::test_create_db_session_remember_me`
- `TestCreateDBSession::test_create_db_session_success`
- `TestCreateDBSession::test_create_db_session_user_not_found`
- `TestHandleOAuthCallback::test_handle_oauth_callback_error`
- `TestHandleOAuthCallback::test_handle_oauth_callback_new_user`
- `TestHandleOAuthCallback::test_handle_oauth_callback_success`
- `TestInitiateOAuthLogin::test_initiate_oauth_login_error`
- `TestInitiateOAuthLogin::test_initiate_oauth_login_google`
- `TestLoadCredentialsFromDatabase::test_load_credentials_database_error`
- `TestLoadCredentialsFromDatabase::test_load_credentials_skip_inactive_users`
- `TestLoadCredentialsFromDatabase::test_load_credentials_success`
- `TestRenderLogoutButton::test_render_logout_button_clicked`
- `TestRenderLogoutButton::test_render_logout_button_display`
- `TestRenderOAuthButtons::test_render_oauth_buttons_both_enabled`
- `TestRevokeDBSession::test_revoke_db_session_success`

#### tests/auth/test_user_profile_ultra_comprehensive.py (6 failures)

- `TestChangeUserPassword::test_change_user_password_error`
- `TestChangeUserPassword::test_change_user_password_success`
- `TestChangeUserPassword::test_change_user_password_wrong_current_password`
- `TestRenderUserProfile::test_render_user_profile_active_sessions`
- `TestRenderUserProfile::test_render_user_profile_revoke_all_sessions`
- `TestRenderUserProfile::test_render_user_profile_revoke_session`

#### tests/auth/test_oauth_analytics_comprehensive.py (4 failures)

- `TestRenderOAuthAnalyticsDashboard::test_render_dashboard_admin_with_data`
- `TestRenderOAuthAnalyticsDashboard::test_render_dashboard_no_oauth_data`
- `TestRenderOAuthAnalyticsDashboard::test_render_dashboard_not_admin`
- `TestRenderOAuthAnalyticsDashboard::test_render_dashboard_refresh_button`

#### tests/auth/test_email_verification_comprehensive.py (3 failures)

- `TestSendVerificationEmailSMTP::test_send_email_smtp_error`
- `TestSendVerificationEmailSMTP::test_send_email_smtp_no_auth`
- `TestSendVerificationEmailSMTP::test_send_email_smtp_success`

#### tests/auth/test_migrate_yaml_to_db_ultra_comprehensive.py (3 failures)

- `TestMain::test_main_with_backup`
- `TestMigrateUsers::test_migrate_users_skip_existing`
- `TestMigrateUsers::test_migrate_users_success`

#### tests/auth/test_captcha_comprehensive.py (2 failures)

- `TestCaptchaManagerInit::test_init_without_keys_uses_settings`
- `TestCaptchaVerification::test_verify_when_not_configured`

#### tests/auth/test_enforce_2fa_comprehensive.py (1 failures)

- `TestRender2FASetupRequired::test_render_with_secret_in_session`

#### tests/auth/test_oauth_profile_comprehensive.py (1 failures)

- `TestProviderHelpers::test_get_provider_icon_google`

### Config (23 failures)

#### tests/config/test_config_modules_comprehensive.py (15 failures)

- `TestAPIConfig::test_enable_tracing`
- `TestAPIConfig::test_get_cors_config`
- `TestAPIConfig::test_get_uvicorn_config`
- `TestClientsConfig::test_has_neo4j_configured`
- `TestClientsConfig::test_has_supabase_configured`
- `TestClientsConfig::test_llm_provider_config`
- `TestClientsConfig::test_supabase_config`
- `TestUIConfig::test_enable_mcp`
- `TestUIConfig::test_enable_memory`
- `TestUIConfig::test_get_ui_config`
- `TestUIConfig::test_is_advanced_mode`
- `TestUIConfig::test_is_simple_mode`
- `TestUIConfig::test_ui_config_singleton`
- `TestUIConfig::test_ui_mode`
- `TestUIConfig::test_ui_port`

#### tests/config/test_settings_comprehensive.py (8 failures)

- `TestAgentConfig::test_agent_config_llm_settings`
- `TestSettingsEnvironments::test_development_settings`
- `TestSettingsEnvironments::test_production_settings`
- `TestSettingsEnvironments::test_test_settings`
- `TestSettingsReload::test_settings_reload`
- `TestSettingsSecrets::test_api_keys_not_logged`
- `TestSettingsSecrets::test_password_masking`
- `TestSettingsTypes::test_boolean_conversion`

### Constitution Validator (20 failures)

#### tests/constitution_validator/rules/test_principles_ultra_comprehensive.py (14 failures)

- `TestPrincipleIV::test_execute_coverage_check_below_minimum`
- `TestPrincipleIV::test_execute_coverage_check_measurement_failure`
- `TestPrincipleIV::test_execute_coverage_check_success`
- `TestPrincipleIV::test_test_coverage_rule_above_minimum`
- `TestPrincipleIV::test_test_coverage_rule_below_minimum`
- `TestPrincipleVI::test_execute_git_check_anthropic_pattern`
- `TestPrincipleVI::test_execute_git_check_git_error`
- `TestPrincipleVI::test_execute_git_check_no_commits`
- `TestPrincipleVI::test_execute_git_check_skip_merge_commits`
- `TestPrincipleVI::test_execute_git_check_success`
- `TestPrincipleVI::test_git_attribution_rule_clean_commits`
- `TestPrincipleVI::test_git_attribution_rule_detect_claude_attribution`
- `TestPrincipleVI::test_git_attribution_rule_detect_generated_with_claude`
- `TestPrincipleVI::test_git_attribution_rule_skip_merge_commits`

#### tests/constitution_validator/test_reporter_comprehensive.py (5 failures)

- `TestGenerateDetailedTextReport::test_generate_detailed_report_severity_grouping`
- `TestGenerateJSONReport::test_generate_json_report_unicode_safe`
- `TestReportGeneration_EdgeCases::test_report_with_empty_metadata`
- `TestReportGeneration_EdgeCases::test_report_with_special_characters_in_path`
- `TestReportGeneration_EdgeCases::test_report_with_very_long_message`

#### tests/constitution_validator/scanners/test_scanners_ultra_comprehensive.py (1 failures)

- `TestCoverageScanner::test_check_pytest_cov_installed_timeout`

### Integration (99 failures)

#### tests/integration/test_chat_endpoints_comprehensive.py (38 failures)

- `TestCacheBehavior::test_cache_key_includes_strategy`
- `TestCacheBehavior::test_cache_ttl`
- `TestChatEndpoint::test_chat_basic_request`
- `TestChatEndpoint::test_chat_error_handling`
- `TestChatEndpoint::test_chat_with_cache_hit`
- `TestChatEndpoint::test_chat_with_parameters`
- `TestChatEndpoint::test_chat_with_sources`
- `TestChatResponseModel::test_response_confidence_score`
- `TestChatResponseModel::test_response_includes_metrics`
- `TestChatResponseModel::test_response_includes_session_info`
- `TestChatStreamEndpoint::test_chat_stream_basic`
- `TestChatStreamEndpoint::test_chat_stream_error`
- `TestChatStreamEndpoint::test_chat_stream_headers`
- `TestChatStreamEndpoint::test_chat_stream_with_parameters`
- `TestConcurrentRequests::test_multiple_concurrent_chats`
- `TestEndpointRouting::test_chat_endpoint_path`
- `TestEndpointRouting::test_feedback_endpoint_path`
- `TestEndpointRouting::test_stream_endpoint_path`
- `TestErrorScenarios::test_agent_timeout`
- `TestErrorScenarios::test_invalid_parameters`
- `TestFeedbackEndpoint::test_submit_feedback_minimal`
- `TestFeedbackEndpoint::test_submit_feedback_success`
- `TestFeedbackEndpoint::test_submit_feedback_with_issues`
- `TestFeedbackValidation::test_feedback_generates_unique_id`
- `TestFeedbackValidation::test_feedback_rating_range`
- `TestFeedbackValidation::test_feedback_with_comment`
- `TestMetricsCollection::test_metrics_recorded_on_cache_hit`
- `TestMetricsCollection::test_metrics_recorded_on_success`
- `TestRequestValidation::test_empty_message_rejected`
- `TestRequestValidation::test_valid_request_structure`
- `TestResponseTiming::test_timing_metric_recorded`
- `TestSessionHistoryEndpoint::test_get_session_history_basic`
- `TestSessionHistoryEndpoint::test_get_session_history_default_limit`
- `TestSessionHistoryEndpoint::test_get_session_history_with_limit`
- `TestSessionManagement::test_default_session_id`
- `TestStreamingConfiguration::test_stream_agent_params_forwarded`
- `TestWebSocketEndpoint::test_websocket_connection`
- `TestWebSocketEndpoint::test_websocket_endpoint_exists`

#### tests/integration/test_api_main_comprehensive.py (25 failures)

- `TestAppVersion::test_version_in_root`
- `TestAppVersion::test_version_in_status`
- `TestCORSConfiguration::test_cors_headers_on_root`
- `TestCacheClearing::test_cache_flush_called`
- `TestCacheClearing::test_cache_pattern_clearing`
- `TestCacheEndpoint::test_clear_cache_all`
- `TestCacheEndpoint::test_clear_cache_error`
- `TestCacheEndpoint::test_clear_cache_pattern`
- `TestConcurrency::test_concurrent_metrics_requests`
- `TestConcurrency::test_multiple_concurrent_root_requests`
- `TestDocumentation::test_openapi_json`
- `TestDocumentation::test_redoc`
- `TestDocumentation::test_swagger_docs`
- `TestErrorHandling::test_not_found_error_message`
- `TestExceptionHandlers::test_404_error_structure`
- `TestExceptionHandlers::test_404_handler`
- `TestMetricsEndpoint::test_metrics_content_type`
- `TestMetricsEndpoint::test_metrics_endpoint`
- `TestRootEndpoints::test_root_endpoint`
- `TestRootEndpoints::test_root_endpoint_structure`
- `TestStatusComponentDetails::test_status_component_structure`
- `TestStatusComponentDetails::test_status_metrics_included`
- `TestStatusEndpoint::test_status_endpoint_degraded`
- `TestStatusEndpoint::test_status_endpoint_healthy`
- `TestTracingSetup::test_tracing_import_error`

#### tests/integration/test_ui_all_comprehensive.py (17 failures)

- `TestBaseHandler::test_base_handler_init`
- `TestBaseHandler::test_handle_user_input`
- `TestDashboardHandler::test_dashboard_handler_init`
- `TestDashboardHandler::test_fetch_analytics_data`
- `TestDashboardUtils::test_create_chart`
- `TestDashboardUtils::test_create_metric_card`
- `TestErrorHandling::test_handler_error_recovery`
- `TestMCPHandler::test_mcp_handler_init`
- `TestMCPHandler::test_run_with_mcp`
- `TestMemoryHandler::test_memory_handler_init`
- `TestMemoryHandler::test_retrieve_memories`
- `TestStreamingHandler::test_stream_response`
- `TestStreamingHandler::test_streaming_handler_init`
- `TestStreamlitAppInitialization::test_session_state_initialization`
- `TestUIIntegration::test_advanced_mode_workflow`
- `TestUploadHandler::test_handle_file_upload`
- `TestUploadHandler::test_upload_handler_init`

#### tests/integration/test_rag_tools_comprehensive.py (14 failures)

- `TestFormatSearchResults::test_format_results_basic`
- `TestFormatSearchResults::test_format_results_metadata`
- `TestFormatSearchResults::test_format_results_with_entities`
- `TestGetHybridSearch::test_get_hybrid_search_creates_instance`
- `TestGetHybridSearch::test_get_hybrid_search_event_loop_change`
- `TestGetHybridSearch::test_get_hybrid_search_singleton`
- `TestIntentAnalysisIntegration::test_different_intents`
- `TestIntentAnalysisIntegration::test_intent_affects_strategy`
- `TestPerformanceMetrics::test_format_includes_timing`
- `TestResultFormatting::test_format_with_many_entities`
- `TestRetrieveRelevantDocumentsTool::test_retrieve_documents_basic`
- `TestRetrieveRelevantDocumentsTool::test_retrieve_documents_with_strategy`
- `TestSmartSearchTool::test_smart_search_basic`
- `TestSmartSearchTool::test_smart_search_with_limit`

#### tests/integration/test_health_utils_comprehensive.py (3 failures)

- `TestCheckWebSearchHealth::test_web_search_brave_healthy`
- `TestCheckWebSearchHealth::test_web_search_degraded`
- `TestCheckWebSearchHealth::test_web_search_searxng_healthy`

#### tests/integration/test_additional_coverage.py (1 failures)

- `TestConfigImports::test_search_intent_enum`

#### tests/integration/test_web_search_tools_comprehensive.py (1 failures)

- `TestWebSearchTool::test_web_search_fallback_chain`

### Rag Pipeline (13 failures)

#### tests/rag_pipeline/test_db_handler.py (9 failures)

- `TestDbHandler::test_delete_document_by_file_id`
- `TestDbHandler::test_insert_document_chunks`
- `TestDbHandler::test_insert_document_rows`
- `TestDbHandler::test_insert_or_update_document_metadata_insert`
- `TestDbHandler::test_insert_or_update_document_metadata_update`
- `TestDbHandler::test_process_file_for_rag_image_file`
- `TestDbHandler::test_process_file_for_rag_no_chunks`
- `TestDbHandler::test_process_file_for_rag_tabular_file`
- `TestDbHandler::test_process_file_for_rag_text_file`

#### tests/rag_pipeline/test_text_processor.py (4 failures)

- `TestTextProcessor::test_chunk_text`
- `TestTextProcessor::test_create_embeddings`
- `TestTextProcessor::test_extract_text_from_file_pdf`
- `TestTextProcessor::test_extract_text_from_pdf`

### Root Level Tests (142 failures)

#### tests/test_integration.py (20 failures)

- `TestDatabaseOperationsIntegration::test_database_connection_resilience`
- `TestDatabaseOperationsIntegration::test_sql_injection_protection`
- `TestDatabaseOperationsIntegration::test_sql_query_integration`
- `TestEndToEndWorkflows::test_data_analysis_workflow`
- `TestEndToEndWorkflows::test_research_workflow`
- `TestErrorRecoveryIntegration::test_database_failover_scenarios`
- `TestErrorRecoveryIntegration::test_embedding_service_degradation`
- `TestErrorRecoveryIntegration::test_partial_system_failure_recovery`
- `TestErrorRecoveryIntegration::test_timeout_handling_integration`
- `TestPerformanceIntegration::test_concurrent_tool_execution`
- `TestRAGPipelineIntegration::test_document_listing_integration`
- `TestRAGPipelineIntegration::test_rag_document_retrieval_integration`
- `TestRAGPipelineIntegration::test_rag_error_handling`
- `TestRAGPipelineIntegration::test_rag_with_empty_results`
- `TestSecurityIntegration::test_api_key_handling_integration`
- `TestSecurityIntegration::test_data_sanitization_integration`
- `TestSecurityIntegration::test_sql_injection_prevention_integration`
- `TestToolIntegration::test_memory_context_in_rag`
- `TestToolIntegration::test_tool_error_propagation`
- `TestToolIntegration::test_web_search_and_rag_integration`

#### tests/test_user_profile.py (18 failures)

- `test_change_password_with_same_password`
- `test_change_user_password_exception`
- `test_change_user_password_success`
- `test_change_user_password_user_not_found`
- `test_change_user_password_wrong_current`
- `test_complete_password_change_flow`
- `test_get_user_info_exception`
- `test_get_user_info_not_found`
- `test_get_user_info_success`
- `test_get_user_info_with_missing_fields`
- `test_password_change_flow_with_weak_password`
- `test_password_change_flow_with_wrong_current`
- `test_revoke_all_sessions_flow`
- `test_revoke_all_sessions_none_active`
- `test_revoke_session_failure`
- `test_session_list_empty`
- `test_session_revocation_flow`
- `test_session_viewing_flow`

#### tests/test_e2e.py (16 failures)

- `TestCompleteUserWorkflows::test_code_execution_workflow`
- `TestCompleteUserWorkflows::test_document_analysis_workflow`
- `TestCompleteUserWorkflows::test_research_query_workflow`
- `TestCompleteUserWorkflows::test_simple_ui_workflow`
- `TestEdgeCaseWorkflows::test_concurrent_user_sessions_workflow`
- `TestEdgeCaseWorkflows::test_empty_query_workflow`
- `TestEdgeCaseWorkflows::test_large_response_handling_workflow`
- `TestEdgeCaseWorkflows::test_special_characters_workflow`
- `TestEdgeCaseWorkflows::test_very_long_query_workflow`
- `TestErrorHandlingWorkflows::test_database_connection_failure_workflow`
- `TestErrorHandlingWorkflows::test_embedding_service_failure_workflow`
- `TestErrorHandlingWorkflows::test_memory_service_degradation_workflow`
- `TestErrorHandlingWorkflows::test_partial_response_handling`
- `TestErrorHandlingWorkflows::test_timeout_handling_workflow`
- `TestPerformanceWorkflows::test_high_load_workflow`
- `TestStreamlitUIFunctionality::test_resource_caching`

#### tests/test_password_reset.py (16 failures)

- `test_complete_password_reset_flow`
- `test_password_reset_flow_token_reuse`
- `test_password_reset_flow_with_weak_password`
- `test_request_password_reset_by_email`
- `test_request_password_reset_by_username`
- `test_request_password_reset_email_disabled`
- `test_reset_password_with_token_failure`
- `test_reset_password_with_token_success`
- `test_send_reset_email_disabled`
- `test_send_reset_email_smtp_authentication_error`
- `test_send_reset_email_smtp_no_auth`
- `test_send_reset_email_smtp_provider`
- `test_send_reset_email_smtp_success`
- `test_send_reset_email_unsupported_provider`
- `test_validate_reset_token_invalid`
- `test_validate_reset_token_valid`

#### tests/test_config.py (12 failures)

- `TestAPIConfig::test_api_config_properties`
- `TestAPIConfig::test_cors_config`
- `TestAPIConfig::test_uvicorn_config`
- `TestAgentConfig::test_agent_config_properties`
- `TestAgentConfig::test_search_config`
- `TestAgentConfig::test_web_search_config`
- `TestClientsConfig::test_database_config`
- `TestClientsConfig::test_embedding_client_config`
- `TestClientsConfig::test_llm_client_config`
- `TestSettings::test_default_settings_load`
- `TestUIConfig::test_feature_flags`
- `TestUIConfig::test_ui_mode_properties`

#### tests/test_oauth_handler.py (12 failures)

- `test_exchange_code_for_token_failure`
- `test_get_authorization_url_github`
- `test_get_authorization_url_google`
- `test_get_encryption_cipher_no_key`
- `test_get_user_profile_failure`
- `test_handle_callback_existing_user`
- `test_oauth_handler_default_redirect_uri`
- `test_oauth_handler_github_init`
- `test_oauth_handler_google_init`
- `test_oauth_handler_missing_credentials`
- `test_oauth_handler_unsupported_provider`
- `test_refresh_access_token_failure`

#### tests/test_phase2_search.py (9 failures)

- `TestGraphSearch::test_chunk_ref_extraction`
- `TestGraphSearch::test_entity_timeline`
- `TestGraphSearch::test_graph_search_facts`
- `TestHybridSearch::test_parallel_search_execution`
- `TestHybridSearch::test_result_boosting`
- `TestHybridSearch::test_strategy_selection`
- `TestIntegration::test_end_to_end_search_flow`
- `TestVectorSearch::test_similarity_search`
- `TestVectorSearch::test_vector_search_basic`

#### tests/test_hybrid_search_extended.py (6 failures)

- `TestStrategySelection::test_default_intent_with_graph_selects_adaptive`
- `TestStrategySelection::test_entity_focused_intent_selects_hybrid`
- `TestStrategySelection::test_graph_heavy_intent_with_graph_enabled`
- `TestStrategySelection::test_graph_heavy_intent_without_graph_enabled`
- `TestStrategySelection::test_temporal_intent_selects_hybrid`
- `TestStrategySelection::test_vector_heavy_intent_selects_vector_only`

#### tests/test_memory.py (6 failures)

- `TestMemoryClientInitialization::test_async_memory_client_creation`
- `TestMemoryClientInitialization::test_memory_client_with_custom_config`
- `TestMemoryClientInitialization::test_sync_memory_client_creation`
- `TestMemoryErrorHandling::test_invalid_provider_configuration`
- `TestMemoryErrorHandling::test_memory_client_initialization_failure`
- `TestMemoryErrorHandling::test_memory_operation_failures`

#### tests/test_phase2_ingestion.py (6 failures)

- `TestChunker::test_semantic_chunking_fallback`
- `TestChunker::test_simple_chunking`
- `TestEmbedding::test_embedding_generation_with_cache`
- `TestIngestionPipeline::test_pipeline_initialization`
- `TestSearchPerformance::test_caching_improves_performance`
- `TestSearchPerformance::test_vector_search_latency`

#### tests/test_clients.py (5 failures)

- `TestGetLlmClient::test_get_llm_client`
- `TestGetMem0Client::test_get_mem0_client_with_ollama`
- `TestGetMem0Client::test_get_mem0_client_with_openai`
- `TestGetMem0Client::test_get_mem0_client_with_openrouter`
- `TestGetSupabaseClient::test_get_supabase_client`

#### tests/test_migrate_yaml_to_db.py (5 failures)

- `test_complete_migration_flow_with_backup`
- `test_migrate_users_admin_gets_admin_role`
- `test_migrate_users_non_admin_gets_user_role`
- `test_migrate_users_partial_failure`
- `test_migrate_users_success`

#### tests/test_auth_integration.py (4 failures)

- `test_config_with_empty_users`
- `test_load_auth_config_missing_file`
- `test_load_auth_config_success`
- `test_multiple_users_in_config`

#### tests/test_unified_agent.py (3 failures)

- `TestUnifiedAgent::test_iterative_search`
- `TestUnifiedAgent::test_run_unified_agent`
- `TestUnifiedAgent::test_smart_search_tool`

#### tests/test_db_cli.py (1 failures)

- `test_cmd_role_revoke`

#### tests/test_image_analysis.py (1 failures)

- `TestImageAnalysisTool::test_image_analysis_tool_success`

#### tests/test_main.py (1 failures)

- `test_main_function_prints_correct_message`

#### tests/test_sql_query.py (1 failures)

- `TestSqlQueryTool::test_execute_sql_query_tool_success`

### Storage (23 failures)

#### tests/storage/test_supabase_rest_store.py (23 failures)

- `TestComplexScenarios::test_batch_chunk_operations`
- `TestComplexScenarios::test_document_lifecycle`
- `TestDeleteDocument::test_delete_document_exception`
- `TestDeleteDocument::test_delete_document_success`
- `TestEdgeCases::test_store_empty_chunks`
- `TestGetChunks::test_get_chunks_empty`
- `TestGetChunks::test_get_chunks_exception`
- `TestGetChunks::test_get_chunks_success`
- `TestGetDocument::test_get_document_exception`
- `TestGetDocument::test_get_document_found`
- `TestGetDocument::test_get_document_not_found`
- `TestStoreChunks::test_store_chunks_exception`
- `TestStoreChunks::test_store_chunks_no_ids_returned`
- `TestStoreChunks::test_store_chunks_success`
- `TestStoreChunks::test_store_chunks_with_defaults`
- `TestStoreDocument::test_store_document_exception`
- `TestStoreDocument::test_store_document_no_id_returned`
- `TestStoreDocument::test_store_document_no_metadata`
- `TestStoreDocument::test_store_document_success`
- `TestUpdateChunkMetadata::test_update_chunk_metadata_json_string`
- `TestUpdateChunkMetadata::test_update_chunk_metadata_not_found`
- `TestUpdateChunkMetadata::test_update_chunk_metadata_success`
- `TestUpdateChunkMetadata::test_update_chunk_metadata_with_entity_refs`

### Tools (30 failures)

#### tests/tools/test_web_search_comprehensive.py (17 failures)

- `test_brave_web_search_api_parameters`
- `test_brave_web_search_empty_results`
- `test_brave_web_search_limit_three`
- `test_brave_web_search_missing_fields`
- `test_brave_web_search_success`
- `test_jina_web_search_empty_results`
- `test_jina_web_search_error`
- `test_jina_web_search_list_response`
- `test_jina_web_search_truncate_content`
- `test_jina_web_search_unexpected_format`
- `test_jina_web_search_use_description_fallback`
- `test_web_search_auto_select_jina`
- `test_web_search_explicit_brave`
- `test_web_search_explicit_jina`
- `test_web_search_fallback_to_brave`
- `test_web_search_fallback_to_searxng`
- `test_web_search_priority_jina_brave_searxng`

#### tests/tools/test_rag_comprehensive.py (11 failures)

- `test_format_search_results_no_entities`
- `test_format_search_results_with_chunks`
- `test_get_hybrid_search_cached`
- `test_get_hybrid_search_event_loop_change`
- `test_get_hybrid_search_first_call`
- `test_large_result_set_handling`
- `test_retrieve_documents_no_results`
- `test_retrieve_documents_success`
- `test_retrieve_documents_with_strategy`
- `test_smart_search_no_entities_or_facts`
- `test_smart_search_with_intent_analysis`

#### tests/tools/test_code_execution_comprehensive.py (2 failures)

- `TestComplexScenarios::test_class_definition`
- `TestComplexScenarios::test_exception_handling`

### Ui (83 failures)

#### tests/ui/features/test_memory_handler_edge_cases.py (18 failures)

- `TestAddMemoryEdgeCases::test_add_memory_exception_handling`
- `TestAddMemoryEdgeCases::test_add_memory_only_user_input`
- `TestAddMemoryEdgeCases::test_add_memory_with_empty_response`
- `TestAddMemoryEdgeCases::test_add_memory_with_response`
- `TestAddMemoryEdgeCases::test_add_memory_with_unicode_content`
- `TestAddMemoryEdgeCases::test_add_memory_with_very_long_content`
- `TestGetMemoriesEdgeCases::test_get_memories_search_exception`
- `TestGetMemoriesEdgeCases::test_get_memories_with_large_limit`
- `TestGetMemoriesEdgeCases::test_get_memories_with_long_query`
- `TestGetMemoriesEdgeCases::test_get_memories_with_memory_limit_zero`
- `TestGetMemoriesEdgeCases::test_get_memories_with_special_characters`
- `TestGetMemoriesEdgeCases::test_get_memories_with_unicode`
- `TestMemoryHandlerInit::test_init_mem0_client_exception_handling`
- `TestMemoryHandlerInit::test_setup_hook_logging`
- `TestMemoryHandlerIntegration::test_full_conversation_flow`
- `TestRunAgentEdgeCases::test_run_agent_accumulates_response`
- `TestRunAgentEdgeCases::test_run_agent_with_kwargs`
- `TestRunAgentEdgeCases::test_run_agent_with_memories`

#### tests/ui/features/test_memory_handler_ultra_comprehensive.py (12 failures)

- `TestMemoryHandlerHandle::test_handle_with_memory`
- `TestMemoryHandlerHandle::test_handle_without_memory`
- `TestMemoryHandlerInit::test_init_default_memory_limit`
- `TestMemoryHandlerInit::test_init_with_memory_disabled`
- `TestMemoryHandlerInit::test_init_with_memory_enabled`
- `TestMemoryHandlerRetrieve::test_retrieve_memories_disabled`
- `TestMemoryHandlerRetrieve::test_retrieve_memories_empty`
- `TestMemoryHandlerRetrieve::test_retrieve_memories_exception`
- `TestMemoryHandlerRetrieve::test_retrieve_memories_success`
- `TestMemoryHandlerStore::test_store_memory_disabled`
- `TestMemoryHandlerStore::test_store_memory_exception`
- `TestMemoryHandlerStore::test_store_memory_success`

#### tests/ui/features/test_memory_handler.py (11 failures)

- `test_add_memory_empty_response`
- `test_add_memory_no_response`
- `test_add_memory_success`
- `test_get_memories_custom_limit`
- `test_get_memories_long_query`
- `test_get_memories_success`
- `test_memory_handler_init_with_memory_enabled`
- `test_run_agent_accumulates_full_response`
- `test_run_agent_passes_memories_to_parent`
- `test_run_agent_stores_memory`
- `test_run_agent_with_memories`

#### tests/ui/features/test_streaming_handler.py (10 failures)

- `test_streaming_handler_basic_text_stream`
- `test_streaming_handler_ctx_attribute_access`
- `test_streaming_handler_error_with_event_tracking`
- `test_streaming_handler_long_content`
- `test_streaming_handler_multiple_nodes`
- `test_streaming_handler_text_delta_batching`
- `test_streaming_handler_text_delta_logging_frequency`
- `test_streaming_handler_tool_call_event`
- `test_streaming_handler_tool_call_with_complex_args`
- `test_streaming_handler_tool_return_with_content`

#### tests/ui/test_streamlit_app_core.py (10 failures)

- `TestModeSwitching::test_handler_type_matches_mode`
- `TestModeSwitching::test_mode_feature_mapping_consistency`
- `TestUIConfig::test_advanced_mode_features`
- `TestUIConfig::test_get_handler_advanced_mode`
- `TestUIConfig::test_get_handler_simple_mode`
- `TestUIConfig::test_get_handler_standard_mode`
- `TestUIConfig::test_handler_config_includes_memory_limit`
- `TestUIConfig::test_handler_config_includes_user_id`
- `TestUIConfig::test_simple_mode_features`
- `TestUIConfig::test_standard_mode_features`

#### tests/ui/features/test_upload_handler_edge_cases.py (9 failures)

- `test_document_metadata_completeness`
- `test_document_single_byte_file`
- `test_process_document_chunking_error`
- `test_process_document_database_error`
- `test_process_document_embedding_error`
- `test_process_document_empty_file`
- `test_process_document_unicode_content`
- `test_process_document_very_large_file`
- `test_tabular_schema_preservation`

#### tests/ui/test_streamlit_app_ultra_comprehensive.py (6 failures)

- `TestHandleUserInput::test_handle_user_input_simple_mode`
- `TestHandleUserInput::test_handle_user_input_streaming_mode`
- `TestInitializeSessionState::test_initialize_session_state_first_time`
- `TestMain::test_main_chat_page_no_input`
- `TestRenderDashboard::test_render_dashboard_error`
- `TestRenderDashboard::test_render_dashboard_success`

#### tests/ui/features/test_mcp_handler_comprehensive.py (3 failures)

- `TestMCPHandlerErrors::test_run_agent_error_logging`
- `TestMCPHandlerInit::test_init_inherits_from_memory_handler`
- `TestMCPHandlerInit::test_init_with_mcp_enabled`

#### tests/ui/features/test_dashboard_utils_comprehensive.py (1 failures)

- `TestPyvisGraphCreation::test_create_pyvis_graph_circular`

#### tests/ui/features/test_streaming_handler_ultra_comprehensive.py (1 failures)

- `TestStreamingHandler::test_stream_response`

#### tests/ui/features/test_upload_handler_render_section.py (1 failures)

- `test_render_upload_section_file_size_display`

#### tests/ui/test_dashboard_handler.py (1 failures)

- `test_get_performance_metrics_includes_percentiles`

### Utils (15 failures)

#### tests/utils/test_cache_comprehensive.py (7 failures)

- `TestCacheDelete::test_delete_from_fallback_cache`
- `TestCacheExists::test_exists_in_fallback_cache`
- `TestCacheGet::test_get_from_fallback_cache`
- `TestCacheIncr::test_incr_in_fallback_cache`
- `TestCacheIncr::test_incr_new_key_in_fallback`
- `TestCacheSet::test_set_fallback_memory_limit`
- `TestCacheSet::test_set_to_fallback_cache`

#### tests/utils/test_health.py (4 failures)

- `TestWebSearchHealthCheck::test_check_web_search_health_brave_degraded`
- `TestWebSearchHealthCheck::test_check_web_search_health_brave_success`
- `TestWebSearchHealthCheck::test_check_web_search_health_exception`
- `TestWebSearchHealthCheck::test_check_web_search_health_searxng_success`

#### tests/utils/test_health_comprehensive.py (3 failures)

- `TestWebSearchHealthCheck::test_check_web_search_health_brave_healthy`
- `TestWebSearchHealthCheck::test_check_web_search_health_degraded`
- `TestWebSearchHealthCheck::test_check_web_search_health_searxng_healthy`

#### tests/utils/test_rate_limiting_comprehensive.py (1 failures)

- `TestEdgeCases::test_very_short_window`

---

## Test Errors (19 total)

These tests have ERRORS (setup/teardown issues, not failures):

### tests/constitution_validator/test_reporter_comprehensive.py (19 errors)

- `TestGenerateDetailedTextReport::test_generate_detailed_report_basic`
- `TestGenerateDetailedTextReport::test_generate_detailed_report_empty`
- `TestGenerateDetailedTextReport::test_generate_detailed_report_file_paths`
- `TestGenerateDetailedTextReport::test_generate_detailed_report_formatting`
- `TestGenerateDetailedTextReport::test_generate_detailed_report_line_breaks`
- `TestGenerateDetailedTextReport::test_generate_detailed_report_metadata`
- `TestGenerateDetailedTextReport::test_generate_detailed_report_scan_metrics`
- `TestGenerateDetailedTextReport::test_generate_detailed_report_structure`
- `TestGenerateDetailedTextReport::test_generate_detailed_report_violations`
- `TestGenerateJSONReport::test_generate_json_report_basic`
- `TestGenerateJSONReport::test_generate_json_report_empty`
- `TestGenerateJSONReport::test_generate_json_report_pretty_printed`
- `TestGenerateJSONReport::test_generate_json_report_structure`
- `TestGenerateJSONReport::test_generate_json_report_with_file`
- `TestGenerateTextSummary::test_generate_text_summary_basic`
- `TestGenerateTextSummary::test_generate_text_summary_contains_key_info`
- `TestGenerateTextSummary::test_generate_text_summary_not_empty`
- `TestGenerateTextSummary::test_generate_text_summary_passed`
- `TestReportGeneration_EdgeCases::test_json_report_invalid_output_path`

---

## Files with Most Failures (Top 30)

| Rank | File | Failures | % of Total |
|------|------|----------|------------|
| 1 | `tests/integration/test_chat_endpoints_comprehensive.py` | 38 | 6.1% |
| 2 | `tests/integration/test_api_main_comprehensive.py` | 25 | 4.0% |
| 3 | `tests/storage/test_supabase_rest_store.py` | 23 | 3.7% |
| 4 | `tests/api/endpoints/test_documents_endpoints_comprehensive.py` | 21 | 3.4% |
| 5 | `tests/test_integration.py` | 20 | 3.2% |
| 6 | `tests/test_user_profile.py` | 18 | 2.9% |
| 7 | `tests/ui/features/test_memory_handler_edge_cases.py` | 18 | 2.9% |
| 8 | `tests/agentic_rag/storage/test_connection_manager_comprehensive.py` | 17 | 2.7% |
| 9 | `tests/integration/test_ui_all_comprehensive.py` | 17 | 2.7% |
| 10 | `tests/tools/test_web_search_comprehensive.py` | 17 | 2.7% |
| 11 | `tests/auth/test_streamlit_auth_ultra_comprehensive.py` | 16 | 2.6% |
| 12 | `tests/test_e2e.py` | 16 | 2.6% |
| 13 | `tests/test_password_reset.py` | 16 | 2.6% |
| 14 | `tests/config/test_config_modules_comprehensive.py` | 15 | 2.4% |
| 15 | `tests/api/test_chat_endpoints_comprehensive.py` | 14 | 2.3% |
| 16 | `tests/constitution_validator/rules/test_principles_ultra_comprehensive.py` | 14 | 2.3% |
| 17 | `tests/integration/test_rag_tools_comprehensive.py` | 14 | 2.3% |
| 18 | `tests/api/test_main_comprehensive.py` | 13 | 2.1% |
| 19 | `tests/test_config.py` | 12 | 1.9% |
| 20 | `tests/test_oauth_handler.py` | 12 | 1.9% |
| 21 | `tests/ui/features/test_memory_handler_ultra_comprehensive.py` | 12 | 1.9% |
| 22 | `tests/tools/test_rag_comprehensive.py` | 11 | 1.8% |
| 23 | `tests/ui/features/test_memory_handler.py` | 11 | 1.8% |
| 24 | `tests/agentic_rag/ingestion/test_pipeline_comprehensive.py` | 10 | 1.6% |
| 25 | `tests/ui/features/test_streaming_handler.py` | 10 | 1.6% |
| 26 | `tests/ui/test_streamlit_app_core.py` | 10 | 1.6% |
| 27 | `tests/rag_pipeline/test_db_handler.py` | 9 | 1.5% |
| 28 | `tests/test_phase2_search.py` | 9 | 1.5% |
| 29 | `tests/ui/features/test_upload_handler_edge_cases.py` | 9 | 1.5% |
| 30 | `tests/agentic_rag/storage/test_neo4j_store_comprehensive.py` | 8 | 1.3% |

---

## Priority Recommendations

### High Priority (>15 failures per file)

- **tests/integration/test_chat_endpoints_comprehensive.py**: 38 failures
- **tests/integration/test_api_main_comprehensive.py**: 25 failures
- **tests/storage/test_supabase_rest_store.py**: 23 failures
- **tests/api/endpoints/test_documents_endpoints_comprehensive.py**: 21 failures
- **tests/test_integration.py**: 20 failures
- **tests/test_user_profile.py**: 18 failures
- **tests/ui/features/test_memory_handler_edge_cases.py**: 18 failures
- **tests/agentic_rag/storage/test_connection_manager_comprehensive.py**: 17 failures
- **tests/integration/test_ui_all_comprehensive.py**: 17 failures
- **tests/tools/test_web_search_comprehensive.py**: 17 failures
- **tests/auth/test_streamlit_auth_ultra_comprehensive.py**: 16 failures
- **tests/test_e2e.py**: 16 failures
- **tests/test_password_reset.py**: 16 failures

### Medium Priority (10-15 failures per file)

- **tests/config/test_config_modules_comprehensive.py**: 15 failures
- **tests/api/test_chat_endpoints_comprehensive.py**: 14 failures
- **tests/constitution_validator/rules/test_principles_ultra_comprehensive.py**: 14 failures
- **tests/integration/test_rag_tools_comprehensive.py**: 14 failures
- **tests/api/test_main_comprehensive.py**: 13 failures
- **tests/test_config.py**: 12 failures
- **tests/test_oauth_handler.py**: 12 failures
- **tests/ui/features/test_memory_handler_ultra_comprehensive.py**: 12 failures
- **tests/tools/test_rag_comprehensive.py**: 11 failures
- **tests/ui/features/test_memory_handler.py**: 11 failures
- **tests/agentic_rag/ingestion/test_pipeline_comprehensive.py**: 10 failures
- **tests/ui/features/test_streaming_handler.py**: 10 failures
- **tests/ui/test_streamlit_app_core.py**: 10 failures

### Quick Wins (1-3 failures per file)

**28 files** with 1-3 failures each - These are good candidates for quick fixes.
