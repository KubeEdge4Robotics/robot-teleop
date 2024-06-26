const { defineConfig } = require('@vue/cli-service')
module.exports = defineConfig({
  transpileDependencies: true,
  devServer: {
    proxy: {
      '/v1': {
        target: process.env.VUE_APP_api_url,
        changeOrigin: true
      }
    }
  }
})
