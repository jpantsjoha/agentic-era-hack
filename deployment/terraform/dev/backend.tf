terraform {
  backend "gcs" {
    bucket = "qwiklabs-gcp-00-ec45a6172538-terraform-state"
    prefix = "dev"
  }
}
