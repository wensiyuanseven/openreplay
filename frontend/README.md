# openreplay-ui
OpenReplay prototype UI

On new icon addition:
`yarn gen:icons`

## Documentation

* [Redux](https://redux.js.org/)
* [Immutable](https://facebook.github.io/immutable-js/)
* [Ducks](https://github.com/erikras/ducks-modular-redux)
* [CSS Modules](https://github.com/css-modules/css-modules)

Labels in comments:
TEMP = temporary code
TODO = things to implement

## Contributing notes

Please use `dev` branch as base and target branch.



# openreplay-ui
OpenReplay 原型 UI

## 新增图标时：
要生成新图标，请运行以下命令：
```bash
yarn gen:icons
```

## 文档

以下是项目中使用的一些技术和模式的有用链接：

- **[Redux](https://redux.js.org/)**：一个用于 JavaScript 应用的可预测状态容器，通常与 React 一起使用。
- **[Immutable](https://facebook.github.io/immutable-js/)**：提供不可变、持久数据结构的库。
- **[Ducks](https://github.com/erikras/ducks-modular-redux)**：一种将 reducers、action 类型和 actions 组合到同一个文件中的提议，以避免 Redux 代码的分散。
- **[CSS Modules](https://github.com/css-modules/css-modules)**：默认情况下，所有类名和动画名在 CSS 文件中都是局部作用域的。

## 代码注释中的标签：
在代码库中，您会看到以下标签用于注释，以标记特定部分：

- **TEMP**：表示临时代码，可能需要删除或重构。
- **TODO**：标记需要实现或完成功能的部分。

## 贡献须知

请在贡献代码时遵循以下指南：

- 始终以 `dev` 分支作为工作基础分支。
- 所有的 pull request 目标分支均为 `dev`。

这些做法有助于保持清晰一致的开发工作流程。
