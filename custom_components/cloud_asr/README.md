# 中文云语音识别

这是一个适用于Home Assistant的中文云语音识别组件，支持火山引擎(豆包)和腾讯云ASR服务。可以在Home Assistant的语音助手中选择使用这些ASR服务进行语音识别。

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

### 豆包ASR (火山引擎) 配置

| 参数 | 必填 | 描述 |
| --- | --- | --- |
| type | 是 | 固定为 `doubao` |
| appid | 是 | 火山引擎应用ID |
| access_token | 是 | 火山引擎访问令牌 |
| cluster | 是 | 资源ID，通常为 `volcengine_input_common` |
| output_dir | 否 | 临时文件存储目录，默认为 `tmp/` |
| enable_vad | 否 | 是否启用VAD，默认为 `true` |
| vad_mode | 否 | VAD灵敏度，可选 `normal`、`low`、`high`，默认为 `normal` |

### 腾讯ASR 配置

| 参数 | 必填 | 描述 |
| --- | --- | --- |
| type | 是 | 固定为 `tencent` |
| appid | 是 | 腾讯云应用ID |
| secret_id | 是 | 腾讯云API密钥ID |
| secret_key | 是 | 腾讯云API密钥 |
| output_dir | 否 | 临时文件存储目录，默认为 `tmp/` |
| enable_vad | 否 | 是否启用VAD，默认为 `true` |
| vad_mode | 否 | VAD灵敏度，可选 `normal`、`low`、`high`，默认为 `normal` |

### VAD设置说明

VAD（语音活动检测）用于过滤音频中的静音部分，只保留有语音的片段，可以提高识别准确率和降低API调用成本。

- `normal`: 正常灵敏度，适合大多数场景
- `low`: 低灵敏度，需要更强的语音信号才会被识别为语音，适合噪音较大的环境
- `high`: 高灵敏度，弱语音信号也能被检测到，适合安静环境下捕捉低音量语音

## 使用

配置完成后，重启Home Assistant。在语音助手的设置中，应该能够看到并选择`DoubaoASR`或`TencentASR`作为语音识别引擎。

## 注意事项

- 确保已经在各自的平台上申请了相应的API密钥
- 临时文件目录需要有写入权限
- 语音识别需要网络连接，请确保Home Assistant可以访问外部网络
- 使用VAD功能需要安装numpy库，如果未安装，可以通过HACS或手动安装 