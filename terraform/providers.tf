terraform {
  required_version = ">= 1.6"

  required_providers {
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = ">= 2.30, < 4.0"
    }
  }
}

# Talk to the local kind cluster, using the same settings kubectl uses.
provider "kubernetes" {
  config_path    = "~/.kube/config"
  config_context = "kind-platform-ops"
}
