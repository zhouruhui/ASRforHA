# 火山引擎 ASR Home Assistant 集成 (Volcengine ASR Integration for Home Assistant)

本文档介绍了如何安装和配置火山引擎 ASR (Automatic Speech Recognition) 自定义集成，以便在 Home Assistant 的语音助手中使用火山引擎提供的语音转文本服务。

## 功能特性

*   通过 WebSocket 连接火山引擎大模型流式语音识别服务。
*   支持在 Home Assistant 的 `configuration.yaml` 文件中配置认证信息及相关参数。
*   集成到 Home Assistant 的语音助手，作为可选的语音转文本引擎。
*   支持自定义服务地址、语言、音频参数等。

## 先决条件

*   拥有一个火山引擎账号，并已开通语音技术相关服务。
*   获取到火山引擎应用的 APP ID、Access Token 以及 ASR 服务的资源 ID。
*   Home Assistant 版本兼容此集成 (通常为较新版本)。
*   如果通过 HACS 安装，请确保已安装 HACS。

## 安装

您可以通过以下两种方式安装此自定义集成：

### 方式一：通过 HACS (Home Assistant Community Store) 安装 (推荐)

1.  **添加自定义存储库**：
    *   打开 Home Assistant 中的 HACS 面板。
    *   进入 “集成” (Integrations) 部分。
    *   点击右上角的三个点菜单，选择 “自定义存储库” (Custom repositories)。
    *   在 “存储库” (Repository) 输入框中填入本集成的 GitHub 仓库地址 (例如: `https://github.com/manus-team/ha-volcengine-asr` - 请替换为实际的仓库地址)。
    *   在 “类别” (Category) 下拉菜单中选择 “集成” (Integration)。
    *   点击 “添加” (ADD)。
2.  **安装集成**：
    *   关闭自定义存储库对话框后，在 HACS 的集成列表中搜索 “Volcengine ASR Integration” (或您在 `manifest.json` 中定义的名称)。
    *   找到该集成后，点击 “安装” (INSTALL)。
    *   按照 HACS 的提示完成安装。
3.  **重启 Home Assistant**：安装完成后，根据提示重启 Home Assistant 以加载新的集成。

### 方式二：手动安装

1.  **下载集成文件**：
    *   从本集成的 GitHub 仓库下载最新的发布版本 (通常是一个 `.zip` 文件) 或直接克隆仓库。
    *   解压后，您应该会得到一个名为 `volcengine_asr` 的文件夹，其中包含 `__init__.py`, `manifest.json`, `stt.py`, `const.py` 等文件。
2.  **复制到 `custom_components` 目录**：
    *   在您的 Home Assistant 配置目录中，找到或创建 `custom_components` 文件夹。
    *   将下载的 `volcengine_asr` 文件夹完整复制到 `custom_components` 目录下。
    *   最终的目录结构应为：`<config_dir>/custom_components/volcengine_asr/`。
3.  **安装依赖**：
    *   此集成依赖 `websockets` Python 库。如果您的 Home Assistant 环境没有自动安装，您可能需要手动安装。通常，Home Assistant 会在启动时根据 `manifest.json` 中的 `requirements` 自动处理。
4.  **重启 Home Assistant**：复制文件并确认依赖后，重启 Home Assistant 以加载新的集成。

## 配置

在 Home Assistant 的 `configuration.yaml` 文件中添加以下配置块来启用和配置火山引擎 ASR 集成。请将占位符替换为您的实际信息。

```yaml
volcengine_asr:
  app_id: "YOUR_VOLCENGINE_APP_ID"                   # (必填) 您的火山引擎应用 APP ID
  access_token: "YOUR_VOLCENGINE_ACCESS_TOKEN"        # (必填) 您的火山引擎应用 Access Token
  resource_id: "volc.bigasr.sauc.duration"          # (必填) 火山引擎 ASR 服务的资源 ID (例如用户提供的这个)
  
  # --- 可选参数 (以下均为默认值，可按需修改) ---
  # service_url: "wss://openspeech.bytedance.com/api/v3/sauc/bigmodel" # ASR 服务 WebSocket 地址
  # language: "zh-CN"                                 # 识别语言
  # audio_format: "pcm"                               # 音频格式 (应与 Home Assistant 语音助手输出一致)
  # audio_rate: 16000                                 # 音频采样率 (应与 Home Assistant 语音助手输出一致)
  # audio_bits: 16                                    # 音频采样位数 (应与 Home Assistant 语音助手输出一致)
  # audio_channel: 1                                  # 音频声道数 (应与 Home Assistant 语音助手输出一致)
  # enable_itn: true                                  # 是否启用文本逆规范化
  # enable_punc: true                                 # 是否启用标点符号
  # result_type: "single"                             # 结果返回方式 ('full' 或 'single')
  # show_utterances: false                            # 是否输出语音停顿、分句、分词信息
```

