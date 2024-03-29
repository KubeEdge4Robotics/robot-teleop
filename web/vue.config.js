const { defineConfig } = require('@vue/cli-service')
module.exports = defineConfig({
  transpileDependencies: true,
  devServer: {
    proxy: {
      '/v1': {
        target: 'https://139.159.202.52:8443',
        changeOrigin: true
      }
    }
  }
})
