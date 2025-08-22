# 8maple - 影片下載器

一個用於從影片串流網站下載影片的 Python 工具，支援 M3U8 格式影片的下載與合併。

## 功能特點

- 🎬 支援多個影片網站（Bowang、Gimy、PTTPlay）
- 📺 自動解析劇集列表
- 🔄 異步下載，提高效率
- 🔐 支援 AES 加密的 M3U8 影片
- 📦 自動合併 TS 片段為 MP4
- 🔄 斷點續傳功能
- 📊 下載進度顯示
- ✅ 完整的單元測試

## 安裝

### 系統需求

- Python 3.8+
- FFmpeg（用於影片處理）

### 安裝步驟

1. 克隆專案
```bash
git clone https://github.com/recca0120/8maple.git
cd 8maple
```

2. 建立虛擬環境（建議）
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows
```

3. 安裝依賴
```bash
pip install -r requirements.txt
```

## 使用方法

### 基本使用

```python
import asyncio
from main import main

# 下載整部劇集
asyncio.run(main('劇集名稱', 'https://bowang.su/play/xxxxx-x-x.html'))

# 下載指定集數範圍
asyncio.run(main('劇集名稱', 'https://bowang.su/play/xxxxx-x-x.html', start=1, end=10))
```

### 命令列使用

直接修改 `main.py` 中的參數：

```python
if __name__ == '__main__':
    asyncio.run(main('九龍珠 (1993)', 'https://bowang.su/play/103058-5-1.html'))
```

然後執行：
```bash
python main.py
```

## 專案結構

```
8maple/
├── main.py              # 主程式入口
├── crawlers.py          # 網站爬蟲實現
├── m3u8_downloader.py   # M3U8 下載器
├── client.py            # HTTP 客戶端
├── utils.py             # 工具函數
├── requirements.txt     # 依賴套件
├── test_main.py        # 單元測試
└── fixtures/           # 測試用固定資料
```

## 支援的網站

- **Bowang** (bowang.su)
- **Gimy** (gimy.im)

## 工作原理

1. **網頁解析**：爬蟲模組解析影片網頁，提取劇集列表和 M3U8 連結
2. **M3U8 處理**：解析 M3U8 播放列表，獲取所有 TS 片段
3. **並行下載**：使用異步 IO 和線程池並行下載多個片段
4. **解密處理**：如果影片加密，自動下載密鑰並解密
5. **合併輸出**：將所有 TS 片段合併為單一 MP4 檔案

## 測試

執行單元測試：
```bash
pytest test_main.py -v
```

執行測試並查看覆蓋率：
```bash
pytest test_main.py -v --cov=. --cov-report=term
```

## GitHub Actions

專案包含自動化測試工作流程，在每次推送和 PR 時自動執行測試。

## 依賴套件

- `aiohttp` - 異步 HTTP 客戶端
- `beautifulsoup4` - HTML 解析
- `m3u8` - M3U8 播放列表解析
- `pycryptodomex` - AES 解密支援
- `requests` - HTTP 請求
- `pytest` - 測試框架
- `pytest-asyncio` - 異步測試支援
- `pytest-cov` - 測試覆蓋率
- `pyfakefs` - 檔案系統模擬

## 注意事項

- 請確保有足夠的磁碟空間存放下載的影片
- 下載的影片將保存在 `video/` 目錄下
- 每個劇集會建立獨立的子目錄
- 臨時 TS 檔案會在合併後保留，可手動刪除

## 免責聲明

本工具僅供學習和研究使用，請勿用於任何商業用途或侵犯版權的行為。使用者需自行承擔使用本工具的所有責任。

## License

MIT License

## 貢獻

歡迎提交 Issue 和 Pull Request！

## 作者

recca0120