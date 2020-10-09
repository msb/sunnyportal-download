provider "google" {
  credentials = file("/project/service_account_credentials.json")
  project     = "sunny-portal-6d1500"
}
