resource "kubernetes_namespace_v1" "platform_tools" {
  metadata {
    name = "platform-tools"
  }
}

resource "kubernetes_config_map_v1" "app_settings" {
  metadata {
    name      = "app-settings"
    namespace = kubernetes_namespace_v1.platform_tools.metadata[0].name
  }

  data = {
    LOG_LEVEL = "info"
  }
}
