provider "aws" {
  region     = "eu-central-1"
  access_key = ""
  secret_key = ""
}

terraform {
  required_providers {
    local = {
      source = "hashicorp/local"
    }
  }
}
