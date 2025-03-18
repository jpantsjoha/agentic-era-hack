# Your Production Google Cloud project id
prod_project_id = "qwiklabs-gcp-00-ec45a6172538"

# Your Staging / Test Google Cloud project id
staging_project_id = "qwiklabs-gcp-02-1747c65b75d3"

# Your Google Cloud project ID that will be used to host the Cloud Build pipelines.
cicd_runner_project_id = "qwiklabs-gcp-00-ec45a6172538"

# Name of the host connection you created in Cloud Build
host_connection_name = "github-connection"

# Name of the repository you added to Cloud Build
repository_name = "agentic-era-hack"

# The Google Cloud region you will use to deploy the infrastructure
region = "us-central1"
cloud_run_app_sa_name = "market-conditions-agent-cr"

telemetry_bigquery_dataset_id = "telemetry_genai_app_sample_sink"
telemetry_sink_name = "telemetry_logs_genai_app_sample"
telemetry_logs_filter = "jsonPayload.attributes.\"traceloop.association.properties.log_type\"=\"tracing\" jsonPayload.resource.attributes.\"service.name\"=\"market-conditions-agent\""

feedback_bigquery_dataset_id = "feedback_genai_app_sample_sink"
feedback_sink_name = "feedback_logs_genai_app_sample"
feedback_logs_filter = "jsonPayload.log_type=\"feedback\""

cicd_runner_sa_name = "cicd-runner"

suffix_bucket_name_load_test_results = "cicd-load-test-results"
repository_owner = "jpantsjoha"
github_app_installation_id = "1765095"
github_pat_secret_id = "github-connection-github-oauthtoken-1a4c27"
connection_exists = true