**配置项说明**：

*   `app_id` (必填): 您从火山引擎控制台获取的 APP ID。
*   `access_token` (必填): 您从火山引擎控制台获取的 Access Token。
*   `resource_id` (必填): 您使用的火山引擎 ASR 服务的资源 ID。用户提供的是 `volc.bigasr.sauc.duration`。
*   `service_url` (可选): 火山引擎 ASR 服务的 WebSocket 接口地址。默认为双向流式接口 `wss://openspeech.bytedance.com/api/v3/sauc/bigmodel`。如果您需要使用其他接口（如流式输入模式），可以在此修改。
*   `language` (可选): 语音识别的目标语言。默认为 `zh-CN` (简体中文)。请确保火山引擎支持您选择的语言。
*   `audio_format`, `audio_rate`, `audio_bits`, `audio_channel` (可选): 这些参数定义了期望的音频流格式。默认值 (`pcm`, `16000`, `16`, `1`) 通常与 Home Assistant 语音助手生成的音频流格式一致。一般情况下无需修改，除非您明确知道火山引擎 API 对此有特殊要求或 Home Assistant 的音频输出格式不同。
*   `enable_itn` (可选): 是否启用文本逆规范化 (例如，将“一百二十三”转换为“123”)。默认为 `true`。
*   `enable_punc` (可选): 是否在识别结果中自动添加标点符号。默认为 `true`。
*   `result_type` (可选): 结果返回方式。`single` 表示增量返回结果（推荐用于实时语音助手），`full` 表示全量返回。默认为 `single`。
*   `show_utterances` (可选): 是否在结果中包含语音的停顿、分句、分词等详细信息。默认为 `false`。

配置完成后，请再次重启 Home Assistant 以使配置生效。

## 使用

配置并重启 Home Assistant 后，火山引擎 ASR 集成应该可以作为语音转文本 (STT) 引擎使用了。

1.  **选择 STT 引擎**：
    *   在 Home Assistant 的配置中，找到语音助手或 STT 相关的设置部分 (具体位置可能因 Home Assistant 版本而异，通常在 “配置” -> “语音助手” 或 “Assist” 相关设置中)。
    *   在 “首选语音转文本引擎” (Preferred Speech-to-Text engine) 或类似选项中，您应该能看到 “Volcengine ASR Integration” (或您在 `manifest.json` 中定义的名称) 作为可选引擎。
    *   选择它作为您的 STT 引擎。
2.  **测试语音识别**：
    *   使用 Home Assistant 的语音助手功能（例如，通过移动应用、网页界面的麦克风按钮，或连接的智能音箱）进行语音输入。
    *   Home Assistant 会将您的语音流发送到火山引擎 ASR 服务进行处理，并将识别到的文本返回给语音助手进行后续的指令解析。

## 故障排查

*   **集成未加载**：
    *   检查 Home Assistant 的日志 (`home-assistant.log`) 中是否有关于 `volcengine_asr` 组件的错误信息。
    *   确认文件已正确放置在 `custom_components/volcengine_asr/` 目录下，并且 `manifest.json` 文件内容正确。
    *   确保已重启 Home Assistant。
*   **认证失败或连接错误**：
    *   仔细检查 `configuration.yaml` 中的 `app_id`, `access_token`, 和 `resource_id` 是否正确无误，并且与您在火山引擎控制台获取的信息一致。
    *   确认您的火山引擎账户状态正常，相关服务未欠费或停用。
    *   检查网络连接，确保 Home Assistant 服务器可以访问火山引擎的 ASR 服务地址 (`openspeech.bytedance.com`)。
    *   查看 Home Assistant 日志中是否有更详细的错误信息，例如 WebSocket 连接错误、HTTP 状态码错误等。
*   **识别效果不佳**：
    *   尝试调整麦克风的输入音量和环境噪音。
    *   如果火山引擎 API 支持，可以尝试在 `configuration.yaml` 中配置热词等高级参数以优化特定场景的识别率 (本集成目前未直接暴露所有高级参数，但可根据火山引擎文档扩展)。
    *   确认 `language` 配置与您实际使用的语言一致。

## 贡献

欢迎对本项目进行贡献！如果您发现任何问题或有改进建议，请通过 GitHub Issues 或 Pull Requests 提出。

## 免责声明

*   本集成由社区开发和维护，并非火山引擎官方出品。
*   使用火山引擎 ASR 服务可能会产生费用，请查阅火山引擎的计费策略。
*   请妥善保管您的火山引擎认证信息 (APP ID, Access Token)。

