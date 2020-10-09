module "sunnyportal_download_project" {
  source = "git::https://github.com/msb/tf-gcp-project.git"

  project_name         = "Sunny Portal"
  additional_apis      = [
    "drive.googleapis.com",
  ]
}
