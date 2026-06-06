# 小说转有声书系统 — 设计文档

## 1. 概述

构建一个将中文文字小说自动转换为有声小说的系统。用户导入整本书（TXT/EPUB/MOBI），系统通过 LLM 分析角色和情感，利用 IndexTTS2 合成语音，最终在 Web/Android 端提供逐句点击播放体验。

## 2. 架构

```
[小说文件] → Parser → [章节+句子] → LLM → [角色/情感标注]
    → Voice Matcher → [角色↔音色映射] → IndexTTS2 → [WAV]
    → Opus Compressor → [.opus] → REST API → [Web/Android]
```

- **后端**: Python FastAPI + SQLAlchemy (MySQL) + IndexTTS2
- **LLM**: 本地 OpenAI 兼容 API (`http://127.0.0.1:12434/v1`)，模型 `Qwopus3.5-4B-v3-4bit`，超时 30min，并发 4
- **语音库**: 中文多说话人开源数据集（如 AISHELL-3），LLM 根据角色匹配音色
- **音频压缩**: Opus 64kbps

## 3. 数据模型

### 3.1 MySQL 表结构

**novels**
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT PK AUTO_INC | |
| title | VARCHAR(255) | 书名 |
| author | VARCHAR(128) | 作者 |
| language | VARCHAR(10) | 语言，默认 "zh" |
| file_type | VARCHAR(10) | txt/epub/mobi |
| status | ENUM('imported','characters_analyzed','processing','done','error') | |
| created_at | DATETIME | |

**chapters**
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT PK AUTO_INC | |
| novel_id | INT FK→novels | |
| chapter_index | INT | 章节序号 |
| title | VARCHAR(255) | 章标题 |
| full_text | LONGTEXT | 章节完整文本 |
| status | ENUM('pending','analyzing','generating','done','error') | |
| sentence_count | INT | 句子数 |

**sentences**
| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT PK AUTO_INC | |
| chapter_id | INT FK→chapters | |
| sentence_index | INT | 句内序号 |
| text | TEXT | 原文 |
| speaker | VARCHAR(128) | 说话人，如 "张三" 或 "旁白" |
| emotion | VARCHAR(32) | 情感: happy/angry/sad/fear/disgust/melancholy/surprise/calm |
| emotion_vector | VARCHAR(64) | IndexTTS2 8维向量 JSON |
| audio_duration | FLOAT | 秒 |
| audio_path | VARCHAR(512) | 相对路径 |

**characters**
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT PK AUTO_INC | |
| novel_id | INT FK→novels | |
| name | VARCHAR(64) | 规范名 |
| aliases | JSON | 别名数组 |
| base_profile | JSON | {gender, age_range, background} |
| evolution | JSON | [{phase, chapter_range_start, chapter_range_end, personality, speaking_style}] |
| voice_ref_id | INT FK→voice_library | 匹配的参考音色 ID |

**voice_library**
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT PK AUTO_INC | |
| name | VARCHAR(128) | 音色名 |
| gender | VARCHAR(8) | male/female |
| age_group | VARCHAR(32) | child/young/middle/elderly |
| description | TEXT | 声音特征描述 |
| audio_path | VARCHAR(512) | 参考音频路径 |
| source | VARCHAR(64) | 数据集来源（如 AISHELL-3） |

### 3.2 文件存储

```
data/audio/{novel_id}/{chapter_index}/sentence_{seq:05d}.opus
```

## 4. 模块设计

### 4.1 Parser（`src/parser/`）

- `NovelParser` (ABC) — 抽象基类，定义 `parse(path) → list[Chapter]`
- `TxtParser` — 按 `^第[一二三四五六七八九十百千零0-9]+章` 正则分章
- `EpubParser` — 用 `ebooklib` + `beautifulsoup4` 解析 EPUB
- `MobiParser` — 用 `mobi` 解包或回退

### 4.2 LLM 模块（`src/llm/`）

- `LLMClient` — OpenAI 兼容 API 封装，30min 超时，4 并发 semaphore
- `CharacterAnalyzer` — 两轮分析：①提取角色+别名 ②识别性格演变阶段
- `SentenceAnalyzer` — 逐章分析每句说话人和情感

### 4.3 语音模块（`src/voice/`）

- `VoiceLibrary` — 管理参考音频，入库 MySQL
- `VoiceMatcher` — LLM 将角色 profile 与语音库条目匹配

### 4.4 TTS 引擎（`src/tts/`）

- `TTSEngine` — 调用 IndexTTS2 逐句生成 WAV

### 4.5 音频压缩（`src/audio/`）

- `AudioCompressor` — WAV → Opus 64kbps，使用 ffmpeg

### 4.6 管线编排（`src/pipeline/`）

- `PipelineOrchestrator` — 按序执行 6 步管线，支持断点续传

### 4.7 REST API（`src/api/`）

| 路由 | 方法 | 说明 |
|------|------|------|
| /api/novels | GET | 小说列表 |
| /api/novels | POST | 导入小说 |
| /api/novels/{id} | GET | 小说详情 |
| /api/novels/{id}/characters | GET | 角色列表 |
| /api/novels/{nid}/chapters/{cid}/sentences | GET | 章节句子+音频 URL |
| /api/audio/{novel_id}/{chapter_id}/{sentence_seq} | GET | 句子音频 |
| /api/novels/{id} | DELETE | 删除小说 |
| ws://host/api/ws/progress/{novel_id} | WS | 实时进度 |

## 5. Prompt 设计

### 角色分析 Prompt

```
分析以下小说的主要角色。对每个角色：
1. 列出该角色的所有不同称呼（包括但不限于姓名、昵称、称号等）
2. 描述其基础设定（性别、年龄范围、背景身份）
3. 识别角色性格演变阶段（按章节范围划分）

输出 JSON 格式：
[{"name":"规范名","aliases":["别名1"],"base_profile":{"gender":"男","age_range":"20-30","background":"..."},"evolution":[{"phase":1,"chapter_range":[1,15],"personality":"...","speaking_style":"..."}]}]

小说正文：
{full_text}
```

### 逐句分析 Prompt

```
分析以下章节中每句话的说话人和情感。
- 说话人：角色名（使用规范名）或"旁白"
- 情感：从 [高兴, 愤怒, 悲伤, 害怕, 厌恶, 忧郁, 惊讶, 平静] 选择一个

角色性格阶段参考：
{character_evolution_context}

输出 JSON：
[{"sentence_index":0,"text":"...","speaker":"...","emotion":"..."}]

章节内容：
{chapter_text}
```

## 6. IndexTTS2 集成

IndexTTS2 路径：`/Users/lambojw/work/index-tts`

调用方式：
```python
from indextts.infer_v2 import IndexTTS2

tts = IndexTTS2(cfg_path="checkpoints/config.yaml", model_dir="checkpoints", use_fp16=True)
tts.infer(
    spk_audio_prompt=voice_ref_path,
    text=sentence_text,
    output_path=output_wav,
    emo_vector=emotion_vector,
    use_emo_text=True,
    emo_text=sentence_text,
    use_random=False,
    verbose=False
)
```

## 7. 音频压缩

`ffmpeg -i input.wav -c:a libopus -b:a 64k -vbr on output.opus`

## 8. 错误处理与断点续传

- 每章处理前检查状态，已完成的跳过
- 单句生成失败记录 error，跳过继续
- 崩溃重启时从 chapters.status 读取，中断的章继续
- LLM 调用最多重试 3 次
