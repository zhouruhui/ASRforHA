# 中文云语音识别 (Chinese Cloud ASR)

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)

这是一个适用于Home Assistant的中文云语音识别组件，支持火山引擎(豆包)和腾讯云ASR服务。可以在Home Assistant的语音助手中选择使用这些ASR服务进行语音识别。

## 功能特点

- 支持火山引擎(豆包)ASR服务
- 支持腾讯云ASR服务
- 支持VAD（语音活动检测），过滤静音提高识别率
- 可通过configuration.yaml文件配置
- 集成Home Assistant语音助手
- 支持中文和英文语音识别

## 安装

### HACS安装（推荐）

1. 在HACS中，转到"自定义存储库"
2. 添加此仓库: `https://github.com/zhouruhui/ASRforHA`
3. 选择类别为"集成"
4. 点击"添加"
5. 搜索"中文云语音识别"并安装

### 手动安装

1. 下载此仓库的最新版本
2. 解压文件，将`custom_components/cloud_asr`文件夹复制到你的Home Assistant配置目录的`custom_components`文件夹中
3. 重新启动Home Assistant

## 配置

在你的`configuration.yaml`文件中添加以下配置：

```yaml
cloud_asr:
  DoubaoASR:
    # 可以在这里申请相关Key等信息
    # https://console.volcengine.com/speech/app
    type: doubao
    appid: 你的火山引擎语音合成服务appid
    access_token: 你的火山引擎语音合成服务access_token
    cluster: volcengine_input_common
    output_dir: tmp/
    # VAD配置 (可选)
    enable_vad: true
    vad_mode: normal  # 可选: normal, low, high
    
  TencentASR:
    # token申请地址：https://console.cloud.tencent.com/cam/capi
    # 免费领取资源：https://console.cloud.tencent.com/asr/resourcebundle
    type: tencent
    appid: 你的腾讯语音合成服务appid
    secret_id: 你的腾讯语音合成服务secret_id
    secret_key: 你的腾讯语音合成服务secret_key
    output_dir: tmp/
    # VAD配置 (可选)
    enable_vad: true
    vad_mode: normal  # 可选: normal, low, high
```

更多配置详情请查看[组件文档](./custom_components/cloud_asr/README.md)。

## 使用

配置完成后，重启Home Assistant。在语音助手的设置中，应该能够看到并选择`DoubaoASR`或`TencentASR`作为语音识别引擎。

## 许可证

MIT 