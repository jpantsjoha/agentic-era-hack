# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

resource "google_storage_bucket" "logs_data_bucket" {
  name                        = "${var.dev_project_id}-logs-data"
  location                    = var.region
  project                     = var.dev_project_id
  uniform_bucket_level_access = true

  lifecycle {
    prevent_destroy = false
    ignore_changes  = all
  }
  depends_on = [resource.google_project_service.services]
}

# Market conditions agent reports bucket for storing analysis reports
resource "google_storage_bucket" "market_conditions_reports_bucket" {
  name                        = "${var.dev_project_id}-market-conditions-reports"
  location                    = var.region
  project                     = var.dev_project_id
  uniform_bucket_level_access = true
  force_destroy               = false  # Set to true only if you want to allow Terraform to delete a non-empty bucket
  
  # Optional: Configure versioning for important data
  versioning {
    enabled = true
  }
  
  # Optional: Configure lifecycle rules for cost optimization
  lifecycle_rule {
    condition {
      age = 90  # Days
    }
    action {
      type = "Delete"  # Or "SetStorageClass" with storage_class = "NEARLINE" or "COLDLINE"
    }
  }
  
  depends_on = [resource.google_project_service.services]
}
