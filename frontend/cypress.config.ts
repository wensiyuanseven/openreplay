// Cypress:
// Cypress 是一个现代的端到端（E2E）测试框架，主要用于自动化测试 Web 应用程序。它使开发者能够模拟用户在浏览器中的操作，执行功能测试，集成测试等。
// defineConfig 是 Cypress 配置方法，它允许开发者定义 E2E 测试的参数。包括设置浏览器的宽度、高度、基准 URL，以及事件监听器等配置。
// setupNodeEvents(on, config) 中的 on 是一个事件处理器，用来处理和 Cypress 相关的生命周期事件和任务。
// cypress-image-snapshot:
// 这是一个 Cypress 插件库，cypress-image-snapshot 用于实现视觉回归测试（Visual Regression Testing），它可以捕捉和比较测试期间应用的 UI 截图，确保页面或组件在 UI 上没有意外的变化。
// addMatchImageSnapshotPlugin 方法会把这个插件集成到 Cypress 中，用于在测试中自动化截图和比较操作。
import { defineConfig } from "cypress";
import { addMatchImageSnapshotPlugin } from 'cypress-image-snapshot/plugin';

const data = {}

export default defineConfig({
  e2e: {
    viewportHeight: 900,
    viewportWidth: 1400,
    baseUrl: 'http://0.0.0.0:3333/',
    setupNodeEvents(on, config) {
      // implement node event listeners here
      addMatchImageSnapshotPlugin(on, config)
      on('task', {
        setValue({ key, value }) {
          data[key] = value
          return null
        },
        getValue(key) {
          return data[key] || null
        },
      })
    },
  }
});
