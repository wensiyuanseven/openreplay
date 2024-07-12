CONTRIBUTING.md 文件是开源项目中的一部分，用于指导和帮助潜在贡献者了解如何为项目做出贡献。这个文件包含了有关项目贡献过程的详细信息和指南，确保贡献者知道如何高效且有条不紊地进行贡献。

作用
指导贡献者：提供清晰的步骤和指南，帮助贡献者了解如何有效地为项目做出贡献。
提高项目质量：通过统一的代码风格、测试要求和提交规范，确保项目的代码质量和一致性。
减少沟通成本：预先回答贡献者可能遇到的问题，减少项目维护者和贡献者之间的沟通成本。
增强社区参与度：鼓励和支持更多的人参与项目，扩大社区的规模和多样性。
确保顺畅的开发流程：规范贡献流程，确保项目开发的高效和有序。
总之，CONTRIBUTING.md 文件是开源项目中至关重要的一部分，能够帮助新老贡献者了解和遵循项目的贡献流程，确保项目的长期健康发展。



我们很高兴您考虑为 OpenReplay 做出贡献。我们非常感谢每一位贡献者。不用担心如何开始，尽管我们不希望一大堆规则阻碍您的贡献，这份文档将为您提供一些指导。如果您还有疑问，请随时寻求帮助。

## 行为准则

参与此项目即表示您同意遵守我们的[行为准则](CODE_OF_CONDUCT.md)。

## 初次贡献者

我们特别感谢来自初次贡献者的所有贡献。“Good first issues” 是开始的最佳方式。如果您不确定如何提供帮助，请随时通过[电子邮件](mailto:hey@openreplay.com)或[Slack](https://slack.openreplay.com)寻求帮助。所有贡献者必须同意我们的[贡献者许可协议](https://cla-assistant.io/openreplay/openreplay)。

## 贡献领域

### 文档

我们希望保持文档全面、简洁和更新。我们感谢任何形式的贡献：
- 报告缺失的部分
- 修正现有文档中的错误
- 添加内容到文档中

### 社区内容

我们欢迎参与教育社区的贡献，例如：
- 撰写技术博客
- 添加新的用户指南
- 组织研讨会
- 在活动中演讲

我们有一个专门用于社区内容的仓库。如果您有任何贡献，甚至不是上述提到的内容，欢迎提交 pull request。

### OpenReplay 核心

我们在核心组件上有一些适合开源贡献的问题。如果您熟悉 Go 或 JavaScript，请查看我们的问题列表。

## 贡献方式

### 编写代码

我们欢迎所有的代码贡献，无论大小。请记住以下几点：

- 请确保您正在处理的问题已关联到某个 issue
- 如果您正在处理某个 issue，请在该 issue 下评论，以防止他人重复工作
- 我们遵循 [fork-and-branch](https://blog.scottlowe.org/2015/01/27/using-fork-branch-git-workflow/) 方法
- 合并提交并在提交信息中使用 `fix #<issue-no>` 引用问题
- 在提交 pull request 之前，请将您的分支与 master 进行 rebase

如果您计划处理列表中未列出的大功能，请先提出 issue，以便我们确认其是否适合 OpenReplay 整体。

查看我们的审核流程。

### 报告 Bug

Bug 报告有助于我们改进 OpenReplay。在提出新问题之前：
- 在已报告的 Bug 列表中搜索，以确保不是重复问题
- 确保您在最新发布的版本上测试过（我们可能已经修复了）
- 提供明确的重现步骤，并在相关情况下附上日志

### 报告安全漏洞

请不要创建公开的 GitHub issue。如果您发现安全漏洞，请直接通过电子邮件 [security@openreplay.com](mailto:security@openreplay.com) 联系我们，而不是提出 issue。

### 点赞问题和请求新功能

点赞问题和请求新功能是告诉我们您希望我们构建什么的最佳方式，有助于优先安排我们的工作。请务必查看功能请求列表，避免重复。

## 审核流程

我们在审核 PR 时会回答以下问题：
- PR 是否修复了问题？
- 提出的解决方案是否合理？
- 在数百万会话和用户事件下的性能如何？
- 是否进行了测试？
- 是否引入了安全漏洞？
- 贡献者是否同意我们的 CLA？

一旦您的 PR 通过审核，我们将合并它。否则，我们会礼貌地请您进行修改。


We're glad you're considering contributing to OpenReplay. Each and every contribution is highly appreciated. Don't worry if you're not sure how to get things started. Although we don't want a wall of rules to stand in the way of your contribution, this document should give a bit more guidance on the best way to proceed. If you still have questions, reach out for help.

## Code of Conduct

By participating in this project, you are expected to uphold our [Code of Conduct](CODE_OF_CONDUCT.md).

## First-time Contributors

We appreciate all contributions, especially those coming from first time contributors. Good first issues is the best way start. If you're not sure how to help, feel free to reach out anytime for assistance via [email](mailto:hey@openreplay.com) or [Slack](https://slack.openreplay.com). All contributors must approve our [Contributor License Agreement](https://cla-assistant.io/openreplay/openreplay).

## Areas for Contributing

### Documentation

We want to keep our docs comprehensive, concise and updated. We are grateful for any kind of contribution in this area:
- Report missing sections
- Fix errors in the existing docs
- Add content to the docs

### Community Content

We're happy about contributions that participate in educating our community, such as:
- Writing technical blog post
- Adding new user guides
- Organizing a workshop
- Speaking at an event

We have a repo dedicated to community content. Feel free to submit a pull request in this repo, if you have something to add even if it's not related to what's mentioned above.

### OpenReplay Core

We have some issues on core components that are suitable for open source contributions. If you know Go or JavaScript, check out our issue list.

## Ways to Contribute

### Writing Code

We love all code contributions, big or small. A few things to keep in mind:

- Please make sure there is an issue associated with what you're working on
- If you're tackling an issue, please comment on that to prevent duplicate work by others
- We follow the [fork-and-branch](https://blog.scottlowe.org/2015/01/27/using-fork-branch-git-workflow/) approach
- Squash your commits and refer to the issue using `fix #<issue-no>` in the commit message
- Rebase master with your branch before submitting a pull request.

If you're planning to work on a bigger feature that is not on the list of issues, please raise an issue first so we can check whether it makes sense for OpenReplay as a whole.

Check our Review Process below.

### Reporting Bugs

Bug reports help us make OpenReplay better for everyone. Before raising a new issue:
- Search within the list of reported bugs so you're not dealing with a duplicate
- Make sure you test against the last released version (we may have fixed it already)
- Provide clear steps to reproduce the issue and attach logs if relevant

### Reporting Security Flaws

Please do not create a public GitHub issue. If you find a security flaw, please email us directly at [security@openreplay.com](mailto:security@openreplay.com) instead of raising an issue.

### Upvoting Issues and Requesting Features

Upvoting issues and requesting new features is the best way to tell us what you'd like us to build and helps prioritize our efforts. Don't refrain from doing that but make sure to watch out for duplicates by looking at the feature-request list.

## Review Process

We try to answer the below questions when reviewing a PR:
- Does the PR fix the issue?
- Does the proposed solution makes sense?
- How will it perform with millions of sessions and users events?
- Has it been tested?
- Is it introducing any security flaws?
- Did the contributor approve our CLA?

Once your PR passes, we will merge it. Otherwise, we'll politely ask you to make a change.
